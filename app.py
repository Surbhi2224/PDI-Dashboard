import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
from streamlit_autorefresh import st_autorefresh

# ===== CONFIG =====
pio.templates.default = "plotly_dark"
st.set_page_config(layout="wide", page_title="PDI Dashboard")

# ===== AUTO REFRESH =====
st_autorefresh(interval=5000, key="refresh")

# ===== GOOGLE SHEETS =====
@st.cache_resource
def gsheet_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    return gspread.authorize(creds)

client = gsheet_client()

# ===== LOAD FUNCTION =====
@st.cache_data
def load_sheet(sheet_name):
    try:
        ws = client.open("PDI_Dashboard").worksheet(sheet_name)
        df = pd.DataFrame(ws.get_all_records())
    except Exception as e:
        st.error(f"Error loading sheet {sheet_name}: {e}")
        # Fallback empty DataFrame
        df = pd.DataFrame()
    return df

# ===== SIDEBAR =====
pages = [
    "Executive_Summary","Daily_Clearing","Electrical_Issues",
    "Process_Issues","SQA_Issues","Paint_Issues",
    "Design_Issue","Testing_Issue","Water_Ingress","Major_Issues"
]
page = st.sidebar.radio("📂 Navigation", pages)

# ===== CHART FUNCTIONS =====
def column_chart(df, x, y1, y2, title):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df[x], y=df[y1], name="Plan"))
    fig.add_trace(go.Bar(x=df[x], y=df[y2], name="Actual"))
    fig.update_layout(title=title, barmode='group')
    return fig

def stacked_chart(df, x, y1, y2, title):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df[x], y=df[y1], name="Plan"))
    fig.add_trace(go.Bar(x=df[x], y=df[y2], name="Actual"))
    fig.update_layout(title=title, barmode='stack')
    return fig

def bar_chart_top10(df, x, y, title):
    # Only top 10
    df_top = df.sort_values(by=y, ascending=False).head(10)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_top[x], y=df_top[y], text=df_top[y], textposition='outside'))
    fig.update_layout(title=title)
    return fig

# ============================================
# 📊 EXECUTIVE SUMMARY
# ============================================
if page == "Executive_Summary":

    df = load_sheet("Daily_Clearing")
    model_df = load_sheet("Model_Summary")

    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        models = df["Model"].astype(str).unique().tolist()
        model = st.selectbox("🚗 Select Model", ["All"] + models)

        if model != "All":
            df = df[df["Model"] == model]

        start, end = st.date_input("📅 Date Range", [df['Date'].min(), df['Date'].max()])
        df = df[(df['Date'] >= pd.to_datetime(start)) & (df['Date'] <= pd.to_datetime(end))]

        total_plan = df["Plan"].sum()
        total_actual = df["Actual"].sum()
        efficiency = (total_actual / total_plan * 100) if total_plan > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Offered", int(total_plan))
        col2.metric("Total Cleared", int(total_actual))
        col3.metric("Efficiency %", f"{efficiency:.2f}%")

        st.subheader("📈 Daily Performance")
        st.plotly_chart(column_chart(df, "Date", "Plan", "Actual", "Daily Performance"))

# ============================================
# 📅 DAILY CLEARING
# ============================================
elif page == "Daily_Clearing":
    df = load_sheet("Daily_Clearing")
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        models = df["Model"].astype(str).unique().tolist()
        model = st.selectbox("🚗 Select Model", ["All"] + models)
        if model != "All":
            df = df[df["Model"] == model]

        start, end = st.date_input("📅 Date Range", [df['Date'].min(), df['Date'].max()])
        df = df[(df['Date'] >= pd.to_datetime(start)) & (df['Date'] <= pd.to_datetime(end))]

        st.subheader("📊 Daily Plan vs Actual")
        st.plotly_chart(column_chart(df, "Date", "Plan", "Actual", "Daily"))

# ============================================
# 📊 ISSUE PAGES (TOP 10)
# ============================================
elif page != "Major_Issues":
    df = load_sheet(page)
    if not df.empty and "Issue Type" in df.columns and "Count" in df.columns:
        st.subheader(f"🔝 Top 10 Issues - {page}")
        st.plotly_chart(bar_chart_top10(df, "Issue Type", "Count", f"Top 10 Issues - {page}"))

# ============================================
# 📋 MAJOR ISSUES
# ============================================
elif page == "Major_Issues":
    st.info("📄 Please check detailed data in Google Sheets")

# ===== FOOTER =====
st.markdown("---")
st.caption("Developed by Surbhi | PDI Dashboard")
