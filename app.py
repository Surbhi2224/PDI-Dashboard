import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# Service account credentials from secrets
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"])
client = gspread.authorize(creds)

# Load sheet
def load_sheet(sheet_name):
    try:
        sheet = client.open("PDI_Dashboard").worksheet(sheet_name)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error loading sheet: {e}")
        return pd.DataFrame()

# Example usage
df = load_sheet("Daily_Clearing")
st.dataframe(df)
