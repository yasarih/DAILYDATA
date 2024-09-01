import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
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
    
    # Use get_all_values to read all data including blank rows
    data = sheet.get_all_values()
    
    # Check if data is non-empty and has headers
    if data and len(data) > 1:
        # Convert the data into a DataFrame
        df = pd.DataFrame(data[1:], columns=data[0])  # Skip the first row for headers
    else:
        # Handle empty or incorrectly formatted data
        st.warning("No data found or the sheet is incorrectly formatted.")
        df = pd.DataFrame()  # Return an empty DataFrame

    return df

# Function to manage data display and filtering for a specific worksheet
def manage_data(data, sheet_name, role):
    st.subheader(f"{sheet_name} Data")

    # Role-specific filtering
    if role == "Student":
        st.sidebar.subheader("Filter Options for Student")
        
        # Filter by Student ID
        student_ids = sorted(data["Student id"].unique())
        selected_student_id = st.sidebar.selectbox("Enter Student ID", student_ids)

        # Filter data by selected student ID
        filtered_data = data[data["Student id"] == selected_student_id]
        
        # Ask for the first four letters of the student's name
        input_name = st.sidebar.text_input("Enter the first four letters of your name")
        # Verify the input name
        actual_name = filtered_data["Student"].values[0]  # Assumes there's only one matching row
        if input_name.lower() == actual_name[:4].lower():
            # Proceed if names match
            show_filtered_data(filtered_data, role)
        else:
            st.error("Name does not match. Please check your input.")

    elif role == "Teacher":
        st.sidebar.subheader("Filter Options for Teacher")
        
        # Filter by Teacher ID
        teacher_ids = sorted(data["Teachers ID"].unique())
        selected_teacher_id = st.sidebar.selectbox("Enter Teacher ID", teacher_ids)

        # Filter data by selected teacher ID
        filtered_data = data[data["Teachers ID"] == selected_teacher_id]
        
        # Ask for the first four letters of the teacher's name
        input_name = st.sidebar.text_input("Enter the first four letters of your name")
        # Verify the input name
        actual_name = filtered_data["Teachers Name"].values[0]  # Assumes there's only one matching row
        if input_name.lower() == actual_name[:4].lower():
            # Proceed if names match
            show_filtered_data(filtered_data, role)
        else:
            st.error("Name does not match. Please check your input.")

def show_filtered_data(filtered_data, role):
    # Filter by Month Number
    months = sorted(filtered_data["MM"].unique())
    selected_month = st.sidebar.selectbox("Select Month", months)

    # Apply month filter
    filtered_data = filtered_data[filtered_data["MM"] == selected_month]

    # Universal filter: text input to filter across all columns
    search_term = st.sidebar.text_input("Search All Columns", "")
    if search_term:
        filtered_data = filtered_data[filtered_data.apply(lambda row: row.astype(str).str.contains(search_term,
