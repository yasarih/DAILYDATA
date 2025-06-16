import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
import json

# Constants
SPREADSHEET_ID = "1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4"
WORKSHEET_NAME = "Student class details"

# Page config
st.set_page_config(
    page_title="Student Insights App",
    page_icon="🎓",
    layout="wide",
)

# Load credentials from Streamlit secrets
def load_credentials_from_secrets():
    try:
        credentials_info = dict(st.secrets["google_credentials_new_project"])  # convert to dict
        return credentials_info
    except KeyError:
        st.error("Google credentials not found in Streamlit secrets.")
        return None


# Connect to Google Sheets
def connect_to_google_sheets(spreadsheet_id, worksheet_name):
    credentials_info = load_credentials_from_secrets()
    if not credentials_info:
        return None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
    ]

    try:
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
        return sheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet with ID '{spreadsheet_id}' not found.")
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet '{worksheet_name}' not found.")
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
    return None


# Fetch data from Google Sheet
def fetch_data_from_sheet(spreadsheet_id, worksheet_name):
    sheet = connect_to_google_sheets(spreadsheet_id, worksheet_name)
    if not sheet:
        return pd.DataFrame()

    try:
        data = sheet.get_all_values()
        if not data:
            return pd.DataFrame()

        headers = pd.Series(data[0]).fillna('').str.strip()
        headers = headers.where(headers != '', other='Unnamed')
        headers = headers + headers.groupby(headers).cumcount().astype(str).replace('0', '')
        df = pd.DataFrame(data[1:], columns=headers)
        df.replace('', pd.NA, inplace=True)
        df.ffill(inplace=True)
        if 'hr' in df.columns:
            df['hr'] = pd.to_numeric(df['hr'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error fetching data from worksheet: {e}")
        return pd.DataFrame()


# Load and preprocess data
@st.cache_data(show_spinner=False)
def load_data(spreadsheet_id, sheet_name):
    data = fetch_data_from_sheet(spreadsheet_id, sheet_name)
    if data.empty:
        return pd.DataFrame()

    data.columns = data.columns.str.strip().str.lower()

    required_columns = [
        "date", "subject", "hr", "teachers name",
        "chapter taken", "type of class", "student id", "student"
    ]
    missing_columns = set(required_columns) - set(data.columns)
    if missing_columns:
        raise ValueError(f"Missing columns in data: {missing_columns}")

    data = data[required_columns]

    data["student id"] = data["student id"].astype(str).str.lower().str.strip()
    data["student"] = data["student"].astype(str).str.lower().str.strip()
    data["hr"] = pd.to_numeric(data["hr"], errors="coerce").fillna(0)

    data["date"] = pd.to_datetime(data["date"], errors="coerce", dayfirst=True)

    failed_dates = data["date"].isna().sum()
    if failed_dates > 0:
        st.warning(f"Warning: {failed_dates} date entries could not be parsed and will show as empty.")

    return data


def main():
    st.title("Student Insights and Analysis")

    try:
        student_data = load_data(SPREADSHEET_ID, WORKSHEET_NAME)
    except ValueError as e:
        st.error(str(e))
        return

    student_id = st.text_input("Enter Your Student ID").strip().lower()
    student_name_part = st.text_input("Enter Any Part of Your Name (minimum 4 characters)").strip().lower()

    if st.button("Fetch Data"):
        if not student_id or len(student_name_part) < 4:
            st.error("Please enter a valid Student ID and at least 4 characters of your name.")
            return

        filtered_data = student_data[
            (student_data["Student ID"] == student_id) &
            (student_data["student"].str.contains(student_name_part, na=False))
        ]

        if not filtered_data.empty:
            student_name = filtered_data["student"].iloc[0].title()
            st.subheader(f"Welcome, {student_name}!")

            filtered_data_copy = filtered_data.copy()
            filtered_data_copy["date"] = filtered_data_copy["date"].fillna(pd.NaT)
            filtered_data_copy["date_str"] = filtered_data_copy["date"].dt.strftime('%d/%m/%Y')
            filtered_data_copy["date_str"] = filtered_data_copy["date_str"].where(
                filtered_data_copy["date"].notna(), "Date not available"
            )

            filtered_data_copy.drop(columns=["date"], inplace=True)
            filtered_data_copy.rename(columns={"date_str": "date"}, inplace=True)

            final_data = filtered_data_copy.drop(columns=["student id", "student"]).reset_index(drop=True)

            subject_hours = (
                filtered_data.groupby("subject")["hr"]
                .sum()
                .reset_index()
                .rename(columns={"hr": "Total Hours"})
            )

            st.write("**Your Class Details**")
            st.dataframe(final_data)
            st.subheader("Subject-wise Hour Breakdown")
            st.dataframe(subject_hours)

            total_hours = filtered_data["hr"].sum()
            st.write(f"**Total Hours:** {total_hours:.2f}")
        else:
            st.error("No data found for the given Student ID and Name.")


if __name__ == "__main__":
    main()
