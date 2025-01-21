import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
import json

# Set page configuration
st.set_page_config(page_title="Updating...", layout="wide")

# Global variable for spreadsheet ID
spreadsheet_id = "17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y"  # Replace with your spreadsheet ID

# Function to load credentials
def load_credentials_from_secrets():
    try:
        credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])
        return credentials_info
    except KeyError:
        st.error("Google credentials not found in Streamlit secrets.")
        return None

# Function to connect to Google Sheets
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
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
        return sheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet with ID '{spreadsheet_id}' not found.")
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet '{worksheet_name}' not found in the spreadsheet.")
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
    return None

# Fetch data from sheet
def fetch_data_from_sheet(spreadsheet_id, worksheet_name):
    sheet = connect_to_google_sheets(spreadsheet_id, worksheet_name)
    if not sheet:
        return pd.DataFrame()
    try:
        data = sheet.get_all_values()
        if data:
            headers = pd.Series(data[0]).fillna('').str.strip()
            headers = headers.where(headers != '', other='Unnamed')
            headers += headers.groupby(headers).cumcount().astype(str).replace('0', '')
            df = pd.DataFrame(data[1:], columns=headers)
            df.replace('', pd.NA, inplace=True)
            df.ffill(inplace=True)
            return df
        else:
            st.warning(f"No data found in worksheet '{worksheet_name}'.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# Load and preprocess data
def load_data(spreadsheet_id, sheet_name):
    data = fetch_data_from_sheet(spreadsheet_id, sheet_name)
    if data.empty:
        st.error("No data found.")
        return pd.DataFrame()

    data.columns = data.columns.str.strip().str.lower()

    required_columns = ["date", "subject", "hr", "teachers name", "chapter taken", "type of class", "student id", "student"]
    missing_columns = set(required_columns) - set(data.columns)
    if missing_columns:
        st.error(f"Missing columns: {missing_columns}")
        raise ValueError(f"Missing columns: {missing_columns}")

    data = data[required_columns]
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data[data["date"].notna()]  # Remove rows with invalid dates
    data["hr"] = pd.to_numeric(data["hr"], errors="coerce").fillna(0)
    return data

# Main application
def main():
    st.title("Student Insights and Analysis")

    try:
        student_data = load_data(spreadsheet_id, "Student class details")
    except ValueError as e:
        st.error(str(e))
        return

    student_id = st.text_input("Enter Your Student ID").strip().lower()
    student_name_part = st.text_input("Enter Any Part of Your Name").strip().lower()
    month = st.selectbox("Select Month", options=list(range(1, 13)), format_func=lambda x: pd.to_datetime(f"2024-{x}-01").strftime('%B'))

    if st.button("Fetch Data"):
        if not student_id or len(student_name_part) < 4:
            st.error("Please enter a valid Student ID and at least 4 characters of your name.")
            return

        filtered_data = student_data[
            (student_data["student id"] == student_id) &
            (student_data["student"].str.contains(student_name_part, na=False)) &
            (student_data["date"].dt.month == month)
        ]

        if not filtered_data.empty:
            student_name = filtered_data["student"].iloc[0].title()
            st.subheader(f"Welcome, {student_name}!")

            filtered_data = filtered_data.copy()
            filtered_data["formatted_date"] = filtered_data["date"].dt.strftime('%d/%m/%Y')

            final_data = filtered_data.drop(columns=["student id", "student"]).reset_index(drop=True)
            subject_hours = filtered_data.groupby("subject")["hr"].sum().reset_index().rename(columns={"hr": "Total Hours"})

            st.write("**Your Monthly Class Details**")
            st.dataframe(final_data)
            st.subheader("Subject-wise Hour Breakdown")
            st.dataframe(subject_hours)
            st.write(f"**Total Hours:** {filtered_data['hr'].sum():.2f}")
        else:
            st.error("No data found for the given criteria.")

if __name__ == "__main__":
    main()
