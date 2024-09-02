import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# Custom CSS for Styling
def add_custom_css():
    st.markdown("""
        <style>
        /* General App Background */
        body {
            background-color: #e0f7fa;  /* Light blue background */
        }

        /* Header Titles */
        h1, h2, h3, h4, h5, h6 {
            color: #333333;
            font-family: 'Arial', sans-serif;
        }

        /* Subheader Styles */
        .css-18ni7ap h3 {
            background-color: #4e79a7;
            color: white;
            padding: 10px;
            border-radius: 8px;
        }

        /* DataFrame Styling */
        .dataframe {
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 20px;
        }
        .dataframe th, .dataframe td {
            border: 1px solid #dddddd;
            text-align: left;
            padding: 8px;
        }
        .dataframe th {
            background-color: #4e79a7;
            color: white;
        }
        .dataframe tr:nth-child(even) {
            background-color: #f2f2f2;
        }

        /* Button Styling */
        .stButton>button {
            color: white;
            background-color: #4e79a7;
            border-radius: 8px;
        }
        </style>
        """, unsafe_allow_html=True)

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
    st.subheader(f"📊 {sheet_name} Data")

    # Check if month selection is in session state
    if 'selected_month' not in st.session_state:
        st.session_state.selected_month = None

    # Role-specific filtering
    if role == "Student":
        st.header("Filter Options for Student")
        # Filter by Student ID
        student_ids = sorted(data["Student id"].unique())
        selected_student_id = st.selectbox("Enter Student ID", student_ids, key='student_id')

        # Ask for the first four letters of the student's name
        input_name = st.text_input("Enter the first four letters of your name", key='student_name_input')
        
        # Month selection
        months = sorted(data["MM"].unique())
        selected_month = st.selectbox("Select Month", months, key='month_selection')

        # Button for login verification
        if st.button("Verify"):
            # Filter data by selected student ID and month
            filtered_data = data[(data["Student id"] == selected_student_id) & (data["MM"] == selected_month)]

            # Verify the input name
            if not filtered_data.empty:
                actual_name = filtered_data["Student"].values[0]  # Assumes there's only one matching row
                if input_name.lower() == actual_name[:4].lower():
                    # Proceed if names match
                    st.session_state.logged_in = True
                    st.session_state.role = role
                    st.session_state.filtered_data = filtered_data
                else:
                    st.error("Name does not match. Please check your input.")
            else:
                st.error("No data found for the selected Student ID and Month.")

    elif role == "Teacher":
        st.header("Filter Options for Teacher")
        # Filter by Teacher ID
        teacher_ids = sorted(data["Teachers ID"].unique())
        selected_teacher_id = st.selectbox("Enter Teacher ID", teacher_ids, key='teacher_id')

        # Ask for the first four letters of the teacher's name
        input_name = st.text_input("Enter the first four letters of your name", key='teacher_name_input')

        # Month selection
        months = sorted(data["MM"].unique())
        selected_month = st.selectbox("Select Month", months, key='month_selection_teacher')

        # Button for login verification
        if st.button("Verify"):
            # Filter data by selected teacher ID and month
            filtered_data = data[(data["Teachers ID"] == selected_teacher_id) & (data["MM"] == selected_month)]

            # Verify the input name
            if not filtered_data.empty:
                actual_name = filtered_data["Teachers Name"].values[0]  # Assumes there's only one matching row
                if input_name.lower() == actual_name[:4].lower():
                    # Proceed if names match
                    st.session_state.logged_in = True
                    st.session_state.role = role
                    st.session_state.filtered_data = filtered_data
                else:
                    st.error("Name does not match. Please check your input.")
            else:
                st.error("No data found for the selected Teacher ID and Month.")

    # Display filtered data if logged in
    if 'logged_in' in st.session_state and st.session_state.logged_in and st.session_state.role == role:
        show_filtered_data(st.session_state.filtered_data, role)

def show_filtered_data(filtered_data, role):
    # Add Serial Numbers
    filtered_data.insert(0, 'Sl. No.', range(1, len(filtered_data) + 1))

    if role == "Student":
        # Select specific columns to show for students
        filtered_data = filtered_data[["Sl. No.", "Date", "Subject", "Teachers Name", "Hr", "Type of class"]]
        
        # Convert 'Hr' to numeric and format to two decimal places
        filtered_data["Hr"] = pd.to_numeric(filtered_data["Hr"], errors='coerce').round(2)
        
        # Display the filtered data without the index
        st.write(filtered_data.to_html(index=False), unsafe_allow_html=True)

        # Calculate and display total hours and total hours per subject
        total_hours = filtered_data["Hr"].sum()
        st.write(f"**Total Hours**: {total_hours:.2f}")
        
        subject_hours = filtered_data.groupby("Subject")["Hr"].sum()
        st.write("**Total Hours per Subject:**")
        st.write(subject_hours)

    elif role == "Teacher":
        # Select specific columns to show for teachers
        filtered_data = filtered_data[["Sl. No.", "Date", "Student id", "Student", "Hr", "Type of class"]]
        
        # Convert 'Hr' to numeric and format to two decimal places
        filtered_data["Hr"] = pd.to_numeric(filtered_data["Hr"], errors='coerce').round(2)
        
        # **Duplicate Checking for Teachers Only**
        # Identify duplicates for 'Date' and 'Student id'
        filtered_data['is_duplicate'] = filtered_data.duplicated(subset=['Date', 'Student id'], keep=False)
        
        # Highlight duplicates using style
        def highlight_duplicates(row):
            return ['background-color: red' if row.is_duplicate else '' for _ in row]

        styled_data = filtered_data.style.apply(highlight_duplicates, axis=1)
        
        # Display the styled DataFrame without the index
        st.write(styled_data.to_html(index=False), unsafe_allow_html=True)
        
        # Calculate and display total hours and hours per student
        total_hours = filtered_data["Hr"].sum()
        st.write(f"**Total Hours**: {total_hours:.2f}")
        
        student_hours = filtered_data.groupby("Student")["Hr"].sum()
        st.write("**Total Hours per Student:**")
        st.write(student_hours)

# Main function to handle user role selection and page display
def main():
    add_custom_css()  # Add custom CSS for better styling
    st.title("📘 Angle Belearn: Your Daily Class Insights")

    # Sheet and headers details
    spreadsheet_name = 'Student Daily Class Details 2024'
    worksheet_name = 'Student class details'

    # Cache and fetch the entire dataset once
    data = fetch_all_data(spreadsheet_name, worksheet_name)

    # Check if data is empty and handle the case
    if data.empty:
        st.error("No data available or failed to fetch data from Google Sheets.")
        return

    # All elements on the main page
    st.image("https://anglebelearn.com/wp-content/uploads/2023/06/Angle-Belearn-Logo.svg", use_column_width=True)  # Add your logo URL
    st.header("User Role Selection")
    role = st.selectbox("Select your role:", ["Select", "Student", "Teacher"])

    # Load the corresponding page based on user selection
    if role == "Student":
        student_page(data)
    elif role == "Teacher":
        teacher_page(data)
    else:
        st.write("Please select a role from the options above.")

# Function to display the Student page
def student_page(data):
    st.title("🎓 Student Page")
    manage_data(data, 'Student Daily Data', role="Student")

# Function to display the Teacher page
def teacher_page(data):
    st.title("👩‍🏫 Teacher Page")
    manage_data(data, 'Teacher Daily Data', role="Teacher")

if __name__ == "__main__":
    main()
