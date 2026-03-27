import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import altair as alt
import json

# -----------------------------
# Google Sheets Authentication
# -----------------------------
@st.cache_resource
def get_gs_client():
    try:
        sa_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
        creds = Credentials.from_service_account_info(sa_info, scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ])
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Google Sheets Authentication Failed: {e}")
        return None

client = get_gs_client()
if client is None:
    st.stop()

# -----------------------------
# Load sheet and process data
# -----------------------------
@st.cache_data
def load_issue_sheet(sheet_name):
    """
    Load a sheet from Google Sheets, clean headers, convert Count,
    handle SQA -> Paint conversion, and return top 10 issues.
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

        df = pd.DataFrame(raw_data[1:], columns=headers)

        # Identify Issue Type and Count columns
        issue_col = [c for c in df.columns if "Issue" in c or "Type" in c]
        count_col = [c for c in df.columns if "Count" in c]

        if not issue_col or not count_col:
            st.warning(f"No valid Issue or Count columns found in sheet {sheet_name}")
            return pd.DataFrame(columns=["Issue Type", "Count"])

        df = df[[issue_col[0], count_col[0]]]
        df.columns = ["Issue Type", "Count"]

        # Convert Count to numeric
        df["Count"] = pd.to_numeric(df["Count"], errors="coerce").fillna(0).astype(int)

        # Convert SQA issues that are really Paint issues
        paint_keywords = ["paint", "rundown", "dust"]
        df["Section"] = "Other"
        df.loc[df["Issue Type"].str.contains("SQA", case=False), "Section"] = "SQA"
        df.loc[df["Section"]=="SQA", "Section"] = df.loc[df["Section"]=="SQA", "Issue Type"].apply(
            lambda x: "Paint" if any(k in x.lower() for k in paint_keywords) else "SQA"
        )

        # Keep top 10 issues by Count
        df_top10 = df.sort_values(by="Count", ascending=False).head(10).reset_index(drop=True)
        return df_top10

    except Exception as e:
        st.error(f"Failed to load sheet '{sheet_name}': {e}")
        return pd.DataFrame(columns=["Issue Type", "Count"])

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="PDI Dashboard", layout="wide")
st.title("📊 PDI Dashboard - Top 10 Issues")

# Sheet selection
sheet_option = st.selectbox(
    "Select Issue Sheet",
    ["Testing_Issue", "SQA", "Paint Rundown", "DENT", "SCRATCH", "Other"]
)

# Load data
df = load_issue_sheet(sheet_option)

if df.empty:
    st.warning("No data available for this sheet.")
else:
    st.subheader(f"Top 10 issues from '{sheet_option}'")
    st.dataframe(df, use_container_width=True)

    # Plot bar chart
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Count:Q', title='Count'),
        y=alt.Y('Issue Type:N', sort='-x', title='Issue Type'),
        color='Section:N',
        tooltip=['Issue Type', 'Count', 'Section']
    ).properties(height=400, width=800)

    st.altair_chart(chart, use_container_width=True)
