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
        credentials_info = dict(st.secrets["google_credentials_new_project"])
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
        return pd.DataFrame()
    try:
        data = sheet.get_all_values()
        if data:
            headers = pd.Series(data[0]).fillna('').str.strip()
            headers = headers.where(headers != '', other='Unnamed')
            headers = headers + headers.groupby(headers).cumcount().astype(str).replace('0', '')
            df = pd.DataFrame(data[1:], columns=headers)
            df.columns = df.columns.str.strip()
            df.replace('', np.nan, inplace=True)
            df.fillna('', inplace=True)
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

# Function to merge student and EM data without Supalearn Password in student table
def get_merged_data_with_em():
    main_data = fetch_data_from_sheet("1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4", "Student class details")
    em_data = fetch_data_from_sheet("1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4", "Student Data")

    if main_data.empty or em_data.empty:
        st.warning("Main or EM data is empty. Please check the sheets.")
        return pd.DataFrame()

    main_data = main_data.rename(columns={'Student id': 'Student ID'})
    em_data = em_data.rename(columns={'Student id': 'Student ID', 'EM': 'EM', 'EM Phone': 'Phone Number'})

    merged_data = main_data.merge(em_data[['Student ID', 'EM', 'Phone Number']], on="Student ID", how="left")
    merged_data = merged_data.drop_duplicates()

    return merged_data

# Function to fetch Supalearn Password for welcome message
def get_teacher_password(data, teacher_name):
    teacher_data = data[data['Teachers Name'].str.lower() == teacher_name.lower()]
    if 'Supalearn Password' in teacher_data.columns:
        password_series = teacher_data['Supalearn Password'].dropna()
        if not password_series.empty:
            return password_series.iloc[0]
    return None

st.subheader("💰 Salary Calculator")

# Step 1: Take all rates as input
st.markdown("### Input Your Rates:")

paid_class_rate = st.number_input("Rate per Paid Class (default 100)", value=100)

demo_i_x_rate = st.number_input("Rate for Demo Class I - X", value=150)
demo_xi_xii_rate = st.number_input("Rate for Demo Class XI - XII", value=180)

st.markdown("#### Rates for IB / IGCSE Classes:")
ib_1_4 = st.number_input("Class 1-4 Rate (IB/IGCSE)", value=120)
ib_5_7 = st.number_input("Class 5-7 Rate (IB/IGCSE)", value=150)
ib_8_10 = st.number_input("Class 8-10 Rate (IB/IGCSE)", value=170)
ib_11_13 = st.number_input("Class 11-13 Rate (IB/IGCSE)", value=200)

st.markdown("#### Rates for Other Syllabus Classes:")
other_1_4 = st.number_input("Class 1-4 Rate (Other)", value=120)
other_5_10 = st.number_input("Class 5-10 Rate (Other)", value=150)
other_11_12 = st.number_input("Class 11-12 Rate (Other)", value=180)

# Step 2: Define salary calculation function using inputs
def calculate_salary(row):
    student_id = row['Student ID'].strip().lower()
    syllabus = row['Syllabus'].strip().lower()
    class_type = row['Type of class'].strip().lower()
    hours = row['Hr']

    if 'demo class i - x' in student_id:
        return hours * demo_i_x_rate
    elif 'demo class xi - xii' in student_id:
        return hours * demo_xi_xii_rate
    elif class_type.startswith("paid"):
        return hours * 4 * paid_class_rate
    else:
        class_level = int(row['Class']) if row['Class'].isdigit() else None
        if class_level is None:
            return 0

        if syllabus in ['igcse', 'ib']:
            if 1 <= class_level <= 4:
                return hours * ib_1_4
            elif 5 <= class_level <= 7:
                return hours * ib_5_7
            elif 8 <= class_level <= 10:
                return hours * ib_8_10
            elif 11 <= class_level <= 13:
                return hours * ib_11_13
        else:
            if 1 <= class_level <= 4:
                return hours * other_1_4
            elif 5 <= class_level <= 10:
                return hours * other_5_10
            elif 11 <= class_level <= 12:
                return hours * other_11_12

    return 0

# Step 3: Apply the function
class_summary["Salary"] = class_summary.apply(calculate_salary, axis=1)

# Step 4: Show results
total_salary = class_summary["Salary"].sum()

st.write("## Salary Summary")
st.dataframe(class_summary[["Date", "Student", "Class", "Syllabus", "Type of class", "Hr", "Salary"]])
st.write(f"### Total Salary: **₹ {total_salary}**")


# MAIN APP STARTS HERE
def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=250)
    st.title("Teacher-Class Daily Logbook")

    if st.sidebar.button("Refresh Data"):
        st.session_state.data = get_merged_data_with_em()
        st.success("Data refreshed successfully!")

    if "data" not in st.session_state:
        st.session_state.data = get_merged_data_with_em()

    role = st.sidebar.radio("Select your role:", ["Select", "Student", "Teacher"], index=0)

    if role == "Teacher":
        data = st.session_state.data
        st.subheader("Teacher Login")
        teacher_id = st.text_input("Enter Your Teacher ID").strip().lower()
        teacher_name_part = st.text_input("Enter part of your name").strip().lower()

        if st.button("Verify Teacher"):
            filtered = data[(data['Teachers ID'].str.lower().str.strip() == teacher_id) &
                            (data['Teachers Name'].str.lower().str.contains(teacher_name_part))]
            if not filtered.empty:
                teacher_name = filtered['Teachers Name'].iloc[0]
                password = get_teacher_password(filtered, teacher_name)
                st.subheader(f"Welcome, {teacher_name}!")
                if password:
                    st.write(f"Your Supalearn UserID is: **{password}**")
                else:
                    st.write("Supalearn Password not found.")

                st.write("Class Summary")
                class_summary = filtered.groupby(["Date", "Student ID", "Student", "Class", "Syllabus", "Type of class"]).agg({"Hr": "sum"}).reset_index()
                st.dataframe(class_summary)

                total_hours = class_summary['Hr'].sum()
                st.write(f"Total Hours: **{total_hours}**")
            else:
                st.error("Verification failed. Please check your Teacher ID and Name.")

    elif role == "Student":
        st.subheader("Student Login")
        st.write("(Student interface coming soon...)")

    else:
        st.info("Please select a role from the sidebar.")

if __name__ == "__main__":
    main()
