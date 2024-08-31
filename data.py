import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import matplotlib.pyplot as plt
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
def fetch_all_data(spreadsheet_name, worksheet_name, expected_headers):
    sheet = connect_to_google_sheets(spreadsheet_name, worksheet_name)
    data = sheet.get_all_records(expected_headers=expected_headers)
    return pd.DataFrame(data)

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
        filtered_data = filtered_data[filtered_data.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]

    # Drop specific columns based on the role
    if role == "Student":
        filtered_data = filtered_data.drop(columns=["Year", "MM",  "Class", "Board"], errors='ignore')
    elif role == "Teacher":
        filtered_data = filtered_data.drop(columns=["Year", "MM", "Teachers ID"], errors='ignore')

     # Identify duplicates for 'Date' and 'Student id'
    filtered_data['is_duplicate'] = filtered_data.duplicated(subset=['Date', 'Student id'], keep=False)
    
    # Highlight duplicates using style
    styled_data = filtered_data.style.apply(lambda x: ['background-color: red' if x.is_duplicate else '' for _ in x], axis=1)

    # Display the styled DataFrame
    st.dataframe(styled_data)

    # Create bar charts based on role
    if role == "Student":
        create_bar_chart(filtered_data, 'Subject', 'Hr', 'Hours spent on each subject')
    elif role == "Teacher":
        create_bar_chart(filtered_data, 'Student', 'Hr', 'Hours spent teaching each student')

# Function to create and display a bar chart
def create_bar_chart(data, label_column, value_column, title):
    fig, ax = plt.subplots()
    bar_data = data.groupby(label_column)[value_column].sum()
    ax.bar(bar_data.index, bar_data.values)
    ax.set_xlabel(label_column)
    ax.set_ylabel(value_column)
    plt.xticks(rotation=45)
    plt.title(title)
    st.pyplot(fig)

# Main function to handle user role selection and page display
def main():
    st.title("Angle Belearn: Your Daily Class Insights")

    # Sheet and headers details
    spreadsheet_name = 'Student Daily Class Details 2024'
    worksheet_name = 'Student class details'
    expected_headers = ["Year", "MM", "Date", "Student id", "Student", "Hr", "Teachers ID", "Teachers Name", "Class", "Syllabus", "Subject", "Chapter taken"]

    # Cache and fetch the entire dataset once
    data = fetch_all_data(spreadsheet_name, worksheet_name, expected_headers)

    # Create a sidebar with role options
    role = st.sidebar.selectbox("Select your role:", ["Select", "Student", "Teacher"])

    # Load the corresponding page based on user selection
    if role == "Student":
        student_page(data)
    elif role == "Teacher":
        teacher_page(data)
    else:
        st.write("Please select a role from the sidebar.")

# Function to display the Student page
def student_page(data):
    st.title("Student Page")
    manage_data(data, 'Student Daily Data', role="Student")

# Function to display the Teacher page
def teacher_page(data):
    st.title("Teacher Page")
    manage_data(data, 'Teacher Daily Data', role="Teacher")

if __name__ == "__main__":
    main()
