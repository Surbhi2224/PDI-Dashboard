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

page = st.sidebar.selectbox("Navigation", pages)

# ============================================
# 📊 EXECUTIVE SUMMARY
# ============================================
if page == "Executive_Summary":

    df = load_sheet("Daily_Clearing")

    st.subheader("Executive Summary")

    st.markdown(f"### Offered: {int(df['Plan'].sum())}")
    st.markdown(f"### Cleared: {int(df['Actual'].sum())}")
    st.markdown(f"### Pending: {int(df['Pending'].sum())}")

    fig = go.Figure()
    fig.add_bar(x=df["Date"], y=df["Plan"], name="Offered", marker_color="blue")
    fig.add_bar(x=df["Date"], y=df["Pending"], name="Pending", marker_color="orange")

    st.plotly_chart(fig, use_container_width=True)


# ============================================
# 📅 DAILY CLEARING
# ============================================
elif page == "Daily_Clearing":

    df = load_sheet("Daily_Clearing")

    st.subheader("Daily Clearing")

    # ===== DROPDOWN =====
    models = ["All"] + sorted(df["Model"].unique())
    selected_model = st.selectbox("Select Model", models)

    if selected_model != "All":
        df = df[df["Model"] == selected_model]

    # ===== TOP NUMBERS =====
    st.markdown(f"### Offered: {int(df['Plan'].sum())}")
    st.markdown(f"### Cleared: {int(df['Actual'].sum())}")
    st.markdown(f"### Pending: {int(df['Pending'].sum())}")

    # ===== MODEL-WISE COLOR CHART =====
    st.subheader("Model-wise Performance")

    fig = go.Figure()

    models = df["Model"].unique()

    colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c",
        "#d62728", "#9467bd", "#8c564b"
    ]

    for i, model in enumerate(models):
        model_df = df[df["Model"] == model]

        fig.add_bar(
            x=model_df["Date"],
            y=model_df["Actual"],
            name=model,
            marker_color=colors[i % len(colors)]
        )

    fig.update_layout(barmode="group")

    st.plotly_chart(fig, use_container_width=True)

    # ===== FORECAST =====
    st.subheader("Forecast")

    df = df.sort_values("Date")

    if len(df) > 2:
        trend = np.poly1d(np.polyfit(range(len(df)), df["Actual"], 1))

        fig2 = go.Figure()
        fig2.add_scatter(x=df["Date"], y=df["Actual"], name="Actual")
        fig2.add_scatter(x=df["Date"], y=trend(range(len(df))), name="Trend")

        st.plotly_chart(fig2, use_container_width=True)


# ============================================
# 📊 ISSUE PAGES
# ============================================
elif page != "Major_Issues":

    df = load_sheet(page)

    st.subheader(page.replace("_", " "))

    # ===== CLEAN DROPDOWN =====
    issues = df["Issue Type"].dropna().unique().tolist()
    selected = st.selectbox("Select Issue", ["All"] + issues)

    if selected != "All":
        df = df[df["Issue Type"] == selected]

    # ===== TOTAL ISSUES =====
    st.markdown(f"### Total Issues: {int(df['Count'].sum())}")

    # ===== TOP 10 =====
    top10 = df.groupby("Issue Type")["Count"].sum().nlargest(10).reset_index()

    fig = go.Figure()
    fig.add_bar(
        x=top10["Issue Type"],
        y=top10["Count"],
        text=top10["Count"],
        textposition="outside"
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
        name="Cumulative %"
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
