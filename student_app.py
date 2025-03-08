import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
import json

# Constants for Google Sheets
SPREADSHEET_ID = "1CtmcRqCRReVh0xp-QCkuVzlPr7KDdEquGNevKOA1e4w"  # Replace with your Google Sheets ID
WORKSHEET_NAME = "Student class details"  # Replace with your worksheet name

# Set page layout and title
st.set_page_config(
    page_title="Student Insights App",
    page_icon="🎓",
    layout="wide",
)

# Function to load credentials from Streamlit secrets
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
        "https://www.googleapis.com/auth/drive.file",
    ]

    try:
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
        return sheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

# Function to fetch data from Google Sheets
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

        # Convert 'date' column properly
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y", errors="coerce")
            
            if df["date"].isna().all():
                st.error("All date values are invalid. Check the date format in Google Sheets.")

        # Convert 'hr' column to numeric
        if "hr" in df.columns:
            df["hr"] = pd.to_numeric(df["hr"], errors="coerce").fillna(0)

        return df

    except Exception as e:
        st.error(f"Error fetching data from worksheet: {e}")
        return pd.DataFrame()

# Function to load and preprocess data
@st.cache_data
def load_data(spreadsheet_id, sheet_name):
    data = fetch_data_from_sheet(spreadsheet_id, sheet_name)
    data.columns = data.columns.str.strip().str.lower()

    required_columns = ["date", "subject", "hr", "teachers name", "chapter taken", "type of class", "student id", "student"]
    missing_columns = set(required_columns) - set(data.columns)
    if missing_columns:
        raise ValueError(f"Missing columns in data: {missing_columns}")

    data = data[required_columns]
    data["student id"] = data["student id"].astype(str).str.lower().str.strip()
    data["student"] = data["student"].astype(str).str.lower().str.strip()

    return data

# Main application
def main():
    st.title("Student Insights and Analysis")

    try:
        student_data = load_data(SPREADSHEET_ID, WORKSHEET_NAME)
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

        # Ensure 'date' column exists and is in datetime format
        if "date" not in student_data.columns or not pd.api.types.is_datetime64_any_dtype(student_data["date"]):
            st.error("Date column is missing or contains non-datetime values. Please check your Google Sheet.")
            return

        # Filter data based on student ID, partial name match, and month
        filtered_data = student_data[
            (student_data["student id"] == student_id) &
            (student_data["student"].str.contains(student_name_part, na=False)) &
            (student_data["date"].dt.month == month)
        ]

        if not filtered_data.empty:
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

        else:
            st.error(f"No data found for the given Student ID, Name, and selected month ({pd.to_datetime(f'2024-{month}-01').strftime('%B')}).")

# Run the app
if __name__ == "__main__":
    main()
