import streamlit as st
import pandas as pd
import altair as alt
import json
import gspread
from google.oauth2.service_account import Credentials

# -----------------------------
# Google Sheets Authentication
# -----------------------------
try:
    sa_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"]["GOOGLE_SERVICE_ACCOUNT"])
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(sa_info, scopes=scope)
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"Google Sheets Authentication Failed: {e}")
    st.stop()

# -----------------------------
# Function to load any sheet
# -----------------------------
@st.cache_data
def load_issue_sheet(sheet_name):
    """
    Load a Google Sheet and return top 10 issues as a DataFrame.
    Handles SQA paint issues correctly.
    """
    try:
        sheet = client.open("PDI_Dashboard").worksheet(sheet_name)
        raw_data = sheet.get_all_values()

        if len(raw_data) < 2:
            return pd.DataFrame(columns=["Issue Type", "Count"])

        # Fix headers
        headers = raw_data[0]
        headers = [f"Column_{i}" if not h.strip() else h for i, h in enumerate(headers)]
        seen = {}
        for i, h in enumerate(headers):
            if h in seen:
                headers[i] = f"{h}_{seen[h]+1}"
                seen[h] += 1
            else:
                seen[h] = 0

        # Create DataFrame
        df = pd.DataFrame(raw_data[1:], columns=headers)

        # Detect Issue Type and Count columns
        issue_col = [c for c in df.columns if "Issue" in c or "Type" in c][0]
        count_col = [c for c in df.columns if "Count" in c][0]
        df = df[[issue_col, count_col]]
        df.columns = ["Issue Type", "Count"]

        # Convert Count to numeric
        df["Count"] = pd.to_numeric(df["Count"], errors="coerce").fillna(0).astype(int)

        # For SQA, move paint-related issues to paint category
        if sheet_name.lower() == "sqa":
            paint_keywords = ["paint", "rundown", "uncoverd", "unpainted"]
            paint_mask = df["Issue Type"].str.lower().str.contains("|".join(paint_keywords))
            paint_df = df[paint_mask].copy()
            df = df[~paint_mask].copy()
            # You can choose to save paint_df somewhere or merge into paint sheet later

        # Sort and take top 10
        df_top10 = df.sort_values(by="Count", ascending=False).head(10).reset_index(drop=True)
        return df_top10

    except Exception as e:
        st.error(f"Failed to load sheet '{sheet_name}': {e}")
        return pd.DataFrame(columns=["Issue Type", "Count"])

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="PDI Dashboard", layout="wide")
st.title("PDI Dashboard - Top 10 Issues")

sheet_option = st.selectbox(
    "Select Issue Sheet",
    ["Testing_Issue", "SQA", "Paint Rundown", "DENT", "SCRATCH", "Other", "T&V"]
)

# Load sheet
df = load_issue_sheet(sheet_option)

if df.empty:
    st.warning("No data to display")
else:
    st.subheader(f"Top 10 issues from {sheet_option}")
    st.dataframe(df)

    # Bar chart
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Count:Q', title='Count'),
        y=alt.Y('Issue Type:N', sort='-x', title='Issue Type'),
        tooltip=['Issue Type', 'Count']
    ).properties(height=400, width=800)

    st.altair_chart(chart, use_container_width=True)
