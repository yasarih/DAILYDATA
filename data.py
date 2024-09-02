import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# Custom CSS for Styling
def add_custom_css():
    st.markdown("""
        <style>
        body {
            background-color: #e0f7fa;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #333333;
            font-family: 'Arial', sans-serif;
        }
        .css-18ni7ap h3 {
            background-color: #4e79a7;
            color: white;
            padding: 10px;
            border-radius: 8px;
        }
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
        .dataframe td {
            background-color: #ffffff;
        }
        .stButton>button {
            color: white;
            background-color: #4e79a7;
            border-radius: 8px;
        }
        </style>
        """, unsafe_allow_html=True)

def load_credentials_from_secrets():
    credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])
    return credentials_info

def connect_to_google_sheets(spreadsheet_name, worksheet_name):
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
    sheet = client.open(spreadsheet_name).worksheet(worksheet_name)
    return sheet

@st.cache_data
def fetch_all_data(spreadsheet_name, worksheet_name):
    sheet = connect_to_google_sheets(spreadsheet_name, worksheet_name)
    data = sheet.get_all_values()

    if data and len(data) > 1:
        df = pd.DataFrame(data[1:], columns=data[0])  # Convert to DataFrame
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        df = df.replace(r'^\s*$', pd.NA, regex=True)
        df = df.fillna(method='ffill')
    else:
        st.warning("No data found or the sheet is incorrectly formatted.")
        df = pd.DataFrame()  # Return an empty DataFrame

    st.write("Fetched data:", df)  # Debugging output
    return df

def manage_data(data, sheet_name, role):
    st.subheader(f"📊 {sheet_name} Data")
    
    if data.empty:
        st.error("Data is empty, please check your Google Sheets data.")
        return

    if 'selected_month' not in st.session_state:
        st.session_state.selected_month = None

    if role == "Student":
        st.header("Filter Options for Student")
        student_ids = sorted(data["Student id"].unique())
        selected_student_id = st.sidebar.selectbox("Enter Student ID", student_ids, key='student_id')
        input_name = st.sidebar.text_input("Enter the first four letters of your name", key='student_name_input')
        months = sorted(data["MM"].unique())
        selected_month = st.sidebar.selectbox("Select Month", months, key='month_selection')

        if st.sidebar.button("Verify Student"):
            filtered_data = data[(data["Student id"] == selected_student_id) & (data["MM"] == selected_month)]
            st.write("Filtered data for student:", filtered_data)  # Debugging output

            if not filtered_data.empty:
                actual_name = filtered_data["Student"].values[0]
                if input_name.lower() == actual_name[:4].lower():
                    st.session_state.logged_in = True
                    st.session_state.role = role
                    st.session_state.filtered_data = filtered_data
                else:
                    st.error("Name does not match. Please check your input.")
            else:
                st.error("No data found for the selected Student ID and Month.")

    elif role == "Teacher":
        st.header("Filter Options for Teacher")
        teacher_ids = sorted(data["Teachers ID"].unique())
        selected_teacher_id = st.sidebar.selectbox("Enter Teacher ID", teacher_ids, key='teacher_id')
        input_name = st.sidebar.text_input("Enter the first four letters of your name", key='teacher_name_input')
        months = sorted(data["MM"].unique())
        selected_month = st.sidebar.selectbox("Select Month", months, key='month_selection_teacher')

        if st.sidebar.button("Verify Teacher"):
            filtered_data = data[(data["Teachers ID"] == selected_teacher_id) & (data["MM"] == selected_month)]
            st.write("Filtered data for teacher:", filtered_data)  # Debugging output

            if not filtered_data.empty:
                actual_name = filtered_data["Teachers Name"].values[0]
                if input_name.lower() == actual_name[:4].lower():
                    st.session_state.logged_in = True
                    st.session_state.role = role
                    st.session_state.filtered_data = filtered_data
                else:
                    st.error("Name does not match. Please check your input.")
            else:
                st.error("No data found for the selected Teacher ID and Month.")

    if 'logged_in' in st.session_state and st.session_state.logged_in and st.session_state.role == role:
        show_filtered_data(st.session_state.filtered_data, role)

def show_filtered_data(filtered_data, role):
    if filtered_data.empty:
        st.error("Filtered data is empty.")
        return

    filtered_data.insert(0, range(1, len(filtered_data) + 1))

    if role == "Student":
        filtered_data = filtered_data[[ "Date", "Subject", "Teachers Name", "Hr", "Type of class"]]
        filtered_data["Hr"] = pd.to_numeric(filtered_data["Hr"], errors='coerce').round(2)
        st.write(filtered_data.to_html(index=False), unsafe_allow_html=True)

        total_hours = filtered_data["Hr"].sum()
        st.write(f"**Total Hours**: {total_hours:.2f}")
        subject_hours = filtered_data.groupby("Subject")["Hr"].sum()
        st.write("**Total Hours per Subject:**")
        st.write(subject_hours)

    elif role == "Teacher":
        filtered_data = filtered_data[[ "Date", "Student id", "Student", "Hr", "Type of class"]]
        filtered_data["Hr"] = pd.to_numeric(filtered_data["Hr"], errors='coerce').round(2)
        filtered_data['is_duplicate'] = filtered_data.duplicated(subset=['Date', 'Student id'], keep=False)

        def highlight_duplicates(row):
            return ['background-color: red' if row.is_duplicate else '' for _ in row]

        styled_data = filtered_data.style.apply(highlight_duplicates, axis=1)
        st.write(styled_data.to_html(index=False), unsafe_allow_html=True)

        total_hours = filtered_data["Hr"].sum()
        st.write(f"**Total Hours**: {total_hours:.2f}")
        student_hours = filtered_data.groupby("Student")["Hr"].sum()
        st.write("**Total Hours per Student:**")
        st.write(student_hours)

def main():
    add_custom_css()
    st.title("📘 Angle Belearn: Your Daily Class Insights")

    spreadsheet_name = 'Student Daily Class Details 2024'
    worksheet_name = 'Student class details'

    data = fetch_all_data(spreadsheet_name, worksheet_name)

    if data.empty:
        st.error("No data available or failed to fetch data from Google Sheets.")
        return

    role = st.selectbox("Select your role:", ["Select", "Student", "Teacher"])

    if role == "Student":
        student_page(data)
    elif role == "Teacher":
        teacher_page(data)
    else:
        st.write("Please select a role from the options above.")

def student_page(data):
    st.title("🎓 Student Page")
    manage_data(data, 'Student Daily Data', role="Student")

def teacher_page(data):
    st.title("👩‍🏫 Teacher Page")
    manage_data(data, 'Teacher Daily Data', role="Teacher")

if __name__ == "__main__":
    main()
