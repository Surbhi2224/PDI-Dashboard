import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
from streamlit_autorefresh import st_autorefresh

# ===== CONFIG =====
pio.defaults.template = "plotly_dark"
st.set_page_config(layout="wide", page_title="PDI Dashboard")

# AUTO REFRESH
st_autorefresh(interval=5000, key="refresh")

# ===== HEADER =====
st.title("PDI Production Dashboard")
st.caption("Real-time Monitoring System")

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
    df = pd.DataFrame(client.open("PDI_Dashboard").worksheet(name).get_all_records())

    for col in ["Plan", "Actual", "Pending", "Count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    return df

# ===== SIDEBAR =====
pages = [
    "Executive_Summary","Daily_Clearing","Electrical_Issues",
    "Process_Issues","SQA_Issues","Paint_Issues",
    "Design_Issue","Testing_Issue","Water_Ingress","Major_Issues"
]

page = st.sidebar.radio("📂 Navigation", pages)

# ===== COLORS =====
model_colors = {
    "TR": "#1f77b4",
    "V1": "#2ca02c",
    "V2": "#ff7f0e",
    "V3": "#d62728",
    "LR": "#9467bd"
}

# ===== MODEL-WISE CHART =====
def model_chart(df):

    fig = go.Figure()

    models = df["Model"].unique()

    for model in models:
        temp = df[df["Model"] == model]

        fig.add_trace(go.Bar(
            x=temp["Date"],
            y=temp["Actual"],
            name=model,
            marker_color=model_colors.get(model, "#888")
        ))

    fig.update_layout(
        title="Model-wise Daily Clearance",
        barmode='group',
        xaxis_title="Date",
        yaxis_title="Actual"
    )

    return fig

# ===== BAR CHART =====
def bar_chart(df, x, y, title):
    df = df.sort_values(by=y, ascending=False).head(10)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df[x],
        y=df[y],
        text=df[y],
        textposition='outside'
    ))

    fig.update_layout(title=title)
    return fig

# ============================================
# 📊 EXECUTIVE SUMMARY
# ============================================
if page == "Executive_Summary":

    st.subheader("Executive Summary")

    df = load_sheet("Daily_Clearing")
    model_df = load_sheet("Model_Summary")

    total_plan = df["Plan"].sum()
    total_actual = df["Actual"].sum()

    col1, col2 = st.columns(2)
    col1.metric("Total Offered", int(total_plan))
    col2.metric("Total Cleared", int(total_actual))

    st.plotly_chart(bar_chart(model_df, "Model", "Plan", "Model Requirement"))

# ============================================
# 📅 DAILY CLEARING
# ============================================
elif page == "Daily_Clearing":

    st.subheader("Daily Clearing")

    df = load_sheet("Daily_Clearing")

    models = df["Model"].unique().tolist()
    selected = st.multiselect("Select Model", models, default=models)

    df = df[df["Model"].isin(selected)]

    st.plotly_chart(model_chart(df))

# ============================================
# 📊 ISSUE PAGES
# ============================================
elif page != "Major_Issues":

    st.subheader(page.replace("_", " "))

    df = load_sheet(page)

    issues = df["Issue Type"].unique().tolist()
    selected = st.multiselect("Select Issue Type", issues, default=issues)

    df = df[df["Issue Type"].isin(selected)]

    total_issues = int(df["Count"].sum())
    st.metric("Total Issues", total_issues)

    st.plotly_chart(bar_chart(df, "Issue Type", "Count", "Top 10 Issues"))

# ============================================
# 📋 MAJOR ISSUES
# ============================================
elif page == "Major_Issues":

    st.subheader("Major Issues")
    st.info("📄 Please check detailed data in Google Sheets")

# ===== FOOTER =====
st.markdown("---")
st.caption("Developed by Surbhi | PDI Dashboard")
