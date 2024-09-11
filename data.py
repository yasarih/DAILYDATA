import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
from datetime import datetime

# Set page layout and title
st.set_page_config(
    page_title="Angle Belearn Insights",
    page_icon="🎓",
    layout="wide"
)

# Function to load credentials from Streamlit secrets for the new project
def load_credentials_from_secrets():
    credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])
    return credentials_info

# Function to connect to Google Sheets using the credentials from secrets for the new project
def connect_to_google_sheets(spreadsheet_name, worksheet_name):
    # Load the credentials from Streamlit secrets
    credentials_info = load_credentials_from_secrets()
    
    # Define the required scopes for Google Sheets API
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ]
    
    # Create credentials using the loaded info and defined scopes
    credentials = Credentials.from_service_account_info(
        credentials_info,
        scopes=scopes
    )
    
    # Authorize gspread with the credentials
    client = gspread.authorize(credentials)
    
    # Open the spreadsheet and access the specified worksheet
    sheet = client.open(spreadsheet_name).worksheet(worksheet_name)
    return sheet

# Function to fetch all data without caching to always get updated values
def fetch_all_data(spreadsheet_name, worksheet_name):
    with st.spinner("Fetching data..."):
        sheet = connect_to_google_sheets(spreadsheet_name, worksheet_name)
        data = sheet.get_all_values()

        if data and len(data) > 1:
            headers = pd.Series(data[0])
            headers = headers.fillna('').str.strip()
            headers = headers.where(headers != '', other='Unnamed')
            headers = headers + headers.groupby(headers).cumcount().astype(str).replace('0', '')

            df = pd.DataFrame(data[1:], columns=headers)

            # Strip any extra spaces from all columns
            for column in df.columns:
                df[column] = df[column].astype(str).str.strip()

            # Remove fully blank rows
            df.replace('', np.nan, inplace=True)
            df.dropna(how='all', inplace=True)

            # Convert 'Date' column to datetime format and handle invalid dates
            df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d", errors="coerce")

            # Drop rows where 'Date' could not be parsed (i.e., where 'Date' is NaT)
            df.dropna(subset=["Date"], inplace=True)

            numeric_cols = ['Hr']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        else:
            st.warning("No data found or the sheet is incorrectly formatted.")
            df = pd.DataFrame()

        return df

# Function to highlight duplicate rows with yellow background
def highlight_duplicates(df):
    # Identify duplicate rows
    is_duplicate = df.duplicated(keep=False)

    # Define the style for the duplicate rows
    return ['background-color: yellow' if is_duplicate.iloc[i] else '' for i in range(len(df))]

# Teacher verification function
def verify_teacher(data, teacher_id, teacher_name_part):
    # Convert teacher's ID and name to lowercase for case-insensitive comparison
    teacher_id = teacher_id.lower().strip()
    teacher_name_part = teacher_name_part.lower().strip()

    # Filter data to find matching Teacher ID and Name Part
    matching_data = data[(data["Teachers ID"].str.lower().str.strip() == teacher_id) &
                         (data["Teachers Name"].str.lower().str.contains(teacher_name_part))]
    
    if not matching_data.empty:
        return True, matching_data
    else:
        return False, None

# Main function to manage data filtering and UI
def manage_data(data, role):
    st.subheader(f"{role} Data")

    if role == "Teacher":
        # Teacher ID and Name input for verification
        teacher_id = st.sidebar.text_input("Enter Teacher ID").strip().lower()
        teacher_name_part = st.sidebar.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

        if st.sidebar.button("Verify Teacher"):
            is_verified, teacher_data = verify_teacher(data, teacher_id, teacher_name_part)

            if is_verified:
                teacher_name = teacher_data["Teachers Name"].iloc[0]  # Get the first matching teacher name
                st.success(f"Welcome {teacher_name}!")

                # Get today's date
                today = datetime.today()

                # Generate month-year options for the past 12 months
                months = pd.date_range(end=today, periods=12, freq='MS').strftime("%B %Y").tolist()

                # Select Month (dropdown)
                selected_month = st.sidebar.selectbox("Select Month", months)

                # Convert selected month back to a datetime object (1st of the selected month)
                start_date = pd.to_datetime(selected_month, format='%B %Y')

                # Date range: From 1st of selected month to today's date
                end_date = today

                # Filter the data by the selected date range
                filtered_data = teacher_data[(teacher_data["Date"] >= start_date) & (teacher_data["Date"] <= end_date)]

                st.write(f"Displaying data from {start_date.date()} to {end_date.date()}")

                # Highlight duplicate entries with a yellow background
                st.dataframe(filtered_data.style.apply(highlight_duplicates, axis=1))

            else:
                st.error("Verification failed. Please check your Teacher ID and Name.")

# Main function to handle user role selection and page display
def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=170)

    st.title("Angle Belearn: Your Daily Class Insights")

    # Sheet and headers details
    spreadsheet_name = 'Student Daily Class Details 2024'
    worksheet_name = 'Student class details'

    role = st.sidebar.radio("Select your role:", ["Select", "Student", "Teacher"], index=0)

    if st.sidebar.button("Refresh Data"):
        st.session_state.data = fetch_all_data(spreadsheet_name, worksheet_name)
    
    if "data" not in st.session_state:
        st.session_state.data = fetch_all_data(spreadsheet_name, worksheet_name)

    if role == "Teacher":
        manage_data(st.session_state.data, role)
    else:
        st.info("Please select 'Teacher' to proceed.")

if __name__ == "__main__":
    main()
