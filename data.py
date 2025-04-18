import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Angle Belearn Insights",
    page_icon="🎓",
    layout="wide"
)

def load_credentials_from_secrets():
    try:
        credentials_info = dict(st.secrets["google_credentials_new_project"])
        return credentials_info
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
        sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
        return sheet
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
            df.columns = df.columns.str.strip()
            df.replace('', np.nan, inplace=True)
            df.fillna('', inplace=True)
            if 'Hr' in df.columns:
                df['Hr'] = pd.to_numeric(df['Hr'], errors='coerce').fillna(0)
            return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
    return pd.DataFrame()

def get_merged_data_with_em():
    main_data = fetch_data_from_sheet("1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4", "Student class details")
    em_data = fetch_data_from_sheet("1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4", "Student Data")

    if main_data.empty or em_data.empty:
        return pd.DataFrame()

    main_data = main_data.rename(columns={'Student id': 'Student ID'})
    em_data = em_data.rename(columns={'Student id': 'Student ID', 'EM': 'EM', 'EM Phone': 'Phone Number'})
    merged_data = main_data.merge(em_data[['Student ID', 'EM', 'Phone Number']], on="Student ID", how="left")
    return merged_data.drop_duplicates()

def get_teacher_password(data, teacher_name):
    teacher_data = data[data['Teachers Name'].str.lower() == teacher_name.lower()]
    if 'Supalearn Password' in teacher_data.columns:
        password_series = teacher_data['Supalearn Password'].dropna()
        if not password_series.empty:
            return password_series.iloc[0]
    return None

def calculate_salary(row, selected_rates):
    student_id = row['Student ID'].strip().lower()
    syllabus = row['Syllabus'].strip().lower()
    class_type = row['Type of class'].strip().lower()
    hours = row['Hr']

    if 'demo class v - x' in student_id:
        return hours * selected_rates.get('demo_v_x', 150)
    elif 'demo class i - iv' in student_id:
        return hours * selected_rates.get('demo_i_iv', 120)
    elif 'demo class xi - xii' in student_id:
        return hours * selected_rates.get('demo_xi_xii', 180)
    elif class_type.startswith("paid"):
        return hours * 4 * 100
    else:
        class_level = int(row['Class']) if str(row['Class']).isdigit() else None
        if syllabus in ['igcse', 'ib']:
            if class_level is not None:
                if 1 <= class_level <= 4:
                    return hours * selected_rates.get('other_1_4', 120)
                elif 5 <= class_level <= 7:
                    return hours * selected_rates.get('other_5_10', 150)
                elif 8 <= class_level <= 10:
                    return hours * selected_rates.get('other_5_10', 150)
                elif 11 <= class_level <= 13:
                    return hours * selected_rates.get('other_11_12', 180)
        else:
            if class_level is not None:
                if 1 <= class_level <= 4:
                    return hours * selected_rates.get('other_1_4', 120)
                elif 5 <= class_level <= 10:
                    return hours * selected_rates.get('other_5_10', 150)
                elif 11 <= class_level <= 12:
                    return hours * selected_rates.get('other_11_12', 180)
    return 0



def highlight_duplicates(df):
    # Find duplicate rows based on 'Date' and 'Student ID'
    duplicates = df[df.duplicated(subset=["Date", "Student ID"], keep=False)]
    
    # Apply background-color: lightcoral to highlight duplicates
    def apply_style(row):
        return ['background-color: lightcoral' if row.name in duplicates.index else '' for _ in row]

    return df.style.apply(apply_style, axis=1)

def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=250)
    st.title("Teacher-Class Daily Logbook")

    if st.sidebar.button("Refresh Data"):
        st.session_state.data = get_merged_data_with_em()
        st.success("Data refreshed!")

    if "data" not in st.session_state:
        st.session_state.data = get_merged_data_with_em()

    role = st.sidebar.radio("Select your role:", ["Select", "Student", "Teacher"], index=0)

    if role == "Teacher":
        data = st.session_state.data
        if "logged_in" not in st.session_state:
            st.session_state.logged_in = False

        if not st.session_state.logged_in:
            st.subheader("Teacher Login")
            teacher_id = st.text_input("Enter Your Teacher ID").strip().lower()
            teacher_name_part = st.text_input("Enter part of your name").strip().lower()

            if st.button("Verify Teacher"):
                filtered = data[(data['Teachers ID'].str.lower().str.strip() == teacher_id) & 
                                 (data['Teachers Name'].str.lower().str.contains(teacher_name_part))]
                if not filtered.empty:
                    st.session_state.logged_in = True
                    st.session_state.teacher_name = filtered['Teachers Name'].iloc[0]
                    st.session_state.filtered_data = filtered
                else:
                    st.error("Verification failed. Please check your Teacher ID and Name.")

        if st.session_state.logged_in:
            teacher_name = st.session_state.teacher_name
            filtered = st.session_state.filtered_data
            st.subheader(f"Welcome, {teacher_name}!")

            password = get_teacher_password(filtered, teacher_name)
            st.write(f"Your Supalearn UserID is: **{password}**" if password else "Supalearn Password not found.")

            # Avoid converting Date to datetime; keep it as it is from the Google Sheet
            class_summary = filtered.groupby(["Date", "Student ID", "Student", "Class", "Syllabus", "Type of class"]).agg({"Hr": "sum"}).reset_index()

            # Display Date exactly as it is in the Google Sheet (no date conversion)
            st.dataframe(class_summary)

            total_hours = class_summary['Hr'].sum()
            st.write(f"Total Hours: **{total_hours}**")

            st.markdown("### Input Your Rates:")
            available_rates = {
                'demo_i_iv': 'Demo Class I - IV',
                'demo_v_x': 'Demo Class V - X',
                'demo_xi_xii': 'Demo Class XI - XII',
                'other_1_4': 'Class I - IV (Other)',
                'other_5_10': 'Class V - X (Other)',
                'other_11_12': 'Class XI - XII (Other)',
            }

            selected_rates = {key: st.number_input(f"{value}", value=120 if "Demo" in value else 100) for key, value in available_rates.items()}

            if st.button("Calculate Salary"):
                class_summary['Salary'] = class_summary.apply(lambda row: calculate_salary(row, selected_rates), axis=1)
                total_salary = class_summary['Salary'].sum()

                consolidated_summary = class_summary.groupby(["Class", "Syllabus", "Type of class"]).agg({
                    "Hr": "sum", "Salary": "sum"}).reset_index()

                st.write("## Consolidated Salary Summary")
                st.dataframe(consolidated_summary)
                st.success(f"### Total Salary: ₹ {total_salary:.2f}")

    elif role == "Student":
        st.subheader("Student Login")
        st.info("(Student interface coming soon...)")
    else:
        st.info("Please select a role from the sidebar.")

if __name__ == "__main__":
    main()



