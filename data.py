import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np

st.set_page_config(page_title="Angle Belearn Insights", page_icon="🎓", layout="wide")

@st.cache_data(show_spinner=False)
def load_credentials():
    try:
        return dict(st.secrets["google_credentials_new_project"])
    except KeyError:
        st.error("Google credentials not found in Streamlit secrets.")
        return None

@st.cache_data(show_spinner=True)
def fetch_data(sheet_id, worksheet):
    creds_info = load_credentials()
    if not creds_info:
        return pd.DataFrame()
    
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        client = gspread.authorize(creds)
        ws = client.open_by_key(sheet_id).worksheet(worksheet)
        data = ws.get_all_values()
        if not data:
            return pd.DataFrame()

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
        st.error(f"Error loading sheet: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner=True)
def merge_teacher_student(main_df, student_df):
    if main_df.empty or student_df.empty:
        return pd.DataFrame()
    
    main_df = main_df.rename(columns={'Student id': 'Student ID'})
    student_df = student_df.rename(columns={'Student id': 'Student ID', 'EM': 'EM', 'EM Phone': 'Phone Number'})
    try:
        merged = main_df.merge(student_df[['Student ID', 'EM', 'Phone Number']], on='Student ID', how='left')
        return merged
    except Exception as e:
        st.error(f"Error during merging: {e}")
        return main_df

def highlight_duplicates(df):
    dupes = df[df.duplicated(subset=["Date", "Student ID"], keep=False)]
    return df.style.apply(
        lambda row: ['background-color: lightcoral' if row.name in dupes.index else '' for _ in row],
        axis=1
    )

def to_csv_download(df, filename="teacher_log.csv"):
    return df.to_csv(index=False).encode("utf-8")

def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=250)
    st.title("Teacher-Class Daily Logbook")


     # 🔁 Refresh button
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.success("Data refreshed successfully. Please proceed.")
        st.experimental_rerun()

    


    

    sheet_id = "1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4"
    class_df = fetch_data(sheet_id, "Student class details")
    student_df = fetch_data(sheet_id, "Student Data")

    role = st.sidebar.radio("Select your role:", ["Select", "Student", "Teacher"], index=0)

    if role == "Teacher":
        st.subheader("Teacher Login")
        teacher_id = st.text_input("Enter Your Teacher ID").strip().lower()
        teacher_pass = st.text_input("Enter last 4 digits of your phone number")
        month = st.selectbox("Pick Month", list(range(4, 13)))
        month_str = f"{month:02}"

        if st.button("Verify Teacher"):
            if class_df.empty:
                st.error("Class data not available.")
                return

            df = class_df.copy()
            df['Teachers ID'] = df['Teachers ID'].str.strip().str.lower()
            df['Password'] = df['Password'].astype(str).str.strip()
            df['MM'] = df['MM'].astype(str).str.zfill(2)

            filtered = df[
                (df['Teachers ID'] == teacher_id) &
                (df['Password'] == teacher_pass) &
                (df['MM'] == month_str)
            ]

            if filtered.empty:
                st.error("Invalid credentials or no data for this month.")
                return

            teacher_name = filtered['Teachers Name'].iloc[0].title()
            st.session_state.teacher_name = teacher_name

            merged_data = merge_teacher_student(filtered, student_df)
            st.success(f"Welcome, {teacher_name}!")
            st.write(f"Your Supalearn UserID: **{filtered['Supalearn Password'].iloc[0]}**")

            summary = merged_data[["Date", "Student ID", "Student", "Class", "Syllabus", "Hr", "Type of class"]]
            summary = summary.sort_values(by=["Date", "Student ID"]).reset_index(drop=True)

            st.dataframe(highlight_duplicates(summary), use_container_width=True)

            st.download_button("📥 Download Class Summary", data=to_csv_download(summary),
                               file_name=f"{teacher_name}_summary.csv", mime="text/csv")

            st.write("## Consolidated Summary")
            group = summary.groupby(["Class", "Syllabus", "Type of class"]).agg({"Hr": "sum"}).reset_index()
            st.dataframe(group, use_container_width=True)

            st.write("## Student + EM Info")
            em_part = merged_data[['Student ID', 'Student', 'EM', 'Phone Number']].drop_duplicates()
            st.dataframe(em_part.sort_values(by="Student"), use_container_width=True)

    elif role == "Student":
        st.subheader("Student Login")
        st.info("(Student interface coming soon...)")
    else:
        st.info("Please select a role from the sidebar.")

if __name__ == "__main__":
    main()
