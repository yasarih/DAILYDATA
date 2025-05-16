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
    return merged_data

def get_teacher_password(data, teacher_name):
    if 'Teachers Name' not in data.columns:
        return None
    teacher_data = data[data['Teachers Name'].str.lower() == teacher_name.lower()]
    if 'Supalearn Password' in teacher_data.columns:
        password_series = teacher_data['Supalearn Password'].dropna()
        if not password_series.empty:
            return password_series.iloc[0]
    return None

def highlight_duplicates(df):
    duplicates = df[df.duplicated(subset=["Date", "Student ID"], keep=False)]
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
        if "logged_in" not in st.session_state:
            st.session_state.logged_in = False

        if not st.session_state.logged_in:
            st.subheader("Teacher Login")
            teacher_id = st.text_input("Enter Your Teacher ID").strip().lower()
            teacher_pass = st.text_input("Enter last 4 digits of your phone number")
            month = st.selectbox("Pick Month ", list(range(4, 13)))
            month_str = f"{month:02}"

            if st.button("Verify Teacher"):
                data = st.session_state.data

                required_cols = ['Teachers ID', 'Password', 'MM']
                missing = [col for col in required_cols if col not in data.columns]
                if missing:
                    st.error(f"Missing required columns: {', '.join(missing)}")
                    st.stop()

                filtered = data[
                    (data['Teachers ID'].str.lower() == teacher_id) &
                    (data['Password'] == teacher_pass) &
                    (data['MM'] == month_str)
                ].copy()

                st.write(f"Filtered rows: {len(filtered)}")  # Debug

                if not filtered.empty:
                    st.session_state.logged_in = True
                    st.session_state.teacher_name = filtered['Teachers Name'].iloc[0].title()
                    st.session_state.filtered_data = filtered
                else:
                    st.error("Verification failed. Please double-check your Teacher ID and phone digits. Contact Nihala (8089381416) if needed.")

        if st.session_state.logged_in:
            teacher_name = st.session_state.teacher_name
            filtered = st.session_state.filtered_data
            st.subheader(f"Welcome, {teacher_name}!")

            password = get_teacher_password(filtered, teacher_name)
            st.write(f"Your Supalearn UserID is: **{password}**" if password else "Supalearn Password not found.")

            class_summary = filtered[["Date", "Student ID", "Student", "Class", "Syllabus", "Hr", "Type of class"]]
            class_summary = class_summary.sort_values(by=["Date", "Student ID"]).reset_index(drop=True)

            st.dataframe(highlight_duplicates(class_summary))

            consolidated_summary = class_summary.groupby(["Class", "Syllabus", "Type of class"]).agg({
                "Hr": "sum"
            }).reset_index()

            st.write("## Consolidated Class Summary")
            st.dataframe(consolidated_summary)

            st.write("## Students and EM")
            unique_students = st.session_state.data[
                st.session_state.data['Teachers Name'].str.lower() == teacher_name.lower()
            ][['Student ID', 'Student', 'EM', 'Phone Number']].drop_duplicates().sort_values(by='Student')

            st.dataframe(unique_students)

    elif role == "Student":
        st.subheader("Student Login")
        st.info("(Student interface coming soon...)")
    else:
        st.info("Please select a role from the sidebar.")

if __name__ == "__main__":
    main()
