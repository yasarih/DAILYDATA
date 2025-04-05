import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
import json

# Set page layout and title
st.set_page_config(
    page_title="Angle Belearn Insights",
    page_icon="🎓",
    layout="wide",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": None
    }
)

# Function to load credentials from Streamlit secrets for the new project
def load_credentials_from_secrets():
    try:
        credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])
        return credentials_info
    except KeyError:
        st.error("Google credentials not found in Streamlit secrets.")
        return None

# Function to connect to Google Sheets using the credentials from secrets for the new project
def connect_to_google_sheets(spreadsheet_id, worksheet_name):
    credentials_info = load_credentials_from_secrets()
    if not credentials_info:
        return None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ]

    try:
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=scopes
        )
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

# Function to fetch all data without caching to always get updated values
def fetch_data_from_sheet(spreadsheet_id, worksheet_name):
    sheet = connect_to_google_sheets(spreadsheet_id, worksheet_name)
    if not sheet:
        st.warning(f"Could not establish a connection to the worksheet '{worksheet_name}'.")
        return pd.DataFrame()  # Return empty DataFrame if connection fails
    try:
        data = sheet.get_all_values()
        if data:
            headers = pd.Series(data[0]).fillna('').str.strip()
            headers = headers.where(headers != '', other='Unnamed')
            headers = headers + headers.groupby(headers).cumcount().astype(str).replace('0', '')
            df = pd.DataFrame(data[1:], columns=headers)
            df.replace('', pd.NA, inplace=True)
            df.ffill(inplace=True)
            if 'Hr' in df.columns:
                df['Hr'] = pd.to_numeric(df['Hr'], errors='coerce').fillna(0)
            return df
        else:
            st.warning(f"No data found in worksheet '{worksheet_name}'.")
            return pd.DataFrame()
    except gspread.exceptions.APIError as api_error:
        st.error(f"Google Sheets API error fetching data from '{worksheet_name}': {api_error}")
    except Exception as e:
        st.error(f"Error fetching data from '{worksheet_name}': {e}")
    return pd.DataFrame()

# Function to merge student and EM data
def get_merged_data_with_em():
    main_data = fetch_data_from_sheet("1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4", "Student class details")
    em_data = fetch_data_from_sheet("1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4", "Student Data")

    if main_data.empty:
        st.warning("Main data is empty. Please check the 'Student class details' sheet.")
    if em_data.empty:
        st.warning("EM data is empty. Please check the 'Student Data' sheet.")
    if main_data.empty or em_data.empty:
        return pd.DataFrame()

    main_data = main_data.rename(columns={'Student id': 'Student ID'})
    em_data = em_data.rename(columns={'Student id': 'Student ID', 'EM': 'EM', 'EM Phone': 'Phone Number'})

    # Merge data including the Supalearn Password column from the main sheet
    merged_data = main_data.merge(em_data[['Student ID', 'EM', 'Phone Number']], on="Student ID", how="left")
    merged_data = merged_data.merge(main_data[['Student ID', 'Supalearn Password']], on="Student ID", how="left")

    return merged_data

# Function to show student EM data with phone numbers
def show_student_em_table(data, teacher_name, role):
    """
    Display a unique list of students taken by the logged-in teacher, 
    showing their ID, name, EM, EM's phone number, and Supalearn Password (if role is Teacher).
    Args:
    - data: Merged DataFrame containing student and EM details.
    - teacher_name: Name of the logged-in teacher.
    - role: Role of the logged-in user ('Teacher' or 'Student').
    """
    st.subheader(f"Unique List of Students for Teacher: {teacher_name}")

    # Check if required columns exist in the data
    required_columns = {"Student ID", "Student", "EM", "Phone Number", "Teachers Name"}
    if not required_columns.issubset(data.columns):
        st.error(f"Missing columns in the data. Expected: {required_columns}.")
        return

    # Filter data for the logged-in teacher
    teacher_students = data[data["Teachers Name"].str.lower() == teacher_name.lower()]

    if teacher_students.empty:
        st.warning("No students found for the logged-in teacher.")
        return

    # Remove duplicate students
    teacher_students = teacher_students.drop_duplicates(subset=["Student ID", "Student"])

    # Select relevant columns for display
    display_columns = ["Student ID", "Student", "EM", "Phone Number"]
    
    # Add Supalearn Password if the role is Teacher
    if role == "Teacher":
        display_columns.append("Supalearn Password")
    
    teacher_students = teacher_students[display_columns]

    # Display the unique list of students
    st.write(teacher_students)

    # Display summary stats
    st.write(f"**Total Unique Students:** {len(teacher_students)}")

# Function to manage data based on the selected role (Student or Teacher)
def manage_data(data, role):
    st.subheader(f"{role} Data")

    if "MM" in data.columns:
        month = st.sidebar.selectbox("Select Month", sorted(data["MM"].unique()))
        year = st.sidebar.selectbox("Select Year", sorted(data["Year"].unique()))
    else:
        st.warning("Month data ('MM' column) not found. Available columns are:")
        st.write(data.columns.tolist())
        return

    if role == "Teacher":
        if "Teachers ID" not in data.columns:
            st.error("The column 'Teacher ID' is missing from the data. Please check the source sheet.")
            return

        teacher_id = st.text_input("Enter Your Teacher ID").strip().lower()
        teacher_name_part = st.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

        if st.button("Verify Teacher"):
            filtered_data = data[
                (data["MM"] == month) & 
                (data["Year"] == year) &  # Added condition to filter by year
                (data["Teachers ID"].str.lower().str.strip() == teacher_id) &
                (data["Teachers Name"].str.lower().str.contains(teacher_name_part))
            ]

            if not filtered_data.empty:
                teacher_name = filtered_data["Teachers Name"].iloc[0]
                st.subheader(f"👩‍🏫 Welcome, {teacher_name}!")

                required_columns = ["Date", "Student ID", "Student", "Class", "Syllabus", "Type of class", "Hr"]
                missing_columns = [col for col in required_columns if col not in filtered_data.columns]

                if missing_columns:
                    st.error(f"The following required columns are missing: {missing_columns}")
                else:
                    show_student_em_table(filtered_data, teacher_name, role)

            else:
                st.error("Verification failed. Please check your Teacher ID and name.")

    elif role == "Student":
        student_id = st.text_input("Enter Student ID").strip().lower()
        student_name_part = st.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

        if st.button("Verify Student"):
            filtered_data = data[(data["MM"] == month) &
                                 (data["Student ID"].str.lower().str.strip() == student_id) &
                                 (data["Student"].str.lower().str.contains(student_name_part))]

            if not filtered_data.empty:
                # Display student's name at the top
                student_name = filtered_data["Student"].iloc[0]
                st.subheader(f"👨‍🎓 Welcome, {student_name}!")

                required_columns = ["Date", "Subject", "Hr", "Teachers Name", "Chapter taken", "Type of class"]
                missing_columns = [col for col in required_columns if col not in filtered_data.columns]

                if missing_columns:
                    st.error(f"The following required columns are missing: {missing_columns}")
                    st.write("Available columns in filtered_data:", filtered_data.columns.tolist())
                else:
                    # Select relevant columns for display
                    filtered_data = filtered_data[required_columns]
                    st.subheader("📚 Your Monthly Class Data")
                    st.write(filtered_data)

                    # Calculate total hours
                    total_hours = filtered_data["Hr"].sum()
                    st.write(f"**Total Hours for {month}th month :** {total_hours:.2f}")

                    # Subject-wise breakdown
                    subject_hours = filtered_data.groupby("Subject")["Hr"].sum().reset_index()
                    subject_hours = subject_hours.rename(columns={"Hr": "Total Hours"})
                    st.subheader("📊 Subject-wise Hour Breakdown")
                    st.write(subject_hours)

            else:
                st.error("Verification failed. Please check your details.")

# Main function to handle user role selection and page display
def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=250)
    st.title("Angle Belearn: Your Daily Class Insights")

    # Refresh Data button in the sidebar
    if st.sidebar.button("Refresh Data"):
        # Clear cached data if it exists to ensure a fresh fetch
        st.session_state.data = get_merged_data_with_em()  # Forcefully reload data from Google Sheets
        st.success("Data refreshed successfully!")

    # Load data if it is not already in session state
    if "data" not in st.session_state:
        st.session_state.data = get_merged_data_with_em()

    # Role selection and data management
    role = st.sidebar.radio("Select your role:", ["Select", "Student", "Teacher"], index=0)

    if role != "Select":
        manage_data(st.session_state.data, role)
    else:
        st.info("Please select a role from the sidebar.")

if __name__ == "__main__":
    main()
