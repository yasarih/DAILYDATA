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
        df.ffill(inplace=True)  # Use forward fill instead of deprecated method

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

# Function to extract the first few letters from the name
def extract_first_letters(name):
    name_parts = name.strip().split()  # Split the name by spaces
    if len(name_parts) >= 2:
        # If there are two parts (first name and last name), take first three letters of first name and first letter of last name
        return (name_parts[0][:3] + name_parts[1][0]).lower()
    else:
        # Otherwise, take the first four letters of the first name
        return name_parts[0][:4].lower()

# Salary calculation function (for overall salary)
# Salary calculation function (for overall salary)
# Salary calculation function (for overall salary)
# Salary calculation function (for overall salary)
def calculate_salary(row):
    class_level = row['Class'].strip()  # Strip to remove any leading/trailing spaces
    syllabus = row['Syllabus'].strip().lower()
    class_type = row['Type of class'].strip().lower()
    hours = row['Hr']

    # Map class ranges to a single representative class level
    if "1-10" in class_level:
        numeric_class_level = 10
    elif "11-12" in class_level:
        numeric_class_level = 12
    else:
        try:
            numeric_class_level = int(class_level)
        except ValueError:
            return 0  # Return 0 for invalid class values

    # Handle demo classes
    if "demo" in class_type:
        if numeric_class_level <= 10:
            return hours * 150
        elif numeric_class_level >= 11:
            return hours * 180

    # Handle paid classes
    elif class_type.startswith("paid"):
        return hours * 4 * 100

    # Handle regular, additional, exam types based on syllabus and class level
    else:
        if syllabus in ['igcse', 'ib']:
            if 1 <= numeric_class_level <= 4:
                return hours * 120
            elif 5 <= numeric_class_level <= 7:
                return hours * 150
            elif 8 <= numeric_class_level <= 10:
                return hours * 170
            elif 11 <= numeric_class_level <= 12:
                return hours * 200
        else:
            if 1 <= numeric_class_level <= 4:
                return hours * 120
            elif 5 <= numeric_class_level <= 10:
                return hours * 150
            elif 11 <= numeric_class_level <= 12:
                return hours * 180

    return 0  # Default case if no condition matches
 # Default case if no condition matches
# Default case if no condition matches
# Default case if no condition matches

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
        filtered_data = filtered_data[["Date","Student id","Student", "Class", "Syllabus", "Type of class", "Hr"]]
        filtered_data["Hr"] = filtered_data["Hr"].round(2)  # Round hours to 2 decimal places

        st.subheader("Daily Class Data")
        st.write(filtered_data)

        # Calculate salary for total hours based on conditions
        filtered_data['Salary'] = filtered_data.apply(calculate_salary, axis=1)
        total_salary = filtered_data['Salary'].sum()

        # Grouping by Class, Syllabus, and Type of Class
        salary_split = filtered_data.groupby(['Class', 'Syllabus', 'Type of class']).agg({'Hr': 'sum', 'Salary': 'sum'}).reset_index()

        st.subheader("Salary Breakdown")
        st.write(f"**Total Salary till last update: ₹{total_salary:.2f}** _This is based on the basic pattern of our salary structure. Accurate values may change on a case-by-case basis._")
        
        # Show the salary breakdown
        st.write(salary_split)

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
