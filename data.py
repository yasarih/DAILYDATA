import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
import json

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

# Cache data fetching to prevent redundant calls
@st.cache_data
def fetch_all_data(spreadsheet_name, worksheet_name):
    sheet = connect_to_google_sheets(spreadsheet_name, worksheet_name)
    data = sheet.get_all_values()

    if data and len(data) > 1:
        headers = pd.Series(data[0])
        headers = headers.fillna('').str.strip()
        headers = headers.where(headers != '', other='Unnamed')
        headers = headers + headers.groupby(headers).cumcount().astype(str).replace('0', '')

        df = pd.DataFrame(data[1:], columns=headers)
        df.replace('', np.nan, inplace=True)
        df.fillna(method='ffill', inplace=True)

        for column in df.columns:
            df[column] = df[column].astype(str).str.strip()

        numeric_cols = ['Hr']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    else:
        st.warning("No data found or the sheet is incorrectly formatted.")
        df = pd.DataFrame()

    return df

# Function to manage data display and filtering for a specific worksheet
def manage_data(data, role):
    st.subheader(f"{role} Data")

    if role == "Student":
        # Filter by Student ID and verify
        student_id = st.sidebar.text_input("Enter Student ID")
        student_name_prefix = st.sidebar.text_input("Enter the first four letters of your name")
        if st.sidebar.button("Verify Student"):
            filtered_data = data[(data["Student id"] == student_id) & 
                                 (data["Student"].str[:4].str.lower() == student_name_prefix.lower())]
            if not filtered_data.empty:
                st.write(filtered_data)
            else:
                st.error("Verification failed. Please check your details.")
    
    elif role == "Teacher":
        # Filter by Teacher ID and verify
        teacher_id = st.sidebar.text_input("Enter Teacher ID")
        teacher_name_prefix = st.sidebar.text_input("Enter the first four letters of your name")
        if st.sidebar.button("Verify Teacher"):
            filtered_data = data[(data["Teachers ID"] == teacher_id) & 
                                 (data["Teachers Name"].str[:4].str.lower() == teacher_name_prefix.lower())]
            if not filtered_data.empty:
                st.write(filtered_data)
            else:
                st.error("Verification failed. Please check your details.")

# Main function to handle user role selection and page display
def main():
    st.title("Angle Belearn: Your Daily Class Insights")

    # Sheet and headers details
    spreadsheet_name = 'Student Daily Class Details 2024'
    worksheet_name = 'Student class details'

    # Create a sidebar with role options
    role = st.sidebar.selectbox("Select your role:", ["Select", "Student", "Teacher"])

    if role == "Student" or role == "Teacher":
        data = fetch_all_data(spreadsheet_name, worksheet_name)
        manage_data(data, role)
    else:
        st.write("Please select a role from the sidebar.")

if __name__ == "__main__":
    main()
