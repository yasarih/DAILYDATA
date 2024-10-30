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

# Function to load credentials from Streamlit secrets for the new project
def load_credentials_from_secrets():
    credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])
    return credentials_info

# Function to connect to Google Sheets using the link and credentials from secrets
def connect_to_google_sheets_by_link(sheet_link, worksheet_name):
    credentials_info = load_credentials_from_secrets()
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ]
    
    credentials = Credentials.from_service_account_info(
        credentials_info,
        scopes=scopes
    )
    
    client = gspread.authorize(credentials)
    sheet = client.open_by_url(sheet_link).worksheet(worksheet_name)
    return sheet

# Function to fetch data from a Google Sheet by link
def fetch_data_from_sheet_by_link(sheet_link, worksheet_name):
    sheet = connect_to_google_sheets_by_link(sheet_link, worksheet_name)
    data = sheet.get_all_values()

    if data and len(data) > 1:
        headers = data[0]
        df = pd.DataFrame(data[1:], columns=headers)
        # Only fill NaNs selectively, not for critical columns like 'Student', 'Student id', etc.
        non_critical_columns = df.columns.difference(['Student id', 'Student', 'Teachers Name'])
        df[non_critical_columns] = df[non_critical_columns].replace('', pd.NA).ffill()
        return df
    else:
        st.warning(f"No data found in worksheet {worksheet_name} or the sheet is incorrectly formatted.")
        return pd.DataFrame()

# Load data from main sheet, EM list sheet, and weekly timetable sheet
def load_all_data():
    main_data = fetch_data_from_sheet_by_link("https://docs.google.com/spreadsheets/d/17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y/edit?gid=148340814#gid=148340814", "Student class details")
    em_data = fetch_data_from_sheet_by_link("https://docs.google.com/spreadsheets/d/17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y/edit?gid=148340814#gid=148340814", "Student Data")
    timetable_data = fetch_data_from_sheet_by_link("https://docs.google.com/spreadsheets/d/1RTJrYtD0Fo4GlLyZ2ds7M_1jnQJPk1cpeAvtsTwttdU/edit?gid=1473623416#gid=1473623416", "Console")
    
    # Save to session state to avoid redundant loading
    st.session_state.main_data = main_data
    st.session_state.em_data = em_data
    st.session_state.timetable_data = timetable_data

# Function to display EM for each student by merging with the main data
def display_em_info(filtered_data, em_data):
    st.write("### Education Managers (EMs) for Each Student")
    merged_data = pd.merge(filtered_data, em_data, on="Student id", how="left")
    em_info = merged_data[['Student id', 'Student', 'EM']].drop_duplicates()
    st.dataframe(em_info)

# Function to filter timetable data by day for the teacher
def filter_by_day(timetable_data, teacher_name, day):
    return timetable_data[(timetable_data['Teacher Name'] == teacher_name) & 
                          (timetable_data['Day'].str.lower() == day.lower())]

# Function to display teacher's weekly timetable by day
def display_weekly_timetable(teacher_name, timetable_data):
    st.write(f"### Weekly Timetable for {teacher_name}")
    
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    for day in days_of_week:
        st.write(f"**{day}**")
        day_schedule = filter_by_day(timetable_data, teacher_name, day)
        
        if day_schedule.empty:
            st.write("No classes scheduled.")
        else:
            st.dataframe(day_schedule)

# Function to safely check and filter data based on column existence
def check_and_filter_columns(df, required_columns):
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.warning(f"Missing columns: {', '.join(missing_columns)}. Data may be incomplete.")
    # Filter only the columns that are present
    return df[[col for col in required_columns if col in df.columns]]

# Function to display filtered data based on the role (Student or Teacher)
def show_filtered_data(filtered_data, role, teacher_name=None):
    if role == "Student":
        required_columns = ["Date", "Subject", "Chapter taken", "Teachers Name", "Hr", "Type of class"]
        filtered_data = check_and_filter_columns(filtered_data, required_columns)
        
        # Display total hours and subject-wise breakdown if data is available
        if "Hr" in filtered_data.columns:
            total_hours = filtered_data["Hr"].sum()
            st.write(f"**Total Hours of Classes:** {total_hours:.2f}")
            if "Subject" in filtered_data.columns:
                subject_hours = filtered_data.groupby("Subject")["Hr"].sum()
                st.write("**Subject-wise Hours:**")
                st.bar_chart(subject_hours)
        st.write(filtered_data)

    elif role == "Teacher":
        required_columns = ["Date", "Student id", "Student", "Class", "Syllabus", "Type of class", "Hr", "Day", "Time"]
        filtered_data = check_and_filter_columns(filtered_data, required_columns)

        st.subheader("Daily Class Data")
        
        # Display EM information for students
        display_em_info(filtered_data, st.session_state.em_data)
        
        # Show teacher's weekly timetable
        if teacher_name:
            display_weekly_timetable(teacher_name, st.session_state.timetable_data)

# Main function to handle user role selection and page display
def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=170)

    st.title("App is Updating")

    # Load data once at the start
    if "main_data" not in st.session_state:
        load_all_data()

    role = st.sidebar.radio("Select your role:", ["Select", "Student", "Teacher"], index=0)

    if role != "Select":
        manage_data(st.session_state.main_data, role)
    else:
        st.info("Please select a role from the sidebar.")

def manage_data(data, role):
    st.subheader(f"{role} Data")

    # Filter by month before verification
    if "MM" in data.columns:
        month = st.sidebar.selectbox("Select Month", sorted(data["MM"].unique()))
    else:
        st.warning("Month column 'MM' is missing in the data.")

    if role == "Student":
        with st.expander("Student Verification", expanded=True):
            student_id = st.text_input("Enter Student ID").strip().lower()
            student_name_part = st.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

            if st.button("Verify Student"):
                if "Student id" in data.columns and "Student" in data.columns:
                    filtered_data = data[(data["MM"] == month) & 
                                         (data["Student id"].str.lower().str.strip() == student_id) & 
                                         (data["Student"].str.lower().str.contains(student_name_part))]
                    
                    if not filtered_data.empty:
                        show_filtered_data(filtered_data, role)
                    else:
                        st.error("Verification failed. Please check your details.")
                else:
                    st.warning("Required columns for Student verification are missing.")

    elif role == "Teacher":
        with st.expander("Teacher Verification", expanded=True):
            teacher_id = st.text_input("Enter Teacher ID").strip().lower()
            teacher_name_part = st.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

            if st.button("Verify Teacher"):
                if "Teachers ID" in data.columns and "Teachers Name" in data.columns:
                    filtered_data = data[(data["MM"] == month) & 
                                         (data["Teachers ID"].str.lower().str.strip() == teacher_id) & 
                                         (data["Teachers Name"].str.lower().str.contains(teacher_name_part))]
                    
                    if not filtered_data.empty:
                        teacher_name = filtered_data["Teachers Name"].iloc[0]  # Get the first matching teacher name
                        st.markdown(f"## 👩‍🏫 Welcome, {teacher_name}!")
                        show_filtered_data(filtered_data, role, teacher_name)
                    else:
                        st.error("Verification failed. Please check your details.")
                else:
                    st.warning("Required columns for Teacher verification are missing.")

if __name__ == "__main__":
    main()
