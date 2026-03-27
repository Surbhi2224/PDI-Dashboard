import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ===== CONFIG =====
st.set_page_config(layout="wide", page_title="PDI Dashboard")
st.title("🚗 PDI Production Dashboard")
st.caption("Real-time Monitoring System")

# AUTO REFRESH
st_autorefresh(interval=5000, key="refresh")

# ===== GOOGLE SHEETS CONNECTION (CLOUD SAFE) =====
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
    try:
        sheet = client.open("PDI_Dashboard").worksheet(name)
        df = pd.DataFrame(sheet.get_all_records())

        if df.empty:
            st.warning(f"{name} sheet is empty")
            return df

        # Clean columns
        if "Model" in df.columns:
            df["Model"] = df["Model"].astype(str).str.strip()

        for col in ["Plan", "Actual", "Pending", "Count"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        return df

    except Exception as e:
        st.error(f"Error loading sheet {name}: {e}")
        return pd.DataFrame()

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
    "Major_Issues"
]

page = st.sidebar.radio("📂 Navigation", pages)

# ============================================
# 📊 EXECUTIVE SUMMARY
# ============================================
if page == "Executive_Summary":

    df = load_sheet("Daily_Clearing")

    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])

        total_plan = int(df["Plan"].sum())
        total_actual = int(df["Actual"].sum())
        total_pending = int(df["Pending"].sum())

        c1, c2, c3 = st.columns(3)
        c1.metric("📦 Total Offered", total_plan)
        c2.metric("✅ Total Cleared", total_actual)
        c3.metric("⏳ Total Pending", total_pending)

        daily = df.groupby("Date")[["Plan", "Actual", "Pending"]].sum().reset_index()

        fig = go.Figure()
        fig.add_bar(x=daily["Date"], y=daily["Plan"], name="Offered", marker_color="blue")
        fig.add_bar(x=daily["Date"], y=daily["Actual"], name="Cleared", marker_color="green")
        fig.add_bar(x=daily["Date"], y=daily["Pending"], name="Pending", marker_color="orange")

        fig.update_layout(title="Overall Performance", barmode="group")
        st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📅 DAILY CLEARING
# ============================================
elif page == "Daily_Clearing":

    df = load_sheet("Daily_Clearing")

    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])

        total_plan = int(df["Plan"].sum())
        total_actual = int(df["Actual"].sum())
        total_pending = int(df["Pending"].sum())

        c1, c2, c3 = st.columns(3)
        c1.metric("📦 Total Offered", total_plan)
        c2.metric("✅ Total Cleared", total_actual)
        c3.metric("⏳ Total Pending", total_pending)

        model = st.selectbox("🚗 Select Model", ["All"] + df["Model"].unique().tolist())

        if model != "All":
            df = df[df["Model"] == model]

        start, end = st.date_input(
            "📅 Date Range",
            [df['Date'].min(), df['Date'].max()]
        )

        df = df[
            (df['Date'] >= pd.to_datetime(start)) &
            (df['Date'] <= pd.to_datetime(end))
        ]

        daily = df.groupby("Date")[["Plan", "Actual", "Pending"]].sum().reset_index()

        fig = go.Figure()
        fig.add_bar(x=daily["Date"], y=daily["Plan"], name="Offered", marker_color="blue")
        fig.add_bar(x=daily["Date"], y=daily["Actual"], name="Cleared", marker_color="green")
        fig.add_bar(x=daily["Date"], y=daily["Pending"], name="Pending", marker_color="orange")

        fig.update_layout(title="📊 Daily Production", barmode="group")
        st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📊 ISSUE PAGES (TOP 10)
# ============================================
elif page != "Major_Issues":

    df = load_sheet(page)

    if not df.empty:
        st.subheader(f"📊 {page}")

        total_issues = int(df["Count"].sum())
        st.metric("🚨 Total Issues", total_issues)

        issues = df["Issue Type"].unique().tolist()
        selected = st.multiselect("Select Issues", issues, default=issues)

        df = df[df["Issue Type"].isin(selected)]

        top10 = df.groupby("Issue Type")["Count"].sum().reset_index()
        top10 = top10.sort_values(by="Count", ascending=False).head(10)

        fig = go.Figure()
        fig.add_bar(
            x=top10["Issue Type"],
            y=top10["Count"],
            text=top10["Count"],
            textposition='outside',
            marker_color="red"
        )

        fig.update_layout(title="Top 10 Issues")
        st.plotly_chart(fig, use_container_width=True)

# ============================================
# 📋 MAJOR ISSUES
# ============================================
elif page == "Major_Issues":
    st.info("📄 Please check detailed data in Google Sheets")

# ===== FOOTER =====
st.markdown("---")
st.caption("Developed by Surbhi | PDI Dashboard")
