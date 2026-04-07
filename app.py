import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ===== CONFIG =====
st.set_page_config(layout="wide", page_title="PDI Dashboard")

# ===== PREMIUM UI =====
st.markdown("""
<style>

/* BACKGROUND */
body {
    background-color: #020617;
    color: white;
}

/* KPI CARD */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #0f172a, #020617);
    border-radius: 15px;
    padding: 20px;
    border-left: 5px solid #00f5d4;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
}

/* LABEL */
[data-testid="stMetricLabel"] {
    color: #9ca3af;
    font-size: 14px;
}

/* VALUE */
[data-testid="stMetricValue"] {
    color: #00f5d4;
    font-size: 40px;
    font-weight: bold;
}

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background-color: #020617;
}

</style>
""", unsafe_allow_html=True)

st_autorefresh(interval=5000, key="refresh")

st.title("🚗 PDI Production Dashboard")

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

# ===== LOAD =====
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
    "Executive_Summary",
    "Daily_Clearing",
    "Model_Summary",
    "DPV",
    "Electrical_Issues",
    "Process_Issues",
    "SQA_Issues",
    "Paint_Issues",
    "Design_Issue",
    "Testing_Issue",
    "Water_Ingress",
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
                name="Plan", marker_color="#3b82f6")

    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Actual"],
                name="Actual", marker_color="#00f5d4")

    fig.add_bar(x=df_grouped["Date"], y=df_grouped["Pending"],
                name="Pending", marker_color="#ef4444")

    fig.update_layout(
        barmode="group",
        template="plotly_dark",
        transition_duration=800
    )

    st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📅 DAILY CLEARING (STACKED - CLEAN)
# ============================================
elif page == "Daily_Clearing":

    df = load_sheet("Daily_Clearing")

    st.subheader("📅 Daily Clearing")

    models = ["All"] + sorted(df["Model"].dropna().unique())
    selected_model = st.selectbox("Select Model", models)

    if selected_model != "All":
        df = df[df["Model"] == selected_model]

    df_grouped = df.groupby("Date")[["Actual","Pending"]].sum().reset_index()

    col1, col2 = st.columns(2)
    col1.metric("Cleared", int(df_grouped["Actual"].sum()))
    col2.metric("Pending", int(df_grouped["Pending"].sum()))

    fig = go.Figure()

    fig.add_bar(
        x=df_grouped["Date"],
        y=df_grouped["Actual"],
        name="Cleared",
        marker_color="#00f5d4",
        text=df_grouped["Actual"],
        textposition="inside"
    )

    fig.add_bar(
        x=df_grouped["Date"],
        y=df_grouped["Pending"],
        name="Pending",
        marker_color="#ef4444",
        text=df_grouped["Pending"],
        textposition="inside"
    )

    fig.update_layout(
        barmode="stack",
        template="plotly_dark",
        transition_duration=800
    )

    st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📊 MODEL SUMMARY
# ============================================
elif page == "Model_Summary":

    df = load_sheet("Model_Summary")

    months = sorted(df["Month"].dropna().unique())
    selected_month = st.selectbox("Select Month", months)

    df = df[df["Month"] == selected_month]

    col1, col2, col3 = st.columns(3)
    col1.metric("Requirement", int(df["Requirement"].sum()))
    col2.metric("Cleared", int(df["Cleared"].sum()))
    col3.metric("Pending", int(df["Pending"].sum()))

    fig = go.Figure()

    fig.add_bar(x=df["Model"], y=df["Cleared"],
                name="Cleared", marker_color="#00f5d4")

    fig.add_bar(x=df["Model"], y=df["Pending"],
                name="Pending", marker_color="#ef4444")

    fig.update_layout(barmode="stack", template="plotly_dark")

    st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📈 DPV
# ============================================
elif page == "DPV":

    df = load_sheet("DPV")

    months = df["Month"].dropna().unique()
    selected_month = st.selectbox("Select Month", months)

    df = df[df["Month"] == selected_month]

    fig = go.Figure()

    fig.add_bar(x=df["Month"], y=df["DPV %"], name="DPV %")
    fig.add_bar(x=df["Month"], y=df["Paint issues %"], name="Paint")
    fig.add_bar(x=df["Month"], y=df["Other issues %"], name="Other")

    fig.update_layout(template="plotly_dark")

    st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📊 ISSUE PAGES + PARETO
# ============================================
elif page != "Major_Issues":

    df = load_sheet(page)

    issues = sorted(df["Issue Type"].dropna().unique())
    selected_issue = st.selectbox("Search Issue", ["All"] + issues)

    if selected_issue != "All":
        df = df[df["Issue Type"] == selected_issue]

    month_cols = [c for c in df.columns if c not in ["Model","Issue Type"]]
    selected_month = st.selectbox("Select Month", month_cols)

    df_work = df[["Issue Type", selected_month]].copy()
    df_work.columns = ["Issue Type", "Count"]

    st.metric("Total Issues", int(df_work["Count"].sum()))

    top10 = df_work.sort_values(by="Count", ascending=False).head(10)

    fig = go.Figure()
    fig.add_bar(
        x=top10["Issue Type"],
        y=top10["Count"],
        text=top10["Count"],
        textposition="outside"
    )
    fig.update_layout(template="plotly_dark")

    st.plotly_chart(fig, use_container_width=True)

    # ===== PARETO =====
    st.subheader("Pareto Analysis")

    pareto = df_work.sort_values(by="Count", ascending=False)
    pareto["Cum%"] = pareto["Count"].cumsum() / pareto["Count"].sum() * 100

    fig2 = go.Figure()
    fig2.add_bar(x=pareto["Issue Type"], y=pareto["Count"])

    fig2.add_scatter(
        x=pareto["Issue Type"],
        y=pareto["Cum%"],
        yaxis="y2",
        mode="lines+markers"
    )

    fig2.update_layout(
        template="plotly_dark",
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
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
