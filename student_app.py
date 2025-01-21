import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
import json

# Set page configuration
st.set_page_config(page_title="Student Insights App", layout="wide")

# Global variable for spreadsheet ID
spreadsheet_id = "17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y"  # Replace with your spreadsheet ID

# Function definitions
def load_credentials_from_secrets():
    try:
        credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])
        return credentials_info
    except KeyError:
        st.error("Google credentials not found in Streamlit secrets.")
        return None

def connect_to_google_sheets(spreadsheet_id, worksheet_name):
    credentials_info = load_credentials_from_secrets()
    if not credentials_info:
        return None

    try:
        credentials = Credentials.from_service_account_info(credentials_info)
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
        return sheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

def load_data(spreadsheet_id, sheet_name):
    sheet = connect_to_google_sheets(spreadsheet_id, sheet_name)
    if not sheet:
        return pd.DataFrame()

    try:
        data = sheet.get_all_values()
        if data:
            df = pd.DataFrame(data[1:], columns=data[0])
            df.columns = df.columns.str.lower().str.strip()
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
    return pd.DataFrame()

# Main function
def main():
    st.title("Student Insights and Analysis")
    try:
        student_data = load_data(spreadsheet_id, "Student class details")
    except Exception as e:
        st.error(f"Error loading student data: {e}")
        return

    student_id = st.text_input("Enter Your Student ID").strip().lower()
    student_name_part = st.text_input("Enter Any Part of Your Name").strip().lower()

    if st.button("Fetch Data"):
        if not student_id or len(student_name_part) < 4:
            st.error("Please enter a valid Student ID and at least 4 characters of your name.")
            return

        # Filter data
        filtered_data = student_data[
            (student_data["student id"] == student_id) &
            (student_data["student"].str.contains(student_name_part, na=False))
        ]

        if not filtered_data.empty:
            st.dataframe(filtered_data)
        else:
            st.error("No matching data found.")

if __name__ == "__main__":
    main()
