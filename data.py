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

# Function to calculate salary for teachers
# Function to calculate salary for teachers
# Function to calculate salary for teachers
def calculate_salary(row):
    type_of_class = row['Type of class'].strip().lower()  # Use strip() to remove leading/trailing spaces
    board = row['Syllabus'].strip().lower()
    hours = row['Hr']
    
    try:
        class_level = int(row['Class'])  # Attempt to convert class to an integer
    except ValueError:
        return 0  # If class cannot be converted to an integer, return 0 salary

    # Regular, Additional, Exam classes
    if "regular" in type_of_class or "additional" in type_of_class or "exam" in type_of_class:
        if board in ['igcse', 'ib']:
            if 1 <= class_level <= 4:
                rate = 120
            elif 5 <= class_level <= 7:
                rate = 150
            elif 8 <= class_level <= 10:
                rate = 170
            elif 11 <= class_level <= 12:
                rate = 200
        else:  # Other boards
            if 1 <= class_level <= 4:
                rate = 120
            elif 5 <= class_level <= 10:
                rate = 150
            elif 11 <= class_level <= 12:
                rate = 180

    # Demo classes
    elif "demo" in type_of_class:
        if 1 <= class_level <= 10:
            rate = 150
        elif 11 <= class_level <= 12:
            rate = 180

    # Paid classes
    elif "paid" in type_of_class:
        return hours * 4 * 100  # Different calculation for paid classes

    else:
        return 0  # No salary for other types

    return rate * hours



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
        st.write(filtered_data)

    elif role == "Teacher":
        filtered_data = filtered_data[["Date", "Class", "Syllabus", "Type of class", "Chapter taken", "Hr"]]
        filtered_data["Hr"] = filtered_data["Hr"].round(2)  # Round hours to 2 decimal places

        # Calculate salary for each entry
        filtered_data['Salary'] = filtered_data.apply(calculate_salary, axis=1)

        # Highlight duplicate entries for teachers
        filtered_data['is_duplicate'] = filtered_data.duplicated(subset=['Date', 'Class'], keep=False)
        styled_data = filtered_data.style.apply(lambda x: ['background-color: yellow' if x.is_duplicate else '' for _ in x], axis=1)
        st.dataframe(styled_data)

        # Display total hours and class-wise breakdown
        total_hours = filtered_data["Hr"].sum()
        st.write(f"**Total Hours of Classes:** {total_hours:.2f}")
        
        # Split according to class, syllabus, and type of class
        class_split = filtered_data.groupby(["Class", "Syllabus", "Type of class"])["Hr"].sum()
        st.write("**Class, Syllabus, and Type of Class-wise Hours:**")
        st.write(class_split)

        # Display total salary
        total_salary = filtered_data["Salary"].sum()
        st.write(f"**Total Salary:** ₹{total_salary:.2f}")

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
