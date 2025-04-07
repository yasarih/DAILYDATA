# [Updated Full Streamlit App with Salary Calculation, Timetable, and Supalearn Password Display]

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
import json

st.set_page_config(
    page_title="Angle Belearn Insights",
    page_icon="🎓",
    layout="wide",
    menu_items={"Get Help": None, "Report a bug": None, "About": None}
)

def load_credentials_from_secrets():
    try:
        return dict(st.secrets["google_credentials_new_project"])
    except KeyError:
        st.error("Google credentials not found in Streamlit secrets.")
        return None

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
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        client = gspread.authorize(credentials)
        return client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

def fetch_data_from_sheet(spreadsheet_id, worksheet_name):
    sheet = connect_to_google_sheets(spreadsheet_id, worksheet_name)
    if not sheet:
        return pd.DataFrame()
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
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching data from '{worksheet_name}': {e}")
        return pd.DataFrame()

def get_merged_data_with_em():
    main_data = fetch_data_from_sheet("1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4", "Student class details")
    em_data = fetch_data_from_sheet("1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4", "Student Data")
    if main_data.empty or em_data.empty:
        return pd.DataFrame()

    main_data = main_data.rename(columns={'Student id': 'Student ID'})
    em_data = em_data.rename(columns={'Student id': 'Student ID', 'EM': 'EM', 'EM Phone': 'Phone Number'})
    merged_data = main_data.merge(em_data[['Student ID', 'EM', 'Phone Number']], on="Student ID", how="left")
    merged_data = merged_data.merge(main_data[['Student ID', 'Supalearn Password']], on="Student ID", how="left")
    return merged_data

def calculate_salary(row):
    student_id = row['Student ID'].strip().lower()
    syllabus = row['Syllabus'].strip().lower()
    class_type = row['Type of class'].strip().lower()
    hours = row['Hr']
    try:
        level = int(row['Class']) if row['Class'].isdigit() else None
    except:
        level = None

    if 'demo class i - x' in student_id:
        return hours * 150
    elif 'demo class xi - xii' in student_id:
        return hours * 180
    elif class_type.startswith("paid"):
        return hours * 4 * 100
    elif syllabus in ['igcse', 'ib']:
        if level and 1 <= level <= 4:
            return hours * 120
        elif level and 5 <= level <= 7:
            return hours * 150
        elif level and 8 <= level <= 10:
            return hours * 170
        elif level and 11 <= level <= 13:
            return hours * 200
    else:
        if level and 1 <= level <= 4:
            return hours * 120
        elif level and 5 <= level <= 10:
            return hours * 150
        elif level and 11 <= level <= 12:
            return hours * 180
    return 0

def show_teacher_schedule(teacher_id):
    st.subheader("Your Weekly Schedule")
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    schedule_data = pd.DataFrame()

    for day in days:
        day_data = fetch_data_from_sheet("1RTJrYtD0Fo4GlLyZ2ds7M_1jnQJPk1cpeAvtsTwttdU", day)
        if not day_data.empty and {"Teacher ID", "Time Slot", "Student ID", "Status"}.issubset(day_data.columns):
            day_data = day_data[(day_data['Teacher ID'].str.lower().str.strip() == teacher_id) & (day_data['Status'].str.lower() == 'active')]
            day_data['Day'] = day
            schedule_data = pd.concat([schedule_data, day_data], ignore_index=True)

    if not schedule_data.empty:
        pivoted = schedule_data.groupby(['Time Slot', 'Day'])['Student ID'].apply(lambda x: ', '.join(x)).reset_index()
        schedule_pivot = pivoted.pivot(index="Time Slot", columns="Day", values="Student ID").reindex(columns=days)
        st.write(schedule_pivot)
    else:
        st.info("No active schedule found for this teacher.")

def manage_data(data, role):
    st.subheader(f"{role} Data")

    matched_mm = [col for col in data.columns if col.strip().upper() == "MM"]
    if not matched_mm:
        st.warning("Month data ('MM' column) not found. Available columns are:")
        st.write(data.columns.tolist())
        return

    month_col = matched_mm[0]
    month = st.sidebar.selectbox("Select Month", sorted(data[month_col].unique()))
    year = st.sidebar.selectbox("Select Year", sorted(data["Year"].unique()))

    if role == "Teacher":
        teacher_id = st.text_input("Enter Your Teacher ID").strip().lower()
        teacher_name_part = st.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

        if st.button("Verify Teacher"):
            filtered_data = data[
                (data[month_col] == month) &
                (data["Year"] == year) &
                (data["Teachers ID"].str.lower().str.strip() == teacher_id) &
                (data["Teachers Name"].str.lower().str.contains(teacher_name_part))
            ]
            if not filtered_data.empty:
                teacher_name = filtered_data["Teachers Name"].iloc[0]
                st.subheader(f"👩‍🏫 Welcome, {teacher_name}!")
                st.write(f"Supalearn Password: **{filtered_data['Supalearn Password'].iloc[0]}**")
                st.subheader("📊 Salary Breakdown")
                filtered_data['Salary'] = filtered_data.apply(calculate_salary, axis=1)
                st.write(filtered_data[["Date", "Student", "Class", "Syllabus", "Type of class", "Hr", "Salary"]])
                st.write(f"**Total Salary:** ₹{filtered_data['Salary'].sum():,.2f}")
                show_teacher_schedule(teacher_id)
            else:
                st.error("Verification failed. Please check your Teacher ID and name.")

    elif role == "Student":
        student_id = st.text_input("Enter Student ID").strip().lower()
        student_name_part = st.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

        if st.button("Verify Student"):
            filtered_data = data[
                (data[month_col] == month) &
                (data["Student ID"].str.lower().str.strip() == student_id) &
                (data["Student"].str.lower().str.contains(student_name_part))
            ]
            if not filtered_data.empty:
                student_name = filtered_data["Student"].iloc[0]
                st.subheader(f"👨‍🎓 Welcome, {student_name}!")
                st.write(filtered_data[["Date", "Subject", "Hr", "Teachers Name", "Chapter taken", "Type of class"]])
                st.write(f"**Total Hours:** {filtered_data['Hr'].sum():.2f}")
            else:
                st.error("Verification failed. Please check your details.")

def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=250)
    st.title("Angle Belearn: Your Daily Class Insights")

    if st.sidebar.button("Refresh Data"):
        st.session_state.data = get_merged_data_with_em()
        st.success("Data refreshed successfully!")

    if "data" not in st.session_state:
        st.session_state.data = get_merged_data_with_em()

    role = st.sidebar.radio("Select your role:", ["Select", "Student", "Teacher"], index=0)
    if role != "Select":
        manage_data(st.session_state.data, role)
    else:
        st.info("Please select a role from the sidebar.")

if __name__ == "__main__":
    main()
