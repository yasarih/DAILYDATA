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

# Function to display a welcome message for the teacher
def welcome_teacher(teacher_name):
    st.markdown(f"""
        <div style="background-color:#f9f9f9; padding:10px; border-radius:10px; margin-bottom:20px;">
            <h1 style="color:#4CAF50; text-align:center; font-family:Georgia; font-size:45px;">
                👩‍🏫 Welcome, {teacher_name}!
            </h1>
            <p style="text-align:center; color:#555; font-size:18px; font-family:Arial;">
                We're thrilled to have you here today! Let's dive into your teaching insights 📊.
            </p>
        </div>
    """, unsafe_allow_html=True)

# Main function to manage data filtering and UI
def manage_data(data, role):
    st.subheader(f"{role} Data")

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
    filtered_data = data[(data["Date"] >= start_date) & (data["Date"] <= end_date)]

    st.write(f"Displaying data from {start_date.date()} to {end_date.date()}")

    # Highlight duplicate entries with a yellow background
    st.dataframe(filtered_data.style.apply(highlight_duplicates, axis=1))

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

    if role != "Select":
        manage_data(st.session_state.data, role)
    else:
        st.info("Please select a role from the sidebar.")

if __name__ == "__main__":
    main()
