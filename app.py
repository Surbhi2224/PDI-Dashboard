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
    df_grouped = df.groupby("Date")[["Plan","Actual","Pending"]].sum().reset_index()

    st.subheader("Executive Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("Offered", int(df_grouped["Plan"].sum()))
    col2.metric("Cleared", int(df_grouped["Actual"].sum()))
    col3.metric("Pending", int(df_grouped["Pending"].sum()))

    fig = go.Figure()
    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Actual"], name="Cleared")

    st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📅 DAILY CLEARING (FINAL MODEL-WISE)
# ============================================
elif page == "Daily_Clearing":

    df = load_sheet("Daily_Clearing")
    df = df.dropna(subset=["Date"])

    st.subheader("Daily Clearing (Model-wise)")

    # ===== DROPDOWN =====
    models = ["All"] + sorted(df["Model"].unique())
    selected_model = st.selectbox("Select Model", models)

    if selected_model != "All":
        df = df[df["Model"] == selected_model]

    # ===== KPI =====
    col1, col2, col3 = st.columns(3)
    col1.metric("Offered", int(df["Plan"].sum()))
    col2.metric("Cleared", int(df["Actual"].sum()))
    col3.metric("Pending", int(df["Pending"].sum()))

    # ===== MODEL-WISE GRAPH =====
    st.subheader("Model-wise Daily Clearing")

    fig = go.Figure()

    models = sorted(df["Model"].unique())

    colors = {
       colors = {
    "TR": "#4C78A8",
    "LR": "#F58518",
    "V1": "#54A24B",
    "V2": "#E45756",
    "V3": "#B279A2",
    "ARMOURED": "#FF9DA7"
}}
