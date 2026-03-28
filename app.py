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

# ===== GOOGLE SHEETS CONNECTION =====
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

    # Fix numeric columns
    for col in ["Plan", "Actual", "Pending", "Count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Fix date
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

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

    df_grouped = df.groupby("Date")[["Plan","Actual","Pending"]].sum().reset_index()

    st.subheader("Executive Summary")

    col1, col2, col3 = st.columns(3)

    col1.metric("Offered", int(df_grouped["Plan"].sum()))
    col2.metric("Cleared", int(df_grouped["Actual"].sum()))
    col3.metric("Pending", int(df_grouped["Pending"].sum()))

    fig = go.Figure()

    fig.add_bar(
        x=df_grouped["Date"],
        y=df_grouped["Plan"],
        name="Offered",
        marker_color="#1f77b4"
    )

    fig.add_bar(
        x=df_grouped["Date"],
        y=df_grouped["Actual"],
        name="Cleared",
        marker_color="#2ca02c"
    )

    st.plotly_chart(fig, use_container_width=True)


# ============================================
# 📅 DAILY CLEARING (CLEAN VERSION)
# ============================================
elif page == "Daily_Clearing":

    df = load_sheet("Daily_Clearing")

    st.subheader("Daily Clearing Dashboard")

    # ===== DATE FILTER =====
    min_date = df["Date"].min()
    max_date = df["Date"].max()

    start, end = st.date_input("Select Date Range", [min_date, max_date])

    df = df[(df["Date"] >= pd.to_datetime(start)) & (df["Date"] <= pd.to_datetime(end))]

    # ===== MODEL DROPDOWN =====
    models = ["All"] + sorted(df["Model"].unique())
    selected_model = st.selectbox("Select Model", models)

    if selected_model != "All":
        df = df[df["Model"] == selected_model]

    # ===== KPI CARDS =====
    col1, col2, col3 = st.columns(3)

    col1.metric("Offered", int(df["Plan"].sum()))
    col2.metric("Cleared", int(df["Actual"].sum()))
    col3.metric("Pending", int(df["Pending"].sum()))

    # ===== CLEAN MODEL GRAPH (LIKE YOUR REFERENCE) =====
    st.subheader("Model Performance")

    summary = df.groupby("Model")[["Plan", "Actual", "Pending"]].sum().reset_index()
    summary = summary.sort_values(by="Actual", ascending=True)

    fig = go.Figure()

    fig.add_bar(
        y=summary["Model"],
        x=summary["Plan"],
        name="Offered",
        orientation='h',
        text=summary["Plan"],
        textposition="outside",
        marker_color="#1f77b4"
    )

    fig.add_bar(
        y=summary["Model"],
        x=summary["Actual"],
        name="Cleared",
        orientation='h',
        text=summary["Actual"],
        textposition="outside",
        marker_color="#2ca02c"
    )

    fig.update_layout(
        barmode='group',
        height=500,
        xaxis_title="Vehicles",
        yaxis_title="Model"
    )

    st.plotly_chart(fig, use_container_width=True)

    # ===== DAILY TREND =====
    st.subheader("Daily Trend")

    daily = df.groupby("Date")[["Plan", "Actual"]].sum().reset_index()

    fig2 = go.Figure()

    fig2.add_scatter(
        x=daily["Date"],
        y=daily["Plan"],
        name="Offered",
        mode='lines+markers'
    )

    fig2.add_scatter(
        x=daily["Date"],
        y=daily["Actual"],
        name="Cleared",
        mode='lines+markers'
    )

    st.plotly_chart(fig2, use_container_width=True)

    # ===== FORECAST =====
    st.subheader("Forecast")

    if len(daily) > 2:
        trend = np.poly1d(np.polyfit(range(len(daily)), daily["Actual"], 1))

        fig3 = go.Figure()

        fig3.add_scatter(
            x=daily["Date"],
            y=daily["Actual"],
            name="Actual"
        )

        fig3.add_scatter(
            x=daily["Date"],
            y=trend(range(len(daily))),
            name="Trend",
            line=dict(dash='dash')
        )

        st.plotly_chart(fig3, use_container_width=True)


# ============================================
# 📊 ISSUE PAGES (TOP 10 + PARETO)
# ============================================
elif page != "Major_Issues":

    df = load_sheet(page)

    st.subheader(page.replace("_", " "))

    # ===== DROPDOWN (CLEAN) =====
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
        textposition="outside",
        marker_color="#d62728"
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
        name="Cumulative %",
        line=dict(color="orange")
    )

    fig2.update_layout(
        yaxis2=dict(overlaying="y", side="right")
    )

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
