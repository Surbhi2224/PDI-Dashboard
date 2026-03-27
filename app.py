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

# AUTO REFRESH
st_autorefresh(interval=5000, key="refresh")

# ===== GOOGLE SHEETS =====
try:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"Error connecting to Google Sheets: {e}")

# ===== LOAD FUNCTION =====
@st.cache_data
def load_sheet(name):
    try:
        df = pd.DataFrame(client.open("PDI_Dashboard").worksheet(name).get_all_records())
        if "Model" in df.columns:
            df["Model"] = df["Model"].astype(str).str.strip()
        for col in ["Plan", "Actual", "Pending", "Count", "Requirement"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df
    except Exception as e:
        st.error(f"Error loading sheet {name}: {e}")
        return pd.DataFrame()

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

def bar_chart(df, x, y, title, top_n=None):
    fig = go.Figure()
    if top_n:
        df = df.sort_values(by=y, ascending=False).head(top_n)
    fig.add_trace(go.Bar(x=df[x], y=df[y], text=df[y], textposition='outside'))
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
        models = df["Model"].unique().tolist()
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

        st.subheader("🚗 Model Requirement")
        st.plotly_chart(bar_chart(model_df, "Model", "Requirement", "Model Requirement"))

        st.subheader("📈 Daily Performance")
        st.plotly_chart(column_chart(df, "Date", "Plan", "Actual", "Daily Performance"))

# ============================================
# 📅 DAILY CLEARING
# ============================================
elif page == "Daily_Clearing":
    df = load_sheet("Daily_Clearing")
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        models = df["Model"].unique().tolist()
        model = st.selectbox("🚗 Select Model", ["All"] + models)
        if model != "All":
            df = df[df["Model"] == model]

        start, end = st.date_input("📅 Date Range", [df['Date'].min(), df['Date'].max()])
        df = df[(df['Date'] >= pd.to_datetime(start)) & (df['Date'] <= pd.to_datetime(end))]

        st.subheader("📊 Daily Plan vs Actual")
        st.plotly_chart(column_chart(df, "Date", "Plan", "Actual", "Daily"))

        df['Month'] = df['Date'].dt.to_period('M').astype(str)
        monthly = df.groupby('Month')[['Plan','Actual']].sum().reset_index()
        st.subheader("📈 Monthly Trend")
        st.plotly_chart(stacked_chart(monthly, "Month", "Plan", "Actual", "Monthly"))

        st.subheader("🔮 Forecast")
        df = df.sort_values('Date')
        df['Trend'] = np.poly1d(np.polyfit(range(len(df)), df['Actual'], 1))(range(len(df)))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Actual'], name="Actual"))
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Trend'], name="Trend"))
        st.plotly_chart(fig)

# ============================================
# 📊 ISSUE PAGES (TOP 10 + Dropdown Filter)
# ============================================
elif page != "Major_Issues":
    df = load_sheet(page)
    if not df.empty and "Issue Type" in df.columns and "Count" in df.columns:
        issues = df["Issue Type"].unique().tolist()
        selected = st.multiselect("🔍 Select Issues", issues, default=issues)
        if selected:
            df = df[df["Issue Type"].isin(selected)]

        st.subheader("📊 Top 10 Issues")
        st.plotly_chart(bar_chart(df, "Issue Type", "Count", f"Top 10 Issues - {page}", top_n=10))

        st.metric("Total Issues", int(df["Count"].sum()))

        # Pareto chart
        pareto = df.groupby("Issue Type")["Count"].sum().reset_index()
        pareto = pareto.sort_values(by="Count", ascending=False)
        pareto["Cum%"] = pareto["Count"].cumsum() / pareto["Count"].sum() * 100

        figp = go.Figure()
        figp.add_trace(go.Bar(x=pareto["Issue Type"], y=pareto["Count"]))
        figp.add_trace(go.Scatter(x=pareto["Issue Type"], y=pareto["Cum%"], yaxis='y2'))
        figp.update_layout(yaxis2=dict(overlaying='y', side='right'))
        st.subheader("📊 Pareto Analysis")
        st.plotly_chart(figp)
    else:
        st.info("No data available for this page.")

# ============================================
# 📋 MAJOR ISSUES
# ============================================
elif page == "Major_Issues":
    st.info("📄 Please check detailed data in Google Sheets")

# ===== FOOTER =====
st.markdown("---")
st.caption("Developed by Surbhi | PDI Dashboard")
