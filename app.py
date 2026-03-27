import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import altair as alt

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="PDI Dashboard", layout="wide")
st.title("PDI Dashboard - Top 10 Issues")

# -----------------------------
# Google Sheets Authentication
# -----------------------------
try:
    service_account_info = st.secrets["GOOGLE_SERVICE_ACCOUNT"]

    # Correct scopes for gspread
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
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
    Load a sheet from Google Sheets, fix headers, ensure numeric Count,
    and return a DataFrame with top 10 issues by count.
    """
    try:
        sheet = client.open("PDI_Dashboard").worksheet(sheet_name)
        raw_data = sheet.get_all_values()

        if len(raw_data) < 2:
            st.warning(f"Sheet {sheet_name} has no data!")
            return pd.DataFrame(columns=["Issue Type", "Count"])

        # Fix headers (replace empty and duplicate headers)
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

        # Identify Issue Type and Count columns
        possible_issue_col = [c for c in df.columns if "Issue" in c or "Type" in c]
        possible_count_col = [c for c in df.columns if "Count" in c]

        if not possible_issue_col or not possible_count_col:
            st.warning(f"Sheet {sheet_name} is missing 'Issue Type' or 'Count' columns!")
            return pd.DataFrame(columns=["Issue Type", "Count"])

        df = df[[possible_issue_col[0], possible_count_col[0]]]
        df.columns = ["Issue Type", "Count"]

        # Convert Count to numeric
        df["Count"] = pd.to_numeric(df["Count"], errors="coerce").fillna(0).astype(int)

        # Sort by Count descending and take top 10
        df_top10 = df.sort_values(by="Count", ascending=False).head(10).reset_index(drop=True)

        return df_top10

    except Exception as e:
        st.error(f"Failed to load sheet '{sheet_name}': {e}")
        return pd.DataFrame(columns=["Issue Type", "Count"])

# -----------------------------
# Streamlit UI
# -----------------------------
sheet_option = st.selectbox(
    "Select Issue Sheet",
    ["Testing_Issue", "SQA", "Paint Rundown", "DENT", "SCRATCH", "Other"]
)

# Load sheet
df = load_issue_sheet(sheet_option)

if df.empty:
    st.warning("No data to display")
else:
    st.subheader(f"Top 10 issues from {sheet_option}")
    st.dataframe(df)

    # Plot Bar chart
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Count:Q', title='Count'),
        y=alt.Y('Issue Type:N', sort='-x', title='Issue Type'),
        tooltip=['Issue Type', 'Count']
    ).properties(height=400, width=700)

    st.altair_chart(chart, use_container_width=True)
