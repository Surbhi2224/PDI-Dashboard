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

    for col in df.columns:
        if col not in ["Date", "Model", "Issue Type", "Month"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    return df

# ===== SIDEBAR =====
pages = [
    "Executive_Summary","Daily_Clearing","DPV",
    "Electrical_Issues","Process_Issues","SQA_Issues",
    "Paint_Issues","Design_Issue","Testing_Issue","Water_Ingress",
    "Major_Issues"
]

page = st.sidebar.selectbox("Navigation", pages)

# ============================================
# 📊 EXECUTIVE SUMMARY
# ============================================
if page == "Executive_Summary":

    df = load_sheet("Daily_Clearing")

    df_grouped = df.groupby("Date")[["Plan","Actual","Pending"]].sum().reset_index()

    col1, col2, col3 = st.columns(3)

    col1.metric("Offered", int(df_grouped["Plan"].sum()))
    col2.metric("Cleared", int(df_grouped["Actual"].sum()))
    col3.metric("Pending", int(df_grouped["Pending"].sum()))

    fig = go.Figure()

    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Plan"],
                name="Plan", marker_color="#1f77b4")

    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Actual"],
                name="Actual", marker_color="#2ca02c")

    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Pending"],
                name="Pending", marker_color="#ff7f0e")

    fig.update_layout(barmode="group")

    st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📅 DAILY CLEARING (STACKED CLEAN GRAPH)
# ============================================
elif page == "Daily_Clearing":

    df = load_sheet("Daily_Clearing")

    st.subheader("Daily Clearing")

    models = ["All"] + sorted(df["Model"].unique())
    selected_model = st.selectbox("Select Model", models)

    if selected_model != "All":
        df = df[df["Model"] == selected_model]

    df_grouped = df.groupby("Date")[["Plan","Actual","Pending"]].sum().reset_index()

    col1, col2, col3 = st.columns(3)
    col1.metric("Plan", int(df_grouped["Plan"].sum()))
    col2.metric("Actual", int(df_grouped["Actual"].sum()))
    col3.metric("Pending", int(df_grouped["Pending"].sum()))

    # ===== STACKED GRAPH =====
    fig = go.Figure()

    fig.add_bar(
        x=df_grouped["Date"],
        y=df_grouped["Actual"],
        name="Actual",
        marker_color="#2ca02c",
        text=df_grouped["Actual"],
        textposition="inside"
    )

    fig.add_bar(
        x=df_grouped["Date"],
        y=df_grouped["Pending"],
        name="Pending",
        marker_color="#ff7f0e",
        text=df_grouped["Pending"],
        textposition="inside"
    )

    fig.update_layout(
        barmode="stack",
        xaxis_title="Date",
        yaxis_title="Vehicles"
    )

    st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📊 ISSUE PAGES (AUTO MONTH - WIDE FORMAT)
# ============================================
elif page not in ["Major_Issues", "DPV"]:

    df = load_sheet(page)

    st.subheader(page.replace("_", " "))

    month_cols = [col for col in df.columns if col != "Issue Type"]

    selected_month = st.selectbox("Select Month", month_cols)

    df_work = df[["Issue Type", selected_month]].copy()
    df_work.rename(columns={selected_month: "Count"}, inplace=True)

    issues = df_work["Issue Type"].dropna().unique().tolist()
    selected_issue = st.selectbox("Select Issue", ["All"] + issues)

    if selected_issue != "All":
        df_work = df_work[df_work["Issue Type"] == selected_issue]

    st.metric("Total Issues", int(df_work["Count"].sum()))

    # ===== TOP 10 =====
    top10 = df_work.groupby("Issue Type")["Count"].sum().nlargest(10).reset_index()

    fig = go.Figure()

    fig.add_bar(
        x=top10["Issue Type"],
        y=top10["Count"],
        text=top10["Count"],
        textposition="outside",
        marker_color="#4C78A8"
    )

    st.plotly_chart(fig, use_container_width=True)

    # ===== PARETO =====
    st.subheader("Pareto Analysis")

    pareto = df_work.groupby("Issue Type")["Count"].sum().reset_index()
    pareto = pareto.sort_values(by="Count", ascending=False)

    pareto["Cum%"] = pareto["Count"].cumsum() / pareto["Count"].sum() * 100

    fig2 = go.Figure()

    fig2.add_bar(
        x=pareto["Issue Type"],
        y=pareto["Count"],
        name="Count",
        marker_color="#F28E2B"
    )

    fig2.add_scatter(
        x=pareto["Issue Type"],
        y=pareto["Cum%"],
        yaxis="y2",
        name="Cumulative %",
        mode="lines+markers"
    )

    fig2.add_hline(y=80, line_dash="dash", line_color="red")

    fig2.update_layout(yaxis2=dict(overlaying="y", side="right"))

    st.plotly_chart(fig2, use_container_width=True)

# ============================================
# 📈 DPV PAGE
# ============================================
elif page == "DPV":

    df = load_sheet("DPV")

    st.subheader("DPV Analysis")

    months = df["Month"].dropna().unique()
    selected_month = st.selectbox("Select Month", months)

    df = df[df["Month"] == selected_month]

    fig = go.Figure()

    fig.add_bar(x=df["Month"], y=df["DPV %"], name="DPV %")
    fig.add_bar(x=df["Month"], y=df["Paint issues %"], name="Paint %")
    fig.add_bar(x=df["Month"], y=df["Other issues %"], name="Other %")

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
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
