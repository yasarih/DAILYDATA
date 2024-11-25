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

# Function to load credentials from Streamlit secrets
def load_credentials_from_secrets():
    try:
        credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])
        return credentials_info
    except KeyError:
        st.error("Google credentials not found in Streamlit secrets.")
        return None

# Function to connect to Google Sheets using the credentials
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

# Function to fetch data from a sheet
def fetch_data_from_sheet(spreadsheet_id, worksheet_name):
    sheet = connect_to_google_sheets(spreadsheet_id, worksheet_name)
    if not sheet:
        st.warning(f"Could not establish a connection to the worksheet '{worksheet_name}'.")
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
    main_data = fetch_data_from_sheet("17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y", "Student class details")
    em_data = fetch_data_from_sheet("17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y", "Student Data")
    
    if main_data.empty:
        st.warning("Main data is empty. Please check the 'Student class details' sheet.")
    if em_data.empty:
        st.warning("EM data is empty. Please check the 'Student Data' sheet.")
    if main_data.empty or em_data.empty:
        return pd.DataFrame()

    main_data = main_data.rename(columns={'Student id': 'Student ID'})
    em_data = em_data.rename(columns={'Student id': 'Student ID', 'EM': 'EM','Status':'Status','EM Phone': 'Phone Number'})

    merged_data = main_data.merge(em_data[['Student ID', 'EM','Status','Phone Number']], on="Student ID", how="left")
    return merged_data

# Function to calculate salary
def calculate_salary(row):
    student_id = row['Student ID'].strip().lower()
    syllabus = row['Syllabus'].strip().lower()
    class_type = row['Type of class'].strip().lower()
    hours = row['Hr']

    if 'demo class i - x' in student_id:
        return hours * 150
    elif 'demo class xi - xii' in student_id:
        return hours * 180
    elif class_type.startswith("paid"):
        return hours * 4 * 100
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
    return 0

# Function to display filtered data
def show_filtered_data(filtered_data, role):
    if role == "Teacher":
        filtered_data['Salary'] = filtered_data.apply(calculate_salary, axis=1)
        total_salary = filtered_data['Salary'].sum()
        st.write(f"**Total Salary:** ₹{total_salary:.2f}")

        salary_split = filtered_data.groupby(['Class', 'Syllabus', 'Type of class']).agg({
            'Hr': 'sum', 'Salary': 'sum'
        }).reset_index()
        st.write("Salary Breakdown by Class and Board", salary_split)

# Function to handle data management based on role
def manage_data(data, role):
    if "MM" not in data.columns:
        st.warning("Month data ('MM' column) not found.")
        return

    month = st.sidebar.selectbox("Select Month", sorted(data["MM"].unique()))
    if role == "Teacher":
        teacher_id = st.text_input("Enter Your Teacher ID").strip().lower()
        if st.button("Verify Teacher"):
            filtered_data = data[(data["MM"] == month) &
                                 (data["Teachers ID"].str.lower().str.strip() == teacher_id)]
            if not filtered_data.empty:
                show_filtered_data(filtered_data, role)
            else:
                st.error("Verification failed. Please check your Teacher ID.")
    elif role == "Student":
        student_id = st.text_input("Enter Student ID").strip().lower()
        if st.button("Verify Student"):
            filtered_data = data[(data["MM"] == month) &
                                 (data["Student ID"].str.lower().str.strip() == student_id)]
            if not filtered_data.empty:
                st.write("Student Data", filtered_data)
            else:
                st.error("Verification failed. Please check your Student ID.")

# Main function
def main():
    st.title("Angle Belearn Insights")
    if st.sidebar.button("Refresh Data"):
        st.session_state.data = get_merged_data_with_em()
    if "data" not in st.session_state:
        st.session_state.data = get_merged_data_with_em()
    role = st.sidebar.radio("Select your role:", ["Select", "Student", "Teacher"])
    if role != "Select":
        manage_data(st.session_state.data, role)

if __name__ == "__main__":
    main()
