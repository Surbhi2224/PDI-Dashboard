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

# ===== LOAD DATA =====
@st.cache_data
def load_sheet(name):
    df = pd.DataFrame(
        client.open("PDI_Dashboard").worksheet(name).get_all_records()
    )

    # Clean columns
    df.columns = df.columns.str.strip()

    for col in ["Plan", "Actual", "Pending", "Count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    if "Model" in df.columns:
        df["Model"] = df["Model"].astype(str).str.strip()

    return df


# ===== SIDEBAR =====
pages = [
    "Executive_Summary","Daily_Clearing","Electrical_Issues",
    "Process_Issues","SQA_Issues","Paint_Issues",
    "Design_Issue","Testing_Issue","Water_Ingress","Major_Issues"
]

page = st.sidebar.selectbox("Navigation", pages)

# ============================================
# 📊 EXECUTIVE SUMMARY
# ============================================
if page == "Executive_Summary":

    df = load_sheet("Daily_Clearing")

    st.subheader("Executive Summary")

    total_plan = df["Plan"].sum()
    total_actual = df["Actual"].sum()
    total_pending = df["Pending"].sum()

    col1, col2, col3 = st.columns(3)

    col1.metric("Offered", int(total_plan))
    col2.metric("Cleared", int(total_actual))
    col3.metric("Pending", int(total_pending))

    # Daily trend
    df_grouped = df.groupby("Date")[["Plan","Actual","Pending"]].sum().reset_index()

    fig = go.Figure()
    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Plan"], name="Offered", marker_color="blue")
    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Pending"], name="Pending", marker_color="orange")

    st.plotly_chart(fig, use_container_width=True)


# ============================================
# 📅 DAILY CLEARING
# ============================================
elif page == "Daily_Clearing":

    df = load_sheet("Daily_Clearing")

    st.subheader("Daily Clearing")

    # ===== DROPDOWN =====
    models = ["All"] + sorted(df["Model"].unique())
    selected_model = st.selectbox("Select Model", models)

    # ===== FILTER =====
    if selected_model != "All":
        df_filtered = df[df["Model"] == selected_model]
    else:
        df_filtered = df.copy()

    # ===== KPI =====
    col1, col2, col3 = st.columns(3)

    col1.metric("Offered", int(df_filtered["Plan"].sum()))
    col2.metric("Cleared", int(df_filtered["Actual"].sum()))
    col3.metric("Pending", int(df_filtered["Pending"].sum()))

    # ===== MODEL COLOR MAP =====
    color_map = {
        "TR": "#1f77b4",
        "LR": "#ff7f0e",
        "V1": "#2ca02c",
        "V2": "#d62728",
        "V3": "#9467bd",
        "ARMOURED": "#8c564b"
    }

    # ===== GRAPH =====
    st.subheader("Model-wise Actual")

    fig = go.Figure()

    for model in sorted(df["Model"].unique()):
        model_df = df[df["Model"] == model]

        fig.add_bar(
            x=model_df["Date"],
            y=model_df["Actual"],
            name=model,
            marker_color=color_map.get(model, "gray"),
            text=model_df["Actual"],
            textposition="outside"
        )

    fig.update_layout(barmode="group")

    st.plotly_chart(fig, use_container_width=True)

    # ===== FORECAST =====
    st.subheader("Forecast")

    df_sum = df_filtered.groupby("Date")["Actual"].sum().reset_index()
    df_sum = df_sum.sort_values("Date")

    if len(df_sum) > 2:
        trend = np.poly1d(np.polyfit(range(len(df_sum)), df_sum["Actual"], 1))

        fig2 = go.Figure()
        fig2.add_scatter(x=df_sum["Date"], y=df_sum["Actual"], name="Actual")
        fig2.add_scatter(x=df_sum["Date"], y=trend(range(len(df_sum))), name="Trend")

        st.plotly_chart(fig2, use_container_width=True)


# ============================================
# 📊 ISSUE PAGES
# ============================================
elif page != "Major_Issues":

    df = load_sheet(page)

    st.subheader(page.replace("_", " "))

    # ===== DROPDOWN =====
    issues = df["Issue Type"].dropna().unique().tolist()
    selected = st.selectbox("Select Issue", ["All"] + issues)

    if selected != "All":
        df = df[df["Issue Type"] == selected]

    # ===== TOTAL =====
    st.metric("Total Issues", int(df["Count"].sum()))

    # ===== TOP 10 =====
    top10 = df.groupby("Issue Type")["Count"].sum().nlargest(10).reset_index()

    fig = go.Figure()
    fig.add_bar(
        x=top10["Issue Type"],
        y=top10["Count"],
        text=top10["Count"],
        textposition="outside"
    )

    st.plotly_chart(fig, use_container_width=True)

    # ===== PARETO =====
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
# 📋 MAJOR ISSUES
# ============================================
else:
    st.subheader("Major Issues")
    st.info("Check detailed data in Google Sheets")


# ===== FOOTER =====
st.markdown("---")
st.caption("Developed by Surbhi | PDI Dashboard")
