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

# Function to fetch all data without caching to always get updated values
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

    # Filter by month before verification
    month = st.sidebar.selectbox("Select Month", sorted(data["MM"].unique()))

    if role == "Student":
        # Filter by Student ID and verify
        student_id = st.sidebar.text_input("Enter Student ID").strip().lower()
        student_name_prefix = st.sidebar.text_input("Enter the first four letters of your name").strip().lower()
        if st.sidebar.button("Verify Student"):
            filtered_data = data[(data["MM"] == month) & 
                                 (data["Student id"].str.lower() == student_id) & 
                                 (data["Student"].str[:4].str.lower() == student_name_prefix)]
            if not filtered_data.empty:
                show_filtered_data(filtered_data, role)
            else:
                st.error("Verification failed. Please check your details.")
    
    elif role == "Teacher":
        # Filter by Teacher ID and verify
        teacher_id = st.sidebar.text_input("Enter Teacher ID").strip().lower()
        teacher_name_prefix = st.sidebar.text_input("Enter the first four letters of your name").strip().lower()
        if st.sidebar.button("Verify Teacher"):
            filtered_data = data[(data["MM"] == month) & 
                                 (data["Teachers ID"].str.lower() == teacher_id) & 
                                 (data["Teachers Name"].str[:4].str.lower() == teacher_name_prefix)]
            if not filtered_data.empty:
                show_filtered_data(filtered_data, role)
            else:
                st.error("Verification failed. Please check your details.")

def show_filtered_data(filtered_data, role):
    # Customize columns display based on role
    if role == "Student":
        filtered_data = filtered_data[["Date", "Subject", "Chapter taken", "Teachers Name", "Hr", "Type of class"]]
        filtered_data["Hr"] = filtered_data["Hr"].round(2)  # Round hours to 2 decimal places

        # Display total hours and subject-wise breakdown
        total_hours = filtered_data["Hr"].sum()
        st.write(f"**Total Hours of Classes:** {total_hours:.2f}")
        subject_hours = filtered_data.groupby("Subject")["Hr"].sum()
        st.write("**Subject-wise Hours:**")
        st.write(subject_hours)

    elif role == "Teacher":
        filtered_data = filtered_data[["Date", "Student id", "Student", "Chapter taken", "Hr", "Type of class"]]
        filtered_data["Hr"] = filtered_data["Hr"].round(2)  # Round hours to 2 decimal places

        # Highlight duplicate entries for teachers
        filtered_data['is_duplicate'] = filtered_data.duplicated(subset=['Date', 'Student id'], keep=False)
        styled_data = filtered_data.style.apply(lambda x: ['background-color: yellow' if x.is_duplicate else '' for _ in x], axis=1)
        st.dataframe(styled_data)

        # Display total hours and student-wise breakdown
        total_hours = filtered_data["Hr"].sum()
        #st.write(f"**Total Hours of Classes:** {total_hours:.2f}")
        student_hours = filtered_data.groupby("Student")["Hr"].sum()
        st.write("**Student-wise Hours:**")
        st.write(student_hours)

    # Display the filtered data for students
    st.write(filtered_data)

# Main function to handle user role selection and page display
def main():
    st.title("Angle Belearn: Your Daily Class Insights")

    # Sheet and headers details
    spreadsheet_name = 'Student Daily Class Details 2024'
    worksheet_name = 'Student class details'

    # Create a sidebar with role options
    role = st.sidebar.selectbox("Select your role:", ["Select", "Student", "Teacher"])

    if st.sidebar.button("Refresh Data"):
        st.session_state.data = fetch_all_data(spreadsheet_name, worksheet_name)
    
    if "data" not in st.session_state:
        st.session_state.data = fetch_all_data(spreadsheet_name, worksheet_name)

    if role == "Student" or role == "Teacher":
        manage_data(st.session_state.data, role)
    else:
        st.write("Please select a role from the sidebar.")

if __name__ == "__main__":
    main()
