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

    df.columns = df.columns.str.strip()

    for col in df.columns:
        if "Count" in col or col in ["Plan", "Actual", "Pending"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    return df

# ===== SIDEBAR =====
pages = [
    "Executive_Summary","Daily_Clearing","Electrical_Issues",
    "Process_Issues","SQA_Issues","Paint_Issues",
    "Design_Issue","Testing_Issue","Water_Ingress","Major_Issues","DPV"
]

page = st.sidebar.selectbox("Navigation", pages)

# ============================================
# 📊 EXECUTIVE SUMMARY
# ============================================
if page == "Executive_Summary":

    df = load_sheet("Daily_Clearing")
    df_grouped = df.groupby("Date")[["Plan","Actual","Pending"]].sum().reset_index()

    col1, col2, col3 = st.columns(3)

    col1.metric("Plan", int(df_grouped["Plan"].sum()))
    col2.metric("Actual", int(df_grouped["Actual"].sum()))
    col3.metric("Pending", int(df_grouped["Pending"].sum()))

    fig = go.Figure()

    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Plan"], name="Plan", marker_color="blue")
    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Actual"], name="Actual", marker_color="green")
    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Pending"], name="Pending", marker_color="orange")

    fig.update_layout(barmode="group")

    st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📅 DAILY CLEARING (STACKED CLEAN)
# ============================================
elif page == "Daily_Clearing":

    df = load_sheet("Daily_Clearing")

    st.subheader("Daily Clearing")

    models = sorted(df["Model"].unique())
    selected_models = st.multiselect("Select Model", models, default=models)

    df = df[df["Model"].isin(selected_models)]

    df_grouped = df.groupby("Date")[["Plan","Actual","Pending"]].sum().reset_index()

    col1, col2, col3 = st.columns(3)

    col1.metric("Plan", int(df_grouped["Plan"].sum()))
    col2.metric("Actual", int(df_grouped["Actual"].sum()))
    col3.metric("Pending", int(df_grouped["Pending"].sum()))

    fig = go.Figure()

    fig.add_bar(
        x=df_grouped["Date"],
        y=df_grouped["Actual"],
        name="Actual",
        marker_color="green",
        text=df_grouped["Actual"],
        textposition="outside"
    )

    fig.add_bar(
        x=df_grouped["Date"],
        y=df_grouped["Pending"],
        name="Pending",
        marker_color="orange"
    )

    fig.update_layout(barmode="stack")

    st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📊 ISSUE PAGES (MONTH-WISE + PARETO)
# ============================================
elif page not in ["Major_Issues", "DPV"]:

    df = load_sheet(page)

    st.subheader(page.replace("_", " "))

    # ===== MONTH DROPDOWN =====
    month_map = {
        "March": "Count(March)",
        "April": "Count (April)"
    }

    selected_month = st.selectbox("Select Month", list(month_map.keys()))

    count_col = month_map[selected_month]

    if count_col not in df.columns:
        st.error(f"{count_col} column not found")
        st.stop()

    # ===== ISSUE FILTER =====
    issues = df["Issue Type"].dropna().unique().tolist()
    selected_issue = st.selectbox("Select Issue", ["All"] + issues)

    if selected_issue != "All":
        df = df[df["Issue Type"] == selected_issue]

    st.metric("Total Issues", int(df[count_col].sum()))

    # ===== TOP 10 =====
    top10 = df.groupby("Issue Type")[count_col].sum().nlargest(10).reset_index()

    fig = go.Figure()

    fig.add_bar(
        x=top10["Issue Type"],
        y=top10[count_col],
        text=top10[count_col],
        textposition="outside",
        marker_color="#4C78A8"
    )

    st.plotly_chart(fig, use_container_width=True)

    # ===== PARETO =====
    st.subheader("Pareto Analysis")

    pareto = df.groupby("Issue Type")[count_col].sum().reset_index()
    pareto = pareto.sort_values(by=count_col, ascending=False)

    pareto["Cum%"] = pareto[count_col].cumsum() / pareto[count_col].sum() * 100

    fig2 = go.Figure()

    fig2.add_bar(
        x=pareto["Issue Type"],
        y=pareto[count_col],
        name="Count",
        marker_color="#F28E2B"
    )

    fig2.add_scatter(
        x=pareto["Issue Type"],
        y=pareto["Cum%"],
        yaxis="y2",
        name="Cum%",
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

    fig.add_bar(x=df["Month"], y=df["DPV %"], name="DPV", marker_color="blue")
    fig.add_bar(x=df["Month"], y=df["Paint issues %"], name="Paint", marker_color="red")
    fig.add_bar(x=df["Month"], y=df["Other issues %"], name="Other", marker_color="green")

    st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📋 MAJOR ISSUES
# ============================================
else:
    st.subheader("Major Issues")
    st.info("Check Google Sheet for details")

# ===== FOOTER =====
st.markdown("---")
st.caption("Developed by Surbhi | PDI Dashboard")

		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
