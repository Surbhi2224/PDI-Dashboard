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

    # Fix numeric
    for col in ["Plan", "Actual", "Pending", "Count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Fix date
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

    df_grouped = df.groupby("Date")[["Plan","Actual","Pending"]].sum().reset_index()

    st.subheader("Executive Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("Offered", int(df_grouped["Plan"].sum()))
    col2.metric("Cleared", int(df_grouped["Actual"].sum()))
    col3.metric("Pending", int(df_grouped["Pending"].sum()))

    fig = go.Figure()
    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Plan"], name="Offered", marker_color="blue")
    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Actual"], name="Cleared", marker_color="green")
    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Pending"], name="Pending", marker_color="orange")

    st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📅 DAILY CLEARING (CLEAN GRAPH)
# ============================================
elif page == "Daily_Clearing":

    df = load_sheet("Daily_Clearing")

    st.subheader("Daily Clearing")

    # DROPDOWN
    models = ["All"] + sorted(df["Model"].unique())
    selected_model = st.selectbox("Select Model", models)

    if selected_model != "All":
        df = df[df["Model"] == selected_model]

    df_grouped = df.groupby("Date")[["Plan","Actual","Pending"]].sum().reset_index()

    # KPI
    col1, col2, col3 = st.columns(3)
    col1.metric("Offered", int(df_grouped["Plan"].sum()))
    col2.metric("Cleared", int(df_grouped["Actual"].sum()))
    col3.metric("Pending", int(df_grouped["Pending"].sum()))

    # CLEAN GRAPH
    fig = go.Figure()

    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Plan"], name="Offered")
    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Actual"], name="Cleared")
    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Pending"], name="Pending")

    fig.update_layout(barmode="group")

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
# 📊 ALL ISSUE PAGES (INCLUDING OTHER)
# ============================================
elif page not in ["Major_Issues", "DPV"]:

    df = load_sheet(page)

    st.subheader(page.replace("_", " "))

    # DROPDOWN
    issues = df["Issue Type"].dropna().unique().tolist()
    selected = st.selectbox("Select Issue", ["All"] + issues)

    if selected != "All":
        df = df[df["Issue Type"] == selected]

    # TOTAL
    st.metric("Total Issues", int(df["Count"].sum()))

    # TOP 10 GRAPH
    top10 = df.groupby("Issue Type")["Count"].sum().nlargest(10).reset_index()

    fig = go.Figure()
    fig.add_bar(
        x=top10["Issue Type"],
        y=top10["Count"],
        text=top10["Count"],
        textposition="outside"
    )

    st.plotly_chart(fig, use_container_width=True)

    # PARETO ANALYSIS
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

    # FIX VALUES
    df["DPV %"] = pd.to_numeric(df["DPV %"], errors="coerce").fillna(0)
    df["Paint issues %"] = pd.to_numeric(df["Paint issues %"], errors="coerce").fillna(0)
    df["Other issues %"] = pd.to_numeric(df["Other issues %"], errors="coerce").fillna(0)

    # DROPDOWN
    months = df["Month"].dropna().unique()
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

# FOOTER
st.markdown("---")
st.caption("Developed by Surbhi | PDI Dashboard")
