import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
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

    col1.metric("Total Offered", int(df_grouped["Plan"].sum()))
    col2.metric("Total Cleared", int(df_grouped["Actual"].sum()))
    col3.metric("Total Pending", int(df_grouped["Pending"].sum()))

    fig = go.Figure()

    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Plan"], name="Plan", marker_color="#1f77b4")
    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Pending"], name="Pending", marker_color="#ff7f0e")

    st.plotly_chart(fig, use_container_width=True)


# ============================================
# 📅 DAILY CLEARING (CLEAN STYLE)
# ============================================
elif page == "Daily_Clearing":

    df = load_sheet("Daily_Clearing")

    st.subheader("Daily Clearing (Model-wise)")

    # REMOVE EMPTY / ZERO ROWS ISSUE
    df = df[~((df["Plan"] == 0) & (df["Actual"] == 0) & (df["Pending"] == 0))]

    # ===== DATE FILTER =====
    min_date = df["Date"].min()
    max_date = df["Date"].max()

    start, end = st.date_input("Select Date Range", [min_date, max_date])

    df = df[(df["Date"] >= pd.to_datetime(start)) & (df["Date"] <= pd.to_datetime(end))]

    # ===== KPI =====
    col1, col2, col3 = st.columns(3)

    col1.metric("Offered", int(df["Plan"].sum()))
    col2.metric("Cleared", int(df["Actual"].sum()))
    col3.metric("Pending", int(df["Pending"].sum()))

    # ===== CLEAN HORIZONTAL GRAPH =====
    st.subheader("Model Performance")

    df_model = df.groupby("Model")[["Plan","Actual","Pending"]].sum().reset_index()

    fig = go.Figure()

    fig.add_bar(
        y=df_model["Model"],
        x=df_model["Actual"],
        name="Cleared",
        orientation='h',
        marker_color="#2ca02c"
    )

    fig.add_bar(
        y=df_model["Model"],
        x=df_model["Pending"],
        name="Pending",
        orientation='h',
        marker_color="#d62728"
    )

    fig.update_layout(barmode="stack")

    st.plotly_chart(fig, use_container_width=True)


# ============================================
# ⚡ ELECTRICAL ISSUES (CLEAN + PARETO)
# ============================================
elif page == "Electrical_Issues":

    df = load_sheet("Electrical_Issues")

    st.subheader("Electrical Issues")

    # ===== CLEAN BAR (LIKE DAILY) =====
    df_group = df.groupby("Issue Type")["Count"].sum().reset_index()

    fig = go.Figure()

    fig.add_bar(
        y=df_group["Issue Type"],
        x=df_group["Count"],
        orientation='h',
        marker_color="#1f77b4"
    )

    st.plotly_chart(fig, use_container_width=True)

    # ===== PARETO (IMPORTANT — NOT REMOVED) =====
    st.subheader("Pareto Analysis")

    pareto = df_group.sort_values(by="Count", ascending=False)
    pareto["Cum%"] = pareto["Count"].cumsum() / pareto["Count"].sum() * 100

    fig2 = go.Figure()

    fig2.add_bar(x=pareto["Issue Type"], y=pareto["Count"], name="Issues")

    fig2.add_scatter(
        x=pareto["Issue Type"],
        y=pareto["Cum%"],
        name="Cumulative %",
        yaxis="y2"
    )

    fig2.update_layout(
        yaxis2=dict(overlaying="y", side="right")
    )

    st.plotly_chart(fig2, use_container_width=True)


# ============================================
# 📈 DPV PAGE
# ============================================
elif page == "DPV":

    df = load_sheet("DPV")

    st.subheader("DPV Analysis")

    # ===== MONTH DROPDOWN =====
    months = df["Month"].dropna().unique()
    selected_month = st.selectbox("Select Month", months)

    df_filtered = df[df["Month"] == selected_month]

    # ===== KPIs =====
    col1, col2, col3 = st.columns(3)

    col1.metric("DPV %", float(df_filtered["DPV %"].values[0]))
    col2.metric("Paint Issues %", float(df_filtered["Paint issues %"].fillna(0).values[0]))
    col3.metric("Other Issues %", float(df_filtered["Other issues %"].fillna(0).values[0]))

    # ===== LINE GRAPH =====
    fig = go.Figure()

    fig.add_scatter(x=df["Month"], y=df["DPV %"], name="DPV %")
    fig.add_scatter(x=df["Month"], y=df["Paint issues %"], name="Paint %")
    fig.add_scatter(x=df["Month"], y=df["Other issues %"], name="Other %")

    st.plotly_chart(fig, use_container_width=True)


# ===== FOOTER =====
st.markdown("---")
st.caption("Developed by Surbhi | PDI Dashboard")
