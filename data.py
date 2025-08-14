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

def get_teacher_profile(teacher_id, profile_df):
    profile_df['Teacher id'] = profile_df['Teacher id'].str.strip().str.lower()
    profile_row = profile_df[profile_df['Teacher id'] == teacher_id]
    return profile_row
def get_supaleran_demofit(teacher_id, supa_demofit_df):
    # Clean Teacher ID column
    supa_demofit_df['Teacher id'] = supa_demofit_df['Teacher id'].astype(str).str.strip().str.lower()
    teacher_id = str(teacher_id).strip().lower()

    # Filter row for given teacher
    row = supa_demofit_df[supa_demofit_df['Teacher id'] == teacher_id]

    if not row.empty:
        supalearn_id = row['SupalearnID'].iloc[0] if 'SupalearnID' in row.columns else None
        demofit = row['DemoFit'].iloc[0] if 'DemoFit' in row.columns else None
        return supalearn_id, demofit
    else:
        return None, None
    
def get_teacher_details(teacher_id, supa_demofit_df):
    # Normalize for matching
    supa_demofit_df['Teacher id'] = supa_demofit_df['Teacher id'].str.strip().str.lower()
    teacher_id = teacher_id.strip().lower()
    
    row = supa_demofit_df[supa_demofit_df['Teacher id'] == teacher_id]
    if not row.empty:
        teacher_name = row.iloc[0]['Teacher Name']
        supalearn_id = row.iloc[0]['SupalearnID']
        demofit = row.iloc[0]['DemoFit']
        return teacher_name, supalearn_id, demofit
    else:
        return None, None, None


def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=250)
    st.title("Angle Belearn - Teacher Dashboard")

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    sheet_id = "1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4"
    class_df = fetch_data(sheet_id, "Student class details")
    student_df = fetch_data(sheet_id, "Student Data")
    profile_df = fetch_data(sheet_id, "Profile")
    supa_demofit_df = fetch_data(sheet_id, "ForSupalearnID")

    st.subheader("🔐 Login")
    teacher_id = st.text_input("Enter Your Teacher ID").strip().lower()
    teacher_pass = st.text_input("Enter last 4 digits of your phone number")
    month = st.selectbox("Pick Month", list(range(4, 13)))
    month_str = f"{month:02}"

    if st.button("Login"):
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

        # Save to session_state
        st.session_state.teacher_name = filtered['Teachers Name'].iloc[0].title()
        st.session_state.teacher_id = teacher_id
        st.session_state.filtered_data = filtered
        st.session_state.merged_data = merge_teacher_student(filtered, student_df)
        st.session_state.profile_data = get_teacher_profile(teacher_id, profile_df)

        # Supalearn + DemoFit
        supalearn_id, demofit = get_supaleran_demofit(teacher_id, supa_demofit_df)
        st.session_state.supalearn_id = supalearn_id
        st.session_state.demofit = demofit
        st.rerun()

    # After successful login
    if "teacher_name" in st.session_state:
        # Welcome block BEFORE tabs
        st.success(f"Welcome, {st.session_state.teacher_name}! 🎉")
        st.info(f"**Supalearn ID:** {st.session_state.supalearn_id if st.session_state.supalearn_id else 'Not Found'}")
        st.info(f"**Class Quality:** {st.session_state.demofit if st.session_state.demofit else 'Not Found'}")

        tab1, tab2, tab3 = st.tabs(["👩‍🏫 Profile", "📖 Daily Class Data", "👥 Student Details"])

        with tab1:
            st.subheader("👩‍🏫 Teacher Profile")
            profile_data = st.session_state.profile_data
            if not profile_data.empty:
                st.write(f"**Phone:** {profile_data['Phone number'].values[0]}")
                st.write(f"**Email:** {profile_data['Mail. id'].values[0]}")
                st.write(f"**Qualification:** {profile_data['Qualification'].values[0]}")
                st.write(f"**Available Slots:** {profile_data['Available Slots'].values[0]}")

                lang_col = 'Language preferred  in Class'
                if lang_col in profile_data.columns:
                    st.write(f"**Language Preference:** {profile_data[lang_col].values[0]}")

                syllabus_columns = ["IGCSE", "CBSE", "ICSE"]
                syllabus = [col for col in syllabus_columns if col in profile_data.columns and str(profile_data[col].values[0]).strip().upper() == "YES"]
                st.write("**Syllabus Expertise:** " + ", ".join(syllabus) if syllabus else "No syllabus marked.")

                subjects = profile_data.iloc[0, 12:35]
                subjects = subjects[subjects != '']
                if not subjects.empty:
                    st.write("**Subjects Handled**")
                    for subject, level in subjects.items():
                        st.markdown(f"- **{subject}** : Upto {level}th")
                else:
                    st.write("No subjects listed.")

        with tab2:
            st.subheader("📖 Daily Class Log")
            summary = st.session_state.merged_data[["Date", "Student ID", "Student", "Class", "Syllabus", "Hr", "Type of class"]]
            summary = summary.sort_values(by=["Date", "Student ID"]).reset_index(drop=True)

            st.dataframe(highlight_duplicates(summary), use_container_width=True)
            st.download_button("📥 Download Summary", data=to_csv_download(summary),
                               file_name=f"{st.session_state.teacher_name}_summary.csv", mime="text/csv")

            st.write("## ⏱️ Consolidated Class Hours")
            grouped = summary.groupby(["Class", "Syllabus", "Type of class"]).agg({"Hr": "sum"}).reset_index()
            st.dataframe(grouped, use_container_width=True)

        with tab3:
            st.subheader("👥 Assigned Students & EM Info")
            em_data = st.session_state.merged_data[['Student ID', 'Student', 'EM', 'Phone Number']].drop_duplicates()
            st.dataframe(em_data.sort_values(by="Student"), use_container_width=True)


if __name__ == "__main__":
    main()
