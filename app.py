import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
from streamlit_autorefresh import st_autorefresh

# ===== CONFIG =====
pio.defaults.template = "plotly_dark"
st.set_page_config(layout="wide", page_title="PDI Dashboard")

# AUTO REFRESH
st_autorefresh(interval=5000, key="refresh")

# ===== HEADER WITH LOGO =====
col1, col2 = st.columns([1,5])
with col1:
    st.image("logo.jpg", width=120)  # changed to jpg
with col2:
    st.title("PDI Production Dashboard")
    st.caption("Real-time Monitoring System")

# ===== GOOGLE SHEETS =====
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "C:/Users/Surbhi-TRN0374/Desktop/PDI_Dashboard/credentials.json", scope
)
client = gspread.authorize(creds)

# ===== LOAD =====
@st.cache_data
def load_sheet(name):
    df = pd.DataFrame(client.open("PDI_Dashboard").worksheet(name).get_all_records())
    if "Model" in df.columns:
        df["Model"] = df["Model"].astype(str).str.strip()
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
    fig.add_trace(go.Bar(x=df[x], y=df[y1], name="Plan", marker_color='blue'))
    fig.add_trace(go.Bar(x=df[x], y=df[y2], name="Actual", marker_color='red'))
    fig.update_layout(title=title, barmode='group')
    return fig

def stacked_chart(df, x, y1, y2, title):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df[x], y=df[y1], name="Plan", marker_color='blue'))
    fig.add_trace(go.Bar(x=df[x], y=df[y2], name="Actual", marker_color='red'))
    fig.update_layout(title=title, barmode='stack')
    return fig

def bar_chart(df, x, y, title):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df[x], y=df[y], text=df[y], textposition='outside'))
    fig.update_layout(title=title)
    return fig

# ============================================
# 📊 EXECUTIVE SUMMARY
# ============================================
if page == "Executive_Summary":

    df = load_sheet("Daily_Clearing")
    model_df = load_sheet("Model_Summary")

    df['Date'] = pd.to_datetime(df['Date'])

    models = df["Model"].unique().tolist()
    model = st.selectbox("🚗 Select Model", ["All"] + models)

    if model != "All":
        df = df[df["Model"] == model]

    start, end = st.date_input("📅 Date Range",
                              [df['Date'].min(), df['Date'].max()])
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    df = df[(df['Date'] >= start) & (df['Date'] <= end)]

    total_plan = df["Plan"].sum()
    total_actual = df["Actual"].sum()
    efficiency = (total_actual / total_plan * 100)

    # ===== KPI CARDS =====
    col1, col2, col3 = st.columns(3)

    col1.markdown(f"""
    <div style="background-color:#1f77b4;padding:20px;border-radius:10px;text-align:center">
    <h3>Total Offered</h3>
    <h2>{total_plan}</h2>
    </div>
    """, unsafe_allow_html=True)

    col2.markdown(f"""
    <div style="background-color:#2ca02c;padding:20px;border-radius:10px;text-align:center">
    <h3>Total Cleared</h3>
    <h2>{total_actual}</h2>
    </div>
    """, unsafe_allow_html=True)

    col3.markdown(f"""
    <div style="background-color:#d62728;padding:20px;border-radius:10px;text-align:center">
    <h3>Efficiency %</h3>
    <h2>{efficiency:.2f}%</h2>
    </div>
    """, unsafe_allow_html=True)

    # MODEL
    st.subheader("🚗 Model Requirement")
    st.plotly_chart(bar_chart(model_df, "Model", "Requirement", "Model Requirement"))

    # TREND
    st.subheader("📈 Performance")
    st.plotly_chart(column_chart(df, "Date", "Plan", "Actual", "Daily Performance"))

# ============================================
# 📅 DAILY CLEARING
# ============================================
elif page == "Daily_Clearing":

    df = load_sheet("Daily_Clearing")
    df['Date'] = pd.to_datetime(df['Date'])

    models = df["Model"].unique().tolist()
    model = st.selectbox("🚗 Select Model", ["All"] + models)

    if model != "All":
        df = df[df["Model"] == model]

    start, end = st.date_input("📅 Date Range",
                              [df['Date'].min(), df['Date'].max()])
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    df = df[(df['Date'] >= start) & (df['Date'] <= end)]

    # DAILY
    st.subheader("📊 Daily Plan vs Actual")
    st.plotly_chart(column_chart(df, "Date", "Plan", "Actual", "Daily"))

    # MONTHLY
    df['Month'] = df['Date'].dt.to_period('M').astype(str)
    monthly = df.groupby('Month')[['Plan','Actual']].sum().reset_index()

    st.subheader("📈 Monthly Trend")
    st.plotly_chart(stacked_chart(monthly, "Month", "Plan", "Actual", "Monthly"))

    # FORECAST
    st.subheader("🔮 Forecast")
    df = df.sort_values('Date')
    df['Trend'] = np.poly1d(np.polyfit(range(len(df)), df['Actual'], 1))(range(len(df)))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Actual'], name="Actual"))
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Trend'], name="Trend", line=dict(color='red')))
    st.plotly_chart(fig)

# ============================================
# 📊 ISSUE PAGES
# ============================================
elif page != "Major_Issues":

    df = load_sheet(page)

    if "Model" in df.columns:
        models = df["Model"].unique().tolist()
        model = st.selectbox("🚗 Select Model", ["All"] + models)
        if model != "All":
            df = df[df["Model"] == model]

    if "Date" in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        start, end = st.date_input("📅 Date Range",
                                  [df['Date'].min(), df['Date'].max()])
        start = pd.to_datetime(start)
        end = pd.to_datetime(end)
        df = df[(df['Date'] >= start) & (df['Date'] <= end)]

    issues = df["Issue Type"].unique().tolist()
    selected = st.multiselect("🔍 Select Issues", issues)

    if selected:
        df = df[df["Issue Type"].isin(selected)]

    st.metric("Total Issues", df["Count"].sum())

    st.plotly_chart(bar_chart(df, "Issue Type", "Count", page))

    # PARETO
    st.subheader("📊 Pareto Analysis")
    pareto = df.groupby("Issue Type")["Count"].sum().reset_index()
    pareto = pareto.sort_values(by="Count", ascending=False)
    pareto["Cum%"] = pareto["Count"].cumsum()/pareto["Count"].sum()*100

    figp = go.Figure()
    figp.add_trace(go.Bar(x=pareto["Issue Type"], y=pareto["Count"]))
    figp.add_trace(go.Scatter(x=pareto["Issue Type"], y=pareto["Cum%"],
                             yaxis='y2', line=dict(color='red')))
    figp.update_layout(yaxis2=dict(overlaying='y', side='right'))

    st.plotly_chart(figp)

# ============================================
# 📋 MAJOR ISSUES
# ============================================
elif page == "Major_Issues":
    st.info("📄 Please check detailed data in Google Sheets")

# ===== FOOTER =====
st.markdown("---")
st.caption("Developed by Surbhi | PDI Dashboard")