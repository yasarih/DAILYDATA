import streamlit as st  # Import Streamlit first
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
import json

# Place st.set_page_config at the very top
st.set_page_config(page_title="Student Insights App", layout="wide")

# Define spreadsheet ID globally
spreadsheet_id = "17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y"  # Replace with your spreadsheet ID

# Functions for connecting to Google Sheets and fetching data
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

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ]

    try:
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=scopes
        )
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
        return sheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet with ID '{spreadsheet_id}' not found. Check the spreadsheet ID and permissions.")
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet '{worksheet_name}' not found in the spreadsheet. Verify the worksheet name.")
    except Exception as e:
        st.error(f"Unexpected error connecting to Google Sheets: {e}")
        st.exception(e)
    return None

# Main application logic
def main():
    st.title("Student Insights and Analysis")  # Streamlit commands now come after set_page_config

    # Load data
    try:
        student_data = load_data(spreadsheet_id, "Student class details")
    except ValueError as e:
        st.error(str(e))
        return

    # Inputs for verification
    student_id = st.text_input("Enter Your Student ID").strip().lower()
    student_name_part = st.text_input("Enter Any Part of Your Name (minimum 4 characters)").strip().lower()

    # Month dropdown
    month = st.selectbox(
        "Select Month",
        options=list(range(1, 13)),
        format_func=lambda x: pd.to_datetime(f"2024-{x}-01").strftime('%B')  # Show month names
    )

    if st.button("Fetch Data"):
        if not student_id or len(student_name_part) < 4:
            st.error("Please enter a valid Student ID and at least 4 characters of your name.")
            return

        # Filter data based on student ID, partial name match, and month
        filtered_data = student_data[
            (student_data["student id"] == student_id) &
            (student_data["student"].str.contains(student_name_part, na=False)) &
            (student_data["date"].dt.month == month)
        ]

        if filtered_data.empty:
            st.error(f"No data found for the given Student ID, Name, and selected month.")
            return

        student_name = filtered_data["student"].iloc[0].title()
        st.subheader(f"Welcome, {student_name}!")

        # Display filtered data
        filtered_data["date"] = filtered_data["date"].dt.strftime('%d/%m/%Y')
        final_data = filtered_data.drop(columns=["student id", "student"]).reset_index(drop=True)
        st.write("**Your Monthly Class Details**")
        st.dataframe(final_data)

        # Display subject breakdown
        subject_hours = filtered_data.groupby("subject")["hr"].sum().reset_index().rename(columns={"hr": "Total Hours"})
        st.subheader("Subject-wise Hour Breakdown")
        st.dataframe(subject_hours)

        total_hours = filtered_data["hr"].sum()
        st.write(f"**Total Hours:** {total_hours:.2f}")

if __name__ == "__main__":
    main()
