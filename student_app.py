import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
import json

# Define spreadsheet ID globally
spreadsheet_id = "17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y"  # Replace with your spreadsheet ID

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

def fetch_data_from_sheet(spreadsheet_id, worksheet_name):
    sheet = connect_to_google_sheets(spreadsheet_id, worksheet_name)
    if not sheet:
        st.warning(f"Could not establish a connection to the worksheet '{worksheet_name}'.")
        return pd.DataFrame()
    try:
        data = sheet.get_all_values()
        if data:
            headers = pd.Series(data[0]).fillna('').str.strip()
            headers = headers.where(headers != '', other='Unnamed')
            headers = headers + headers.groupby(headers).cumcount().astype(str).replace('0', '')
            df = pd.DataFrame(data[1:], columns=headers)
            df.replace('', pd.NA, inplace=True)
            df.ffill(inplace=True)
            if 'Hr' in df.columns:
                df['Hr'] = pd.to_numeric(df['Hr'], errors='coerce').fillna(0)
            return df
        else:
            st.warning(f"No data found in worksheet '{worksheet_name}'.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching data from '{worksheet_name}': {e}")
        st.exception(e)
    return pd.DataFrame()

def load_data(spreadsheet_id, sheet_name):
    data = fetch_data_from_sheet(spreadsheet_id, sheet_name)
    if data.empty:
        st.error("No data available to process.")
        return pd.DataFrame()

    data.columns = data.columns.str.strip().str.lower()
    required_columns = ["date", "subject", "hr", "teachers name", "chapter taken", "type of class", "student id", "student"]
    missing_columns = set(required_columns) - set(data.columns)
    if missing_columns:
        st.error(f"Missing columns in data: {missing_columns}")
        raise ValueError(f"Missing columns in data: {missing_columns}")
    
    data = data[required_columns]
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data[data["date"].notna()]  # Filter out rows with invalid dates
    data["hr"] = pd.to_numeric(data["hr"], errors="coerce").fillna(0)
    return data

if st.button("Refresh Data"):
    student_data = load_data(spreadsheet_id, "Student class details")
    st.success("Data refreshed!")

def main():
    st.set_page_config(page_title="Student Insights App", layout="wide")
    st.title("Student Insights and Analysis")

    try:
        student_data = load_data(spreadsheet_id, "Student class details")
    except ValueError as e:
        st.error(str(e))
        return

    student_id = st.text_input("Enter Your Student ID").strip().lower()
    student_name_part = st.text_input("Enter Any Part of Your Name (minimum 4 characters)").strip().lower()
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

        if filtered_data.empty:
            st.error(f"No data found for the given Student ID, Name, and selected month ({pd.to_datetime(f'2024-{month}-01').strftime('%B')}).")
            return

        student_name = filtered_data["student"].iloc[0].title()
        st.subheader(f"Welcome, {student_name}!")

        filtered_data["date"] = filtered_data["date"].dt.strftime('%d/%m/%Y')
        final_data = filtered_data.drop(columns=["student id", "student"]).reset_index(drop=True)
        subject_hours = filtered_data.groupby("subject")["hr"].sum().reset_index().rename(columns={"hr": "Total Hours"})

        st.write("**Your Monthly Class Details**")
        st.dataframe(final_data)
        st.subheader("Subject-wise Hour Breakdown")
        st.dataframe(subject_hours)

        total_hours = filtered_data["hr"].sum()
        st.write(f"**Total Hours:** {total_hours:.2f}")

if __name__ == "__main__":
    main()
