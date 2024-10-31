import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# Set page layout and title
st.set_page_config(
    page_title="Angle Belearn Insights",
    page_icon="🎓",
    layout="wide"
)

# Function to load credentials from Streamlit secrets
def load_credentials_from_secrets():
    credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])
    return credentials_info

# Cached function to connect to Google Sheets using credentials from Streamlit secrets
@st.cache_data
def connect_to_google_sheets(spreadsheet_id, worksheet_name):
    credentials_info = load_credentials_from_secrets()
    
    # Define scopes required for Google Sheets API
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ]
    
    # Create credentials and authorize gspread
    credentials = Credentials.from_service_account_info(
        credentials_info,
        scopes=scopes
    )
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    return sheet

# Cached function to fetch data from Google Sheets and standardize column names
@st.cache_data
def fetch_all_data(spreadsheet_id, worksheet_name):
    sheet = connect_to_google_sheets(spreadsheet_id, worksheet_name)
    data = sheet.get_all_values()
    if data and len(data) > 1:
        headers = pd.Series(data[0]).fillna('').str.strip()
        headers = headers.where(headers != '', other='Unnamed')
        headers = headers + headers.groupby(headers).cumcount().astype(str).replace('0', '')
        df = pd.DataFrame(data[1:], columns=headers)
        
        # Standardize column names by stripping whitespace and converting to lowercase
        df.columns = df.columns.str.strip().str.lower()
        
        df.replace('', pd.NA, inplace=True)
        df.ffill(inplace=True)
        
        # Convert 'hr' column to numeric if it exists
        if 'hr' in df.columns:
            df['hr'] = pd.to_numeric(df['hr'], errors='coerce').fillna(0)
        
        # Check for month column or extract month from 'date' column
        if 'mm' not in df.columns:
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                df['mm'] = df['date'].dt.strftime('%B')  # Extract month name
            else:
                st.error("No 'mm' or 'date' column found. Unable to determine month.")
        
        return df
    else:
        st.warning("No data found or the sheet is incorrectly formatted.")
        return pd.DataFrame()

# Function to merge student data with emergency contact (EM) data
@st.cache_data
def get_merged_data_with_em():
    main_data = fetch_all_data("17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y", "Student class details")
    em_data = fetch_all_data("17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y", "Student Data")
    
    # Normalize column names in both DataFrames
    main_data.columns = main_data.columns.str.lower().str.strip()
    em_data.columns = em_data.columns.str.lower().str.strip()
    
    # Merge on 'student id'
    merged_data = main_data.merge(em_data[['student id', 'em', 'phone number']], on="student id", how="left")
    
    # Check for and add 'mm' column if necessary
    if 'mm' not in merged_data.columns:
        if 'date' in merged_data.columns:
            merged_data['date'] = pd.to_datetime(merged_data['date'], errors='coerce')
            merged_data['mm'] = merged_data['date'].dt.strftime('%B')
        else:
            st.error("Unable to add 'mm' column. Ensure 'date' or 'mm' column exists in sheets.")
    
    return merged_data

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

# Function to display a table with students, their EMs, and EM's phone number
def show_student_em_table(data, teacher_name):
    st.subheader("List of Students with Corresponding EM and EM's Phone Number")

    # Define required columns in lowercase
    required_columns = ["teachers name", "student id", "em", "phone number"]
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        st.error(f"Missing columns in data for student EM table:")
        st.table(pd.DataFrame(missing_columns, columns=["Missing Columns"]))
        return

    # Determine student column name based on available columns
    if "student name" in data.columns:
        student_column = "student name"
    elif "student" in data.columns:
        student_column = "student"
    else:
        st.error("Student name column not found.")
        return

    # Filter data for the selected teacher using lowercase column names
    student_em_table = data[data["teachers name"] == teacher_name][["student id", student_column, "em", "phone number"]].drop_duplicates()
    st.write(student_em_table)

# Function to show filtered data based on role
def show_filtered_data(filtered_data, role):
    # Define required columns based on role in lowercase to match standardized column names
    student_columns = ["date", "subject", "chapter taken", "teachers name", "hr", "type of class"]
    teacher_columns = ["date", "student id", "student", "class", "syllabus", "type of class", "hr"]

    # Show available columns in filtered_data for debugging
    st.write("Filtered Data Columns:", filtered_data.columns.tolist())

    if role == "Student":
        # Check for missing columns
        missing_columns = [col for col in student_columns if col not in filtered_data.columns]
        if missing_columns:
            st.error("Some columns required for student data view are missing.")
            st.table(pd.DataFrame(missing_columns, columns=["Missing Columns"]))
            return
        
        filtered_data = filtered_data[student_columns]
        filtered_data["hr"] = filtered_data["hr"].round(2)

        total_hours = filtered_data["hr"].sum()
        st.write(f"**Total Hours of Classes:** {total_hours:.2f}")
        subject_hours = filtered_data.groupby("subject")["hr"].sum()
        st.write("**Subject-wise Hours:**")
        st.write(subject_hours)  
        st.write(filtered_data)

    elif role == "Teacher":
        # Check for missing columns
        missing_columns = [col for col in teacher_columns if col not in filtered_data.columns]
        if missing_columns:
            st.error("Some columns required for teacher data view are missing.")
            st.table(pd.DataFrame(missing_columns, columns=["Missing Columns"]))
            return
        
        filtered_data = filtered_data[teacher_columns]
        filtered_data["hr"] = filtered_data["hr"].round(2)
        
        st.subheader("Daily Class Data")
        st.write(filtered_data)  

        # Calculate salary
        filtered_data['salary'] = filtered_data.apply(calculate_salary, axis=1)
        total_salary = filtered_data['salary'].sum()
        total_hours = filtered_data["hr"].sum()
        st.write(f"**Total Hours:** {total_hours:.2f}")
        st.write(f"**Total Salary (_It is based on rough calculations and may change as a result._):** ₹{total_salary:.2f}")

        # Salary breakdown
        salary_split = filtered_data.groupby(['class', 'syllabus', 'type of class']).agg({
            'hr': 'sum', 'salary': 'sum'
        }).reset_index()
        st.subheader("Salary Breakdown by Class and Board")
        st.write(salary_split)

# Main function to handle user role selection and page display
def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=170)
    st.title("Angle Belearn: Your Daily Class Insights")

    role = st.sidebar.radio("Select your role:", ["Select", "Student", "Teacher"], index=0)

    if st.sidebar.button("Refresh Data"):
        st.session_state.data = get_merged_data_with_em()
    
    if "data" not in st.session_state:
        st.session_state.data = get_merged_data_with_em()

    if role != "Select":
        manage_data(st.session_state.data, role)
    else:
        st.info("Please select a role from the sidebar.")

def manage_data(data, role):
    st.subheader(f"{role} Data")

    # Select month from 'mm' column
    if 'mm' in data.columns:
        month = st.sidebar.selectbox("Select Month", sorted(data["mm"].dropna().unique()))
    else:
        st.error("The 'mm' column is missing from the data, and month selection is unavailable.")
        return

    if role == "Student":
        with st.expander("Student Verification", expanded=True):
            student_id = st.text_input("Enter Student ID").strip().lower()
            student_name_part = st.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

            if st.button("Verify Student"):
                filtered_data = data[(data["mm"] == month) & 
                                     (data["student id"].str.lower().str.strip() == student_id) & 
                                     (data["student"].str.lower().str.contains(student_name_part))]
                
                if not filtered_data.empty:
                    show_filtered_data(filtered_data, role)
                else:
                    st.error("Verification failed. Please check your details.")

    elif role == "Teacher":
        with st.expander("Teacher Verification", expanded=True):
            teacher_id = st.text_input("Enter Teacher ID").strip().lower()
            teacher_name_part = st.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

            if st.button("Verify Teacher"):
                filtered_data = data[(data["mm"] == month) & 
                                     (data["teachers id"].str.lower().str.strip() == teacher_id) & 
                                     (data["teachers name"].str.lower().str.contains(teacher_name_part))]
                
                if not filtered_data.empty:
                    teacher_name = filtered_data["teachers name"].iloc[0]
                    welcome_teacher(teacher_name)
                    show_filtered_data(filtered_data, role)
                    show_student_em_table(data, teacher_name)
                else:
                    st.error("Verification failed. Please check your details.")

if __name__ == "__main__":
    main()
