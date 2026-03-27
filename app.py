import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import altair as alt

# -----------------------------
# Google Sheets Authentication
# -----------------------------
# Use your secrets.toml GOOGLE_SERVICE_ACCOUNT key
service_account_info = st.secrets["GOOGLE_SERVICE_ACCOUNT"]
creds = Credentials.from_service_account_info(service_account_info)
client = gspread.authorize(creds)

# -----------------------------
# Function to load sheet
# -----------------------------
@st.cache_data
def load_issue_sheet(sheet_name):
    """
    Load Google Sheet, fix headers, convert Count to numeric,
    and return top 10 issues as DataFrame.
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

        df = pd.DataFrame(raw_data[1:], columns=headers)

        # Keep only Issue Type and Count columns
        issue_col = [c for c in df.columns if "Issue" in c or "Type" in c][0]
        count_col = [c for c in df.columns if "Count" in c][0]
        df = df[[issue_col, count_col]]
        df.columns = ["Issue Type", "Count"]

        # Convert Count to numeric
        df["Count"] = pd.to_numeric(df["Count"], errors="coerce").fillna(0).astype(int)

        # For SQA sheet: move Paint-tagged issues to Paint category
        if sheet_name.lower() == "sqa":
            paint_issues = df[df["Issue Type"].str.lower().str.contains("paint")]
            df = df[~df["Issue Type"].str.lower().str.contains("paint")]

        # Sort descending by Count and take top 10
        df_top10 = df.sort_values(by="Count", ascending=False).head(10).reset_index(drop=True)

        return df_top10

    except Exception as e:
        st.error(f"Failed to load sheet '{sheet_name}': {e}")
        return pd.DataFrame(columns=["Issue Type", "Count"])

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("PDI Dashboard - Top 10 Issues")

sheet_option = st.selectbox(
    "Select Issue Sheet",
    ["Testing_Issue", "SQA", "Paint Rundown", "DENT", "SCRATCH", "Other"]
)

df = load_issue_sheet(sheet_option)

if df.empty:
    st.warning("No data to display")
else:
    st.subheader(f"Top 10 issues from {sheet_option}")
    st.dataframe(df)

    # Plot bar chart
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Count:Q', title='Count'),
        y=alt.Y('Issue Type:N', sort='-x', title='Issue Type'),
        tooltip=['Issue Type', 'Count']
    ).properties(height=400, width=700)

    st.altair_chart(chart, use_container_width=True)
