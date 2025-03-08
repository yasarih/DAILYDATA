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
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)

# Function to load credentials from local JSON file
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
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet with ID '{spreadsheet_id}' not found. Check the spreadsheet ID and permissions.")
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet '{worksheet_name}' not found in the spreadsheet. Verify the worksheet name.")
    except Exception as e:
        st.error(f"Unexpected error connecting to Google Sheets: {e}")
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

        # Ensure 'Date' column exists
        if "Date" in df.columns:
            st.write("📌 Raw Date Column Sample (before conversion):", df["Date"].head(5).tolist())  # Debugging
            df["Date"] = pd.to_Datetime(df["Date"], format="%d/%m/%Y", errors="coerce")
            
            # Check if all values are NaT (invalid)
            if df["Date"].isna().all():
                st.error("🚨 The 'Date' column is invalid or incorrectly formatted in Google Sheets.")
                return pd.DataFrame()

            st.write("✅ Date Column Sample (after conversion):", df["Date"].head(5))  # Debugging

        else:
            st.error("🚨 The 'Date' column is missing in the Google Sheet.")
            return pd.DataFrame()

        # Convert 'hr' column to numeric safely
        if "hr" in df.columns:
            df["hr"] = pd.to_numeric(df["hr"], errors="coerce").fillna(0)

        return df

    except Exception as e:
        st.error(f"❌ Error fetching data from worksheet: {e}")
        return pd.DataFrame()

# Function to load and preprocess data
@st.cache_data
def load_data(spreadsheet_id, sheet_name):
    data = fetch_data_from_sheet(spreadsheet_id, sheet_name)

    # Normalize column names
    data.columns = data.columns.str.strip().str.lower()

    # ValiDate required columns
    required_columns = [
        "Date", "subject", "hr", "teachers name",
        "chapter taken", "type of class", "student id", "student"
    ]
    missing_columns = set(required_columns) - set(data.columns)
    if missing_columns:
        raise ValueError(f"Missing columns in data: {missing_columns}")

    # Keep only necessary columns
    data = data[required_columns]

    # Normalize student-related columns
    data["student id"] = data["student id"].astype(str).str.lower().str.strip()
    data["student"] = data["student"].astype(str).str.lower().str.strip()

    return data

# Main application
def main():
    st.title("Student Insights and Analysis")

    # Load data
    try:
        student_data = load_data(SPREADSHEET_ID, WORKSHEET_NAME)
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
        format_func=lambda x: pd.to_Datetime(f"2024-{x}-01").strftime('%B'),  # Show month names
    )

    if st.button("Fetch Data"):
        if not student_id or len(student_name_part) < 4:
            st.error("Please enter a valid Student ID and at least 4 characters of your name.")
            return

        # **Debugging check: Ensure "Date" is Datetime before filtering**
        if not pd.api.types.is_Datetime64_any_dtype(student_data["Date"]):
            st.error("🚨 The 'Date' column is not in Datetime format. Please check the Google Sheet.")
            return

        # Filter data based on student ID, partial name match, and month
        filtered_data = student_data[
            (student_data["student id"] == student_id) &
            (student_data["student"].str.contains(student_name_part, na=False)) &
            (student_data["Date"].dt.month == month)
        ]

        if not filtered_data.empty:
            student_name = filtered_data["student"].iloc[0].title()
            st.subheader(f"Welcome, {student_name}!")

            # Format 'Date' for display
            filtered_data["Date"] = filtered_data["Date"].dt.strftime('%d/%m/%Y')

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

        else:
            st.error(f"No data found for the given Student ID, Name, and selected month ({pd.to_Datetime(f'2024-{month}-01').strftime('%B')}).")

# Run the app
if __name__ == "__main__":
    main()
