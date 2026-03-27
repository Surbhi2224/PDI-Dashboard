import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
import numpy as np
from streamlit_autorefresh import st_autorefresh

# ===== CONFIG =====
st.set_page_config(layout="wide", page_title="PDI Dashboard")

# AUTO REFRESH
st_autorefresh(interval=5000, key="refresh")

# ===== GOOGLE SHEETS =====
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"])
client = gspread.authorize(creds)

# ===== LOAD FUNCTION =====
@st.cache_data
def load_sheet(name):
    try:
        df = pd.DataFrame(client.open("PDI_Dashboard").worksheet(name).get_all_records())
    except Exception as e:
        st.error(f"Error loading sheet {name}: {e}")
        return pd.DataFrame()

    # Strip Model names
    if "Model" in df.columns:
        df["Model"] = df["Model"].astype(str).str.strip()

    # Fix numeric columns
    for col in ["Plan", "Actual", "Pending", "Count", "Requirement"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

# ===== SIDEBAR =====
pages = [
    "Executive_Summary","Daily_Clearing","Electrical_Issues",
    "Process_Issues","SQA_Issues","Paint_Issues",
    "Design_Issue","Testing_Issue","Water_Ingress","Major_Issues"
]
page = st.sidebar.radio("📂 Navigation", pages)

# ===== LOAD SHEET =====
df = load_sheet(page)

# ===== METRICS =====
if page in ["Executive_Summary", "Daily_Clearing"]:
    total_plan = df["Plan"].sum()
    total_actual = df["Actual"].sum()
    efficiency = (total_actual / total_plan * 100) if total_plan > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Offered", int(total_plan))
    col2.metric("Total Cleared", int(total_actual))
    col3.metric("Efficiency %", f"{efficiency:.2f}%")

elif page not in ["Major_Issues", "Executive_Summary", "Daily_Clearing"]:
    st.metric("Total Issues", int(df["Count"].sum()))

# ===== DROPDOWNS =====
if "Model" in df.columns:
    models = df["Model"].unique().tolist()
    model = st.selectbox("🚗 Select Model", ["All"] + models)
    if model != "All":
        df = df[df["Model"] == model]

if "Date" in df.columns:
    df['Date'] = pd.to_datetime(df['Date'])
    start, end = st.date_input("📅 Date Range", [df['Date'].min(), df['Date'].max()])
    df = df[(df['Date'] >= pd.to_datetime(start)) & (df['Date'] <= pd.to_datetime(end))]

# ===== CHART FUNCTIONS =====
def column_chart(df, x, y1, y2, title):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df[x], y=df[y1], name="Plan", marker_color="blue"))
    fig.add_trace(go.Bar(x=df[x], y=df[y2], name="Actual", marker_color="green"))
    fig.update_layout(title=title, barmode='group')
    return fig

def stacked_chart(df, x, y1, y2, title):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df[x], y=df[y1], name="Plan", marker_color="blue"))
    fig.add_trace(go.Bar(x=df[x], y=df[y2], name="Actual", marker_color="green"))
    fig.update_layout(title=title, barmode='stack')
    return fig

def bar_chart(df, x, y, title, top_n=None):
    if top_n:
        df = df.sort_values(y, ascending=False).head(top_n)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df[x], y=df[y], text=df[y], textposition='outside', marker_color="orange"))
    fig.update_layout(title=title)
    return fig

# ===== EXECUTIVE SUMMARY =====
if page == "Executive_Summary":
    model_df = load_sheet("Model_Summary")
    st.subheader("🚗 Model Requirement")
    st.plotly_chart(bar_chart(model_df, "Model", "Requirement", "Model Requirement"))

    st.subheader("📈 Daily Performance")
    st.plotly_chart(column_chart(df, "Date", "Plan", "Actual", "Daily Performance"))

# ===== DAILY CLEARING =====
elif page == "Daily_Clearing":
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

# ===== ISSUE PAGES =====
elif page not in ["Executive_Summary", "Daily_Clearing", "Major_Issues"]:
    st.subheader(f"📊 Top 10 Issues - {page}")
    st.plotly_chart(bar_chart(df, "Issue Type", "Count", f"Top 10 Issues - {page}", top_n=10))

# ===== MAJOR ISSUES =====
elif page == "Major_Issues":
    st.info("📄 Please check detailed data in Google Sheets")

# ===== FOOTER =====
st.markdown("---")
st.caption("Developed by Surbhi | PDI Dashboard")
