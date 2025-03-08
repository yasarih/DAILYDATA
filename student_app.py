import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
import json

# Constants for Google Sheets
SPREADSHEET_ID = "1CtmcRqCRReVh0xp-QCkuVzlPr7KDdEquGNevKOA1e4w"
WORKSHEET_NAME = "Student class details"

# Load Google Sheets credentials
def load_credentials_from_secrets():
    try:
        credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])
        return credentials_info
    except KeyError:
        st.error("Google credentials not found in Streamlit secrets.")
        return None

# Connect to Google Sheets
def connect_to_google_sheets(spreadsheet_id, worksheet_name):
    credentials_info = load_credentials_from_secrets()
    if not credentials_info:
        return None

    try:
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/drive.file",
            ],
        )
        client = gspread.authorize(credentials)
        return client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet '{spreadsheet_id}' not found. Check permissions.")
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet '{worksheet_name}' not found.")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
    return None

# Fetch data from Google Sheets
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

        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# Load and preprocess data
@st.cache_data
def load_data(spreadsheet_id, sheet_name):
    data = fetch_data_from_sheet(spreadsheet_id, sheet_name)

    # Normalize column names
    data.columns = data.columns.str.strip().str.lower()

    # Validate required columns
    required_columns = [
        "mm","date", "subject", "hr", "teachers name",
        "chapter taken", "type of class", "student id", "student"
    ]
    missing_columns = set(required_columns) - set(data.columns)
    if missing_columns:
        raise ValueError(f"Missing columns: {missing_columns}")

    # Keep only necessary columns
    data = data[required_columns]

    # Convert 'student id' and 'student' columns to lowercase and strip whitespace
    data["student id"] = data["student id"].astype(str).str.lower().str.strip()
    data["student"] = data["student"].astype(str).str.lower().str.strip()

    # Convert 'date' column to datetime format (handling errors)
    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], format="%d/%m/%Y", errors="coerce")

    # Convert 'hr' column to numeric safely
    if "hr" in data.columns:
        data["hr"] = pd.to_numeric(data["hr"], errors="coerce").fillna(0)

    # Ensure 'date' column exists and create 'mm' column
    if "date" in data.columns and not data["date"].isna().all():
        data["mm"] = data["date"].dt.month.astype(str).str.zfill(2)
    else:
        st.warning("⚠️ 'Date' column is missing or not properly formatted.")

    return data

# Main app
def main():
    st.title("Student Insights and Analysis")

    try:
        student_data = load_data(SPREADSHEET_ID, WORKSHEET_NAME)
    except ValueError as e:
        st.error(str(e))
        return

    # Debugging: Check available columns and data types
    st.write("🔍 Available columns:", student_data.columns.tolist())
    st.write("📌 Column Data Types:", student_data.dtypes)

    # Inputs
    student_id = st.text_input("Enter Your Student ID").strip().lower()
    student_name_part = st.text_input("Enter Any Part of Your Name (minimum 4 characters)").strip().lower()
    month = st.selectbox(
        "Select Month",
        options=list(range(1, 13)),
        format_func=lambda x: pd.to_datetime(f"2024-{x}-01").strftime('%B'),
    )

    if st.button("Fetch Data"):
        if not student_id or len(student_name_part) < 4:
            st.error("Enter a valid Student ID and at least 4 characters of your name.")
            return

        if "mm" not in student_data.columns:
            st.error("⚠️ 'MM' column is missing. Ensure the 'date' column is formatted correctly.")
            return

        # Filter student data
        filtered_data = student_data[
            (student_data["student id"] == student_id) &
            (student_data["student"].str.contains(student_name_part, na=False)) &
            (student_data["mm"] == str(month).zfill(2))
        ]

        if not filtered_data.empty:
            student_name = filtered_data["student"].iloc[0].title()
            st.subheader(f"Welcome, {student_name}!")

            # Format 'Date' for display
            filtered_data["date"] = filtered_data["date"].dt.strftime('%d/%m/%Y')

            # Remove sensitive columns before displaying
            final_data = filtered_data.drop(columns=["student id", "student"]).reset_index(drop=True)

            # Display subject breakdown
            subject_hours = (
                filtered_data.groupby("subject")["hr"]
                .sum()
                .reset_index()
                .rename(columns={"hr": "Total Hours"})
            )

            st.write("**Your Monthly Class Details**")
            st.dataframe(final_data)
            st.subheader("Subject-wise Hour Breakdown")
            st.dataframe(subject_hours)

            # Total hours calculation and display
            total_hours = filtered_data["hr"].sum()
            st.write(f"**Total Hours:** {total_hours:.2f}")

            # Weekly breakdown
            filtered_data["week"] = pd.to_datetime(filtered_data["date"], errors="coerce").dt.isocalendar().week
            weekly_hours = (
                filtered_data.groupby("week")["hr"].sum().reset_index().rename(columns={"hr": "Weekly Total Hours"})
            )
            st.subheader("Weekly Class Breakdown")
            st.dataframe(weekly_hours)

        else:
            st.error(f"No data found for Student ID '{student_id}' and Month '{month}'.")
  
# Run app
if __name__ == "__main__":
    main()
