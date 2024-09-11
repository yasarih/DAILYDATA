import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
import json
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

def highlight_duplicates(df):
    # Identify duplicate rows
    is_duplicate = df.duplicated(keep=False)

    # Define the style for the duplicate rows
    return ['background-color: yellow' if is_duplicate.iloc[i] else '' for i in range(len(df))]

# Salary calculation function (for overall salary)
def calculate_salary(row):
    student_id = row['Student id'].strip().lower()  # To identify the demo class using student ID
    syllabus = row['Syllabus'].strip().lower()
    class_type = row['Type of class'].strip().lower()
    hours = row['Hr']

    # Handle demo classes based on the 'Student id'
    if 'demo class i - x' in student_id:
        return hours * 150
    elif 'demo class xi - xii' in student_id:
        return hours * 180

    # Handle paid classes
    elif class_type.startswith("paid"):
        return hours * 4 * 100

    # Handle regular, additional, exam types based on syllabus and class level
    else:
        class_level = int(row['Class']) if row['Class'].isdigit() else None

        if syllabus in ['igcse', 'ib']:
            if class_level is not None:
                if 1 <= class_level <= 4:
                    return hours * 120
                elif 5 <= class_level <= 7:
                    return hours * 150
                elif 8 <= class_level <= 10:
                    return hours * 170
                elif 11 <= class_level <= 13:
                    return hours * 200
        else:
            if class_level is not None:
                if 1 <= class_level <= 4:
                    return hours * 120
                elif 5 <= class_level <= 10:
                    return hours * 150
                elif 11 <= class_level <= 12:
                    return hours * 180

    return 0  # Default case if no condition matches

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

def manage_data(data, role):
    st.subheader(f"{role} Data")

    # Filter by month before verification
    month = st.sidebar.selectbox("Select Month", sorted(data["MM"].unique()))

    # **Add Date Range Picker**
    # Ensure that min_date and max_date are valid
    if not data["Date"].isnull().all():  # Check if there's any valid date in the column
        min_date = data["Date"].min().date()  # Get the earliest date in the dataset
        max_date = data["Date"].max().date()  # Get the latest date in the dataset
    else:
        # Fallback to today's date if no valid dates are present
        min_date = datetime.today().date()
        max_date = datetime.today().date()

    # Safely handle invalid date ranges
    if min_date and max_date:
        date_range = st.sidebar.date_input("Select Date Range", [min_date, max_date])
    else:
        st.error("No valid dates available in the dataset.")

    if date_range and len(date_range) == 2:
        start_date, end_date = date_range  # Unpack the date range
        # Filter the data by selected date range
        data = data[(data["Date"] >= pd.to_datetime(start_date)) & (data["Date"] <= pd.to_datetime(end_date))]

    # The rest of the code...


def show_filtered_data(filtered_data, role):
    if role == "Student":
        filtered_data = filtered_data[["Date", "Subject", "Chapter taken", "Teachers Name", "Hr", "Type of class"]]
        filtered_data["Hr"] = filtered_data["Hr"].round(2)  # Round hours to 2 decimal places

        # Display total hours and subject-wise breakdown
        total_hours = filtered_data["Hr"].sum()
        st.write(f"**Total Hours of Classes:** {total_hours:.2f}")
        subject_hours = filtered_data.groupby("Subject")["Hr"].sum()
        st.write("**Subject-wise Hours:**")
        st.bar_chart(subject_hours)
        
        # Highlight duplicate entries with a yellow background
        st.dataframe(filtered_data.style.apply(highlight_duplicates, axis=1))

    elif role == "Teacher":
        filtered_data = filtered_data[["Date","Student id","Student", "Class", "Syllabus", "Type of class", "Hr"]]
        filtered_data["Hr"] = filtered_data["Hr"].round(2)  # Round hours to 2 decimal places

        st.subheader("Daily Class Data")
        # Highlight duplicate entries with a yellow background
        st.dataframe(filtered_data.style.apply(highlight_duplicates, axis=1))

        # Calculate salary for total hours based on conditions
        filtered_data['Salary'] = filtered_data.apply(calculate_salary, axis=1)
        total_salary = filtered_data['Salary'].sum()

        # Grouping by Class, Syllabus, and Type of Class
        salary_split = filtered_data.groupby(['Class', 'Syllabus', 'Type of class']).agg({'Hr': 'sum', 'Salary': 'sum'}).reset_index()

        st.subheader("Salary Breakdown")
        st.write(f"**Total Salary till last update: ₹{total_salary:.2f}** _This is based on the basic pattern of our salary structure. Accurate values may change on a case-by-case basis._")
        
        # Show the salary breakdown
        st.write(salary_split)
        st.bar_chart(salary_split.set_index('Class')['Salary'])

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
