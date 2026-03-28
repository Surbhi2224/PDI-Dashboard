import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
import numpy as np
from streamlit_autorefresh import st_autorefresh

# ===== CONFIG =====
st.set_page_config(layout="wide", page_title="PDI Dashboard")
st_autorefresh(interval=5000, key="refresh")

st.title("PDI Production Dashboard")

# ===== GOOGLE SHEETS =====
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

# ===== LOAD FUNCTION =====
@st.cache_data
def load_sheet(name):
    df = pd.DataFrame(
        client.open("PDI_Dashboard").worksheet(name).get_all_records()
    )

    df.columns = df.columns.str.strip()

    for col in ["Plan", "Actual", "Pending", "Count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    return df

# ===== SIDEBAR =====
pages = [
    "Executive_Summary",
    "Daily_Clearing",
    "Electrical_Issues",
    "Process_Issues",
    "SQA_Issues",
    "Paint_Issues",
    "Design_Issue",
    "Testing_Issue",
    "Water_Ingress",
    "Other_Issues",
    "Major_Issues",
    "DPV"
]

page = st.sidebar.selectbox("Navigation", pages)

# ============================================
# 📊 EXECUTIVE SUMMARY
# ============================================
if page == "Executive_Summary":

    df = load_sheet("Daily_Clearing")
    df = df.dropna(subset=["Date"])

    df_grouped = df.groupby("Date")[["Plan","Actual","Pending"]].sum().reset_index()

    st.subheader("Executive Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("Offered", int(df_grouped["Plan"].sum()))
    col2.metric("Cleared", int(df_grouped["Actual"].sum()))
    col3.metric("Pending", int(df_grouped["Pending"].sum()))

    fig = go.Figure()
    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Plan"], name="Offered")
    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Actual"], name="Cleared")
    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Pending"], name="Pending")

    st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📅 DAILY CLEARING
# ============================================
elif page == "Daily_Clearing":

    df = load_sheet("Daily_Clearing")
    df = df.dropna(subset=["Date"])

    st.subheader("Daily Clearing")

    models = ["All"] + sorted(df["Model"].unique())
    selected_model = st.selectbox("Select Model", models)

    if selected_model != "All":
        df_filtered = df[df["Model"] == selected_model]
    else:
        df_filtered = df

    df_grouped = df_filtered.groupby("Date")[["Plan","Actual","Pending"]].sum().reset_index()

    # KPI
    col1, col2, col3 = st.columns(3)
    col1.metric("Offered", int(df_grouped["Plan"].sum()))
    col2.metric("Cleared", int(df_grouped["Actual"].sum()))
    col3.metric("Pending", int(df_grouped["Pending"].sum()))

    # CLEAN MODEL GRAPH
    st.subheader("Model-wise Clearing")

    fig = go.Figure()

    colors = {
        "TR": "#1f77b4",
        "LR": "#ff7f0e",
        "V1": "#2ca02c",
        "V2": "#d62728",
        "V3": "#9467bd",
        "ARMOURED": "#8c564b"
    }

    for model in df["Model"].unique():
        model_df = df[df["Model"] == model]

        fig.add_scatter(
            x=model_df["Date"],
            y=model_df["Actual"],
            mode="lines+markers",
            name=model,
            line=dict(color=colors.get(model, "white"))
        )

    st.plotly_chart(fig, use_container_width=True)

    # FORECAST
    st.subheader("Forecast")

    if len(df_grouped) > 2:
        trend = np.poly1d(np.polyfit(range(len(df_grouped)), df_grouped["Actual"], 1))

        fig2 = go.Figure()
        fig2.add_scatter(x=df_grouped["Date"], y=df_grouped["Actual"], name="Actual")
        fig2.add_scatter(x=df_grouped["Date"], y=trend(range(len(df_grouped))), name="Trend")

        st.plotly_chart(fig2, use_container_width=True)

# ============================================
# 📊 ISSUE PAGES
# ============================================
elif page not in ["Major_Issues", "DPV"]:

    df = load_sheet(page)

    st.subheader(page.replace("_", " "))

    if "Issue Type" not in df.columns:
        st.error("❌ 'Issue Type' column missing")
        st.stop()

    issues = df["Issue Type"].dropna().unique().tolist()
    selected = st.selectbox("Select Issue", ["All"] + issues)

    if selected != "All":
        df = df[df["Issue Type"] == selected]

    st.metric("Total Issues", int(df["Count"].sum()))

    # TOP 10
    top10 = df.groupby("Issue Type")["Count"].sum().nlargest(10).reset_index()

    fig = go.Figure()
    fig.add_bar(
        x=top10["Issue Type"],
        y=top10["Count"],
        text=top10["Count"],
        textposition="outside"
    )

    st.plotly_chart(fig, use_container_width=True)

    # PARETO
    st.subheader("Pareto Analysis")

    pareto = df.groupby("Issue Type")["Count"].sum().reset_index()
    pareto = pareto.sort_values(by="Count", ascending=False)
    pareto["Cum%"] = pareto["Count"].cumsum() / pareto["Count"].sum() * 100

    fig2 = go.Figure()
    fig2.add_bar(x=pareto["Issue Type"], y=pareto["Count"], name="Count")

    fig2.add_scatter(
        x=pareto["Issue Type"],
        y=pareto["Cum%"],
        yaxis="y2",
        name="Cumulative %"
    )

    fig2.update_layout(yaxis2=dict(overlaying="y", side="right"))

    st.plotly_chart(fig2, use_container_width=True)

# ============================================
# 📈 DPV PAGE
# ============================================
elif page == "DPV":

    df = load_sheet("DPV")

    st.subheader("DPV Analysis")

    if "Month" not in df.columns:
        st.error("❌ 'Month' column missing in DPV sheet")
        st.stop()

    for col in ["DPV %", "Paint issues %", "Other issues %"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

    months = df["Month"].dropna().unique().tolist()
    selected_month = st.selectbox("Select Month", months)

    df_filtered = df[df["Month"] == selected_month]

    col1, col2, col3 = st.columns(3)
    col1.metric("DPV %", float(df_filtered["DPV %"].values[0]))
    col2.metric("Paint %", float(df_filtered["Paint issues %"].values[0]))
    col3.metric("Other %", float(df_filtered["Other issues %"].values[0]))

    fig = go.Figure()
    fig.add_scatter(x=df["Month"], y=df["DPV %"], name="DPV %")
    fig.add_scatter(x=df["Month"], y=df["Paint issues %"], name="Paint %")
    fig.add_scatter(x=df["Month"], y=df["Other issues %"], name="Other %")

    st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📋 MAJOR ISSUES
# ============================================
else:
    st.subheader("Major Issues")
    st.info("Check detailed data in Google Sheets")

# ===== FOOTER =====
st.markdown("---")
st.caption("Developed by Surbhi | PDI Dashboard")
