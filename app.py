import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import altair as alt

# -----------------------------
# Google Sheets Credentials
# -----------------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file("service_account.json", scopes=scope)
client = gspread.authorize(creds)

# -----------------------------
# Load sheet function
# -----------------------------
@st.cache_data(ttl=60)  # refresh cache every 60s
def load_issue_sheet(sheet_name):
    try:
        sheet = client.open("PDI_Dashboard").worksheet(sheet_name)
        raw_data = sheet.get_all_values()

        if len(raw_data) < 2:
            st.warning(f"Sheet '{sheet_name}' has no data!")
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

        # Identify Issue Type and Count columns
        issue_col = [c for c in df.columns if "Issue" in c or "Type" in c]
        count_col = [c for c in df.columns if "Count" in c]
        if not issue_col or not count_col:
            st.error(f"Sheet '{sheet_name}' does not have proper columns.")
            return pd.DataFrame(columns=["Issue Type", "Count"])

        df = df[[issue_col[0], count_col[0]]]
        df.columns = ["Issue Type", "Count"]

        # Convert Count to numeric
        df["Count"] = pd.to_numeric(df["Count"], errors="coerce").fillna(0).astype(int)

        # Special handling: move SQA issues containing "Paint" to Paint sheet
        if sheet_name == "SQA":
            paint_mask = df["Issue Type"].str.contains("Paint", case=False, na=False)
            df.loc[paint_mask, "Sheet"] = "Paint"
        else:
            df["Sheet"] = sheet_name

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

# Load the selected sheet
df = load_issue_sheet(sheet_option)

if df.empty:
    st.warning("No data to display.")
else:
    st.subheader(f"Top 10 issues from {sheet_option}")
    st.dataframe(df[["Issue Type", "Count"]])

    # Plot bar chart
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Count:Q', title='Count'),
        y=alt.Y('Issue Type:N', sort='-x', title='Issue Type'),
        tooltip=['Issue Type', 'Count']
    ).properties(height=400, width=700)

    st.altair_chart(chart, use_container_width=True)
