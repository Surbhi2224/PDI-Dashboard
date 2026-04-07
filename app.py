import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# ===== PAGE CONFIG =====
st.set_page_config(layout="wide", page_title="PDI Dashboard")

# ===== DARK CLEAN UI =====
st.markdown("""
<style>
body {
    background-color: #0f172a;
}

/* KPI CARD */
[data-testid="stMetric"] {
    background: #111827;
    border-radius: 12px;
    padding: 18px;
    border-left: 5px solid #22c55e;
}

/* TEXT */
[data-testid="stMetricLabel"] {
    font-weight: 600;
    color: #9ca3af;
}

[data-testid="stMetricValue"] {
    font-size: 38px;
    font-weight: 800;
}

/* COMMENT BOX */
textarea {
    border-radius: 10px !important;
}

</style>
""", unsafe_allow_html=True)

st.title("🚗 PDI Production Dashboard")

# ===== SAMPLE DATA LOAD (REPLACE WITH GOOGLE SHEET) =====
@st.cache_data
def load_data():
    df = pd.read_csv("daily.csv")  # replace if needed
    df["Date"] = pd.to_datetime(df["Date"])
    return df

df = load_data()

# ===== SIDEBAR =====
page = st.sidebar.selectbox(
    "Navigation",
    ["Executive Summary", "Daily Clearing", "Issues"]
)

# ============================================
# 📊 EXECUTIVE SUMMARY
# ============================================
if page == "Executive Summary":

    df_grouped = df.groupby("Date")[["Plan","Actual","Pending"]].sum().reset_index()

    col1, col2, col3 = st.columns(3)

    total_plan = int(df_grouped["Plan"].sum())
    total_actual = int(df_grouped["Actual"].sum())
    total_pending = int(df_grouped["Pending"].sum())

    # 🔥 TREND CALCULATION
    def trend_arrow(series):
        if len(series) < 2:
            return "➖"
        return "🔼" if series.iloc[-1] > series.iloc[-2] else "🔽"

    col1.metric("Plan", total_plan, trend_arrow(df_grouped["Plan"]))
    col2.metric("Cleared", total_actual, trend_arrow(df_grouped["Actual"]))
    col3.metric("Pending", total_pending, trend_arrow(df_grouped["Pending"]))

    # ===== GRAPH =====
    fig = go.Figure()

    fig.add_bar(
        x=df_grouped["Date"],
        y=df_grouped["Actual"],
        name="Cleared",
        marker_color="#22c55e"
    )

    fig.add_bar(
        x=df_grouped["Date"],
        y=df_grouped["Pending"],
        name="Pending",
        marker_color="#ef4444"
    )

    fig.update_layout(
        barmode="stack",
        template="plotly_dark",
        title="Overall Performance",
        transition_duration=800
    )

    st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📅 DAILY CLEARING
# ============================================
elif page == "Daily Clearing":

    st.subheader("Daily Clearing Status")

    df_grouped = df.groupby("Date")[["Plan","Actual","Pending"]].sum().reset_index()

    col1, col2, col3 = st.columns(3)

    col1.metric("Offered", int(df_grouped["Plan"].sum()))
    col2.metric("Cleared", int(df_grouped["Actual"].sum()))
    col3.metric("Pending", int(df_grouped["Pending"].sum()))

    # ===== STACKED BAR =====
    fig = go.Figure()

    fig.add_bar(
        x=df_grouped["Date"],
        y=df_grouped["Actual"],
        name="CLEARED",
        marker_color="#22c55e",
        text=df_grouped["Actual"],
        textposition="inside"
    )

    fig.add_bar(
        x=df_grouped["Date"],
        y=df_grouped["Pending"],
        name="PENDING",
        marker_color="#ef4444",
        text=df_grouped["Pending"],
        textposition="inside"
    )

    fig.update_layout(
        barmode="stack",
        template="plotly_dark",
        title="Daily Production",
        transition_duration=800
    )

    st.plotly_chart(fig, use_container_width=True)

    # ===== TREND LINE =====
    st.subheader("Trend")

    if len(df_grouped) > 2:
        trend = np.poly1d(np.polyfit(range(len(df_grouped)), df_grouped["Actual"], 1))

        fig2 = go.Figure()
        fig2.add_scatter(
            x=df_grouped["Date"],
            y=df_grouped["Actual"],
            name="Actual",
            line=dict(color="#22c55e")
        )

        fig2.add_scatter(
            x=df_grouped["Date"],
            y=trend(range(len(df_grouped))),
            name="Trend",
            line=dict(dash="dash", color="#60a5fa")
        )

        fig2.update_layout(template="plotly_dark")

        st.plotly_chart(fig2, use_container_width=True)

# ============================================
# ⚠️ ISSUES PAGE
# ============================================
elif page == "Issues":

    st.subheader("Issue Analysis")

    df_issue = pd.read_csv("issues.csv")  # replace with sheet

    # ===== DROPDOWN WITH SEARCH =====
    issue_list = df_issue["Issue Type"].unique()
    selected_issue = st.selectbox(
        "Search Issue",
        options=issue_list
    )

    filtered = df_issue[df_issue["Issue Type"] == selected_issue]

    st.metric("Total Issues", int(filtered["Count"].sum()))

    # ===== BAR CHART =====
    fig = go.Figure()

    fig.add_bar(
        x=filtered["Issue Type"],
        y=filtered["Count"],
        marker_color="#f59e0b"
    )

    fig.update_layout(template="plotly_dark")

    st.plotly_chart(fig, use_container_width=True)

    # ===== PARETO =====
    st.subheader("Pareto Analysis")

    pareto = df_issue.groupby("Issue Type")["Count"].sum().reset_index()
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
        template="plotly_dark",
        yaxis2=dict(overlaying="y", side="right")
    )

    st.plotly_chart(fig2, use_container_width=True)

    # ============================================
    # 💬 COMMENT SECTION
    # ============================================
    st.subheader("💬 Add Comments")

    comment = st.text_area("Write your comment")

    if st.button("Submit Comment"):
        st.success("Comment Added Successfully ✅")

    st.info("Comments storage can be connected to Google Sheets later")

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.caption("Developed by Surbhi 🚀")
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
