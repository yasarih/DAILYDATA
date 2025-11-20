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

        headers = pd.Series(data[0]).fillna('').astype(str).str.strip()
        headers = headers.where(headers != '', other='Unnamed')
        headers = headers + headers.groupby(headers).cumcount().astype(str).replace('0', '')
        df = pd.DataFrame(data[1:], columns=headers)
        df.columns = df.columns.str.strip()
        df.replace('', np.nan, inplace=True)
        df.fillna('', inplace=True)

        # normalize an Hr column if present
        if 'Hr' in df.columns:
            df['Hr'] = pd.to_numeric(df['Hr'], errors='coerce').fillna(0)

        return df

    except Exception as e:
        st.error(f"Error loading sheet: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner=True)
def merge_teacher_student(main_df, student_df):
    if main_df is None or student_df is None or main_df.empty or student_df.empty:
        return pd.DataFrame()
    
    # rename if present (case sensitive in sheet); handle both possibilities
    main_df = main_df.copy()
    student_df = student_df.copy()

    if 'Student id' in main_df.columns and 'Student ID' not in main_df.columns:
        main_df = main_df.rename(columns={'Student id': 'Student ID'})
    if 'Student id' in student_df.columns and 'Student ID' not in student_df.columns:
        student_df = student_df.rename(columns={'Student id': 'Student ID'})

    # ensure student_df has at least Student ID column
    if 'Student ID' not in student_df.columns:
        return main_df  # can't merge - return original

    # make sure columns exist before merging
    merge_cols = ['Student ID']
    if 'EM' in student_df.columns:
        merge_cols.append('EM')
    if 'EM Phone' in student_df.columns and 'Phone Number' not in student_df.columns:
        student_df = student_df.rename(columns={'EM Phone': 'Phone Number'})
    if 'Phone Number' in student_df.columns:
        merge_cols.append('Phone Number')

    try:
        merged = main_df.merge(student_df[merge_cols], on='Student ID', how='left')
        return merged
    except Exception as e:
        st.error(f"Error during merging: {e}")
        return main_df

def highlight_duplicates(df):
    # Accepts a DataFrame and returns a Styler highlighting duplicates on Date+Student ID
    if df is None or df.empty:
        return df
    dupes = df[df.duplicated(subset=["Date", "Student ID"], keep=False)]
    return df.style.apply(
        lambda row: ['background-color: lightcoral' if row.name in dupes.index else '' for _ in row],
        axis=1
    )

def to_csv_download(df, filename="teacher_log.csv"):
    return df.to_csv(index=False).encode("utf-8")

def get_teacher_profile(teacher_id, profile_df):
    if profile_df is None or profile_df.empty:
        return pd.DataFrame()
    df = profile_df.copy()
    # case-insensitive match for teacher id
    id_col = next((c for c in df.columns if c.strip().lower() == 'teacher id' or c.strip().lower() == 'teacher id'), None)
    if id_col is None:
        # try variants
        id_col = next((c for c in df.columns if 'teacher' in c.lower() and 'id' in c.lower()), None)
    if id_col is None:
        return pd.DataFrame()
    df[id_col] = df[id_col].astype(str).str.strip().str.lower()
    return df[df[id_col] == teacher_id]

def get_teacher_demobonus(teacher_id, demoBonus_df):
    if demoBonus_df is None or demoBonus_df.empty:
        return pd.DataFrame()
    df = demoBonus_df.copy()
    id_col = next((c for c in df.columns if c.strip().lower() == 'teacher id'), None)
    if id_col is None:
        id_col = next((c for c in df.columns if 'teacher' in c.lower() and 'id' in c.lower()), None)
    if id_col is None:
        return pd.DataFrame()
    df[id_col] = df[id_col].astype(str).str.strip().str.lower()
    return df[df[id_col] == teacher_id]

def filter_overlimit_for_teacher(overlimit_df: pd.DataFrame, teacher_id_norm: str) -> pd.DataFrame:
    # work on a copy
    if overlimit_df is None or overlimit_df.empty:
        return pd.DataFrame()

    df = overlimit_df.copy()

    # find teacher column case-insensitively
    teacher_col = next((c for c in df.columns if c.strip().lower() == 'teacher id' or ( 'teacher' in c.lower() and 'id' in c.lower() )), None)

    # normalize and filter if that column exists
    if teacher_col is not None:
        df[teacher_col] = df[teacher_col].astype(str).str.strip().str.lower()
        df = df[df[teacher_col] == teacher_id_norm]

    # select only the columns we want to show to the user (exclude Teacher ID)
    cols = ['EM', 'Student ID', 'Student', 'Chapter Taken', 'Hours Taken', 'Max. Hours Alloted']
    existing = [c for c in cols if c in df.columns]
    if not existing:
        return pd.DataFrame()  # nothing to show
    filtered = df.loc[:, existing].copy()

    # make numeric (coerce invalid -> NaN)
    if 'Hours Taken' in filtered.columns:
        filtered['Hours Taken'] = pd.to_numeric(filtered['Hours Taken'], errors='coerce')
    if 'Max. Hours Alloted' in filtered.columns:
        filtered['Max. Hours Alloted'] = pd.to_numeric(filtered['Max. Hours Alloted'], errors='coerce')

    # compute difference (keep as float so partial hours are preserved)
    # only compute for columns that exist
    if 'Hours Taken' in filtered.columns and 'Max. Hours Alloted' in filtered.columns:
        filtered['Difference'] = filtered['Hours Taken'].sub(filtered['Max. Hours Alloted'])
    else:
        # if one of the columns is missing, create Difference as NaN or as HoursTaken if only that exists
        if 'Hours Taken' in filtered.columns:
            filtered['Difference'] = filtered['Hours Taken']
        else:
            filtered['Difference'] = np.nan

    return filtered

def get_exam_data(teacher_id, examlist_df):
    if examlist_df is None or examlist_df.empty:
        return pd.DataFrame()
    df = examlist_df.copy()
    teacher_col = next((c for c in df.columns if c.strip().lower() == 'teacher id'), None)
    if teacher_col is not None:
        df[teacher_col] = df[teacher_col].astype(str).str.strip().str.lower()
        df = df[df[teacher_col] == teacher_id]
    cols = ['Student ID', 'Name', 'SubJect', 'Chapter name', 'EM']
    existing = [c for c in cols if c in df.columns]
    if not existing:
        return pd.DataFrame()
    return df.loc[:, existing].copy()

def get_supaleran_demofit(teacher_id, supa_demofit_df):
    if supa_demofit_df is None or supa_demofit_df.empty:
        return None, None
    df = supa_demofit_df.copy()
    id_col = next((c for c in df.columns if c.strip().lower() == 'teacher id'), None)
    if id_col is None:
        return None, None
    df[id_col] = df[id_col].astype(str).str.strip().str.lower()
    teacher_id = str(teacher_id).strip().lower()
    row = df[df[id_col] == teacher_id]
    if not row.empty:
        supalearn_id = row['SupalearnID'].iloc[0] if 'SupalearnID' in row.columns else None
        demofit = row['DemoFit'].iloc[0] if 'DemoFit' in row.columns else None
        return supalearn_id, demofit
    else:
        return None, None

def get_teacher_details(teacher_id, supa_demofit_df):
    if supa_demofit_df is None or supa_demofit_df.empty:
        return None, None, None
    df = supa_demofit_df.copy()
    id_col = next((c for c in df.columns if c.strip().lower() == 'teacher id'), None)
    if id_col is None:
        return None, None, None
    df[id_col] = df[id_col].str.strip().str.lower()
    tid = teacher_id.strip().lower()
    row = df[df[id_col] == tid]
    if not row.empty:
        teacher_name = row.iloc[0].get('Teacher Name', None)
        supalearn_id = row.iloc[0].get('SupalearnID', None)
        demofit = row.iloc[0].get('DemoFit', None)
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
    sheet_id2 = "1Edkaa-mlW1Huc6ereT8vu6ZNlusInc998zLHrJYDswk"
    class_df = fetch_data(sheet_id, "Student class details")
    student_df = fetch_data(sheet_id, "Student Data")
    profile_df = fetch_data(sheet_id, "Profile")
    supa_demofit_df = fetch_data(sheet_id, "ForSupalearnID")
    demoBonus_df = fetch_data(sheet_id, "DemoBonus")
    overlimit_df = fetch_data(sheet_id2, "OverlimitCall")
    examlist_df = fetch_data(sheet_id2, "ExamList")

    st.subheader("🔐 Login")
    input_teacher_id = st.text_input("Enter Your Teacher ID").strip().lower()
    teacher_pass = st.text_input("Enter last 4 digits of your phone number")
    month = st.selectbox("Pick Month", list(range(8, 13)))
    month_str = f"{month:02}"

    if st.button("Login"):
        if class_df is None or class_df.empty:
            st.error("Class data not available.")
            return

        df = class_df.copy()
        # normalize relevant columns if present
        if 'Teachers ID' in df.columns:
            df['Teachers ID'] = df['Teachers ID'].astype(str).str.strip().str.lower()
        if 'Password' in df.columns:
            df['Password'] = df['Password'].astype(str).str.strip()
        if 'MM' in df.columns:
            df['MM'] = df['MM'].astype(str).str.zfill(2)

        filtered = df[
            (df.get('Teachers ID', '') == input_teacher_id) &
            (df.get('Password', '') == teacher_pass) &
            (df.get('MM', '') == month_str)
        ]

        if filtered.empty:
            st.error("Invalid credentials or no data for this month.")
            return

        # Save to session_state
        st.session_state.teacher_name = filtered['Teachers Name'].iloc[0].title() if 'Teachers Name' in filtered.columns else input_teacher_id.title()
        st.session_state.teacher_id = input_teacher_id
        st.session_state.filtered_data = filtered.reset_index(drop=True)
        st.session_state.merged_data = merge_teacher_student(st.session_state.filtered_data, student_df)
        st.session_state.profile_data = get_teacher_profile(input_teacher_id, profile_df)

        # Supalearn + DemoFit
        supalearn_id, demofit = get_supaleran_demofit(input_teacher_id, supa_demofit_df)
        st.session_state.supalearn_id = supalearn_id
        st.session_state.demofit = demofit
        # store demo bonus
        st.session_state.demobonus = get_teacher_demobonus(input_teacher_id, demoBonus_df)

        st.rerun()

    # After successful login
    if "teacher_name" in st.session_state:
        st.success(f"Welcome, {st.session_state.teacher_name}! 🎉")
        st.info(f"**Supalearn ID:** {st.session_state.get('supalearn_id', 'Not Found')}")
        st.info(f"**Class Quality:** {st.session_state.get('demofit', 'Not Found')}")

        # get normalized teacher id for filters
        teacher_id_norm = st.session_state.get('teacher_id', '').strip().lower()

        # Filter ForSupalearnID data for current teacher (safe)
        qual_df = supa_demofit_df.copy() if supa_demofit_df is not None else pd.DataFrame()
        qual_df.columns = qual_df.columns.str.strip()
        if 'Teacher id' in qual_df.columns:
            qual_df['Teacher id'] = qual_df['Teacher id'].astype(str).str.strip().str.lower()
            qual_df_filtered = qual_df[qual_df['Teacher id'] == teacher_id_norm]
        else:
            # try alternative casing
            teacher_col = next((c for c in qual_df.columns if 'teacher' in c.lower() and 'id' in c.lower()), None)
            if teacher_col:
                qual_df[teacher_col] = qual_df[teacher_col].astype(str).str.strip().str.lower()
                qual_df_filtered = qual_df[qual_df[teacher_col] == teacher_id_norm]
            else:
                qual_df_filtered = pd.DataFrame()

        class_quality_cols = [
            "Punctuality",
            "Video Status (On/Off)",
            "Communication",
            "Network Quality (Audio/Video)",
            "Background",
            "Outfit",
            "Device",
            "Light Issue",
            "Writing / Drawing",
            "Issues"
        ]

        missing_cols = [col for col in class_quality_cols if col not in qual_df_filtered.columns]
        if missing_cols and not qual_df_filtered.empty:
            st.warning(f"Missing columns in ForSupalearnID data: {missing_cols}")

        display_cols = [col for col in class_quality_cols if col in qual_df_filtered.columns]
        if not qual_df_filtered.empty and display_cols:
            df_quality = qual_df_filtered[display_cols]
            st.write("### 📋 Class Quality Details")
            st.dataframe(df_quality, use_container_width=True)
        else:
            st.info("No class quality data found for your profile.")

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["👩‍🏫 Profile", "📖 Daily Class Data", "👥 Student Details","📋 Chapter hour variance" ,"📋 Exam Details" ])

        with tab1:
            st.subheader("👩‍🏫 Teacher Profile")
            profile_data = st.session_state.get('profile_data', pd.DataFrame())
            if profile_data is not None and not profile_data.empty:
                # safe extraction with .get or checking column presence
                def show_col(df, col, label=None):
                    if col in df.columns:
                        st.write(f"**{label or col}:** {df[col].values[0]}")

                show_col(profile_data, 'Phone number', 'Phone')
                show_col(profile_data, 'Mail. id', 'Email')
                show_col(profile_data, 'Qualification')
                show_col(profile_data, 'Available Slots')
                lang_col = next((c for c in profile_data.columns if 'language' in c.lower()), None)
                if lang_col:
                    st.write(f"**Language Preference:** {profile_data[lang_col].values[0]}")

                syllabus_columns = ["IGCSE", "CBSE", "ICSE"]
                syllabus = [col for col in syllabus_columns if col in profile_data.columns and str(profile_data[col].values[0]).strip().upper() == "YES"]
                st.write("**Syllabus Expertise:** " + ", ".join(syllabus) if syllabus else "No syllabus marked.")

                # Subjects list: guard against index errors
                # You originally sliced columns 12:35 — safer to check length
                if profile_data.shape[1] >= 13:
                    subjects = profile_data.iloc[0, 12:35]
                    subjects = subjects[subjects != '']
                    if not subjects.empty:
                        st.write("**Subjects Handled**")
                        for subject, level in subjects.items():
                            st.markdown(f"- **{subject}** : Upto {level}th")
                    else:
                        st.write("No subjects listed.")
                else:
                    st.write("No subjects listed.")

                # Display demo bonus data (already stored in session)
                demobonus_data = st.session_state.get('demobonus', pd.DataFrame())
                st.write("**Your recent demo conversions. ₹300 reward per student converted:**")
                if demobonus_data is not None and not demobonus_data.empty:
                    st.dataframe(demobonus_data, use_container_width=True)
                else:
                    st.write("No demo bonus data available.")
            else:
                st.info("No profile data available to show.")

        with tab2:
            st.subheader("📖 Daily Class Log")
            merged_data = st.session_state.get('merged_data', pd.DataFrame())
            # safe column selection
            summary_cols = ["Date", "Student ID", "Student", "Class", "Syllabus", "Hr", "Type of class"]
            available_summary_cols = [c for c in summary_cols if c in merged_data.columns]
            if merged_data is None or merged_data.empty or not available_summary_cols:
                st.info("No daily class data available.")
            else:
                summary = merged_data[available_summary_cols].sort_values(by=[c for c in ["Date", "Student ID"] if c in available_summary_cols]).reset_index(drop=True)
                st.dataframe(highlight_duplicates(summary), use_container_width=True)
                st.download_button("📥 Download Summary", data=to_csv_download(summary),
                                   file_name=f"{st.session_state.get('teacher_name','teacher')}_summary.csv", mime="text/csv")

                st.write("## ⏱️ Consolidated Class Hours")
                if 'Hr' in summary.columns:
                    grouped = summary.groupby([c for c in ["Class", "Syllabus", "Type of class"] if c in summary.columns]).agg({"Hr": "sum"}).reset_index()
                    total_hours = summary['Hr'].sum()
                    st.write(f"### 🕒 Total Teaching Hours: {total_hours}")
                    st.dataframe(grouped, use_container_width=True)
                else:
                    st.info("No 'Hr' column found to compute consolidated hours.")

        with tab3:
            st.subheader("👥 Assigned Students & EM Info")
            merged_data = st.session_state.get('merged_data', pd.DataFrame())
            cols_for_em = ['Student ID', 'Student', 'EM', 'Phone Number']
            existing = [c for c in cols_for_em if c in merged_data.columns]
            if merged_data is None or merged_data.empty or not existing:
                st.info("No student/EM data available.")
            else:
                em_data = merged_data[existing].drop_duplicates()
                if 'Student' in em_data.columns:
                    st.dataframe(em_data.sort_values(by="Student"), use_container_width=True)
                else:
                    st.dataframe(em_data, use_container_width=True)

        with tab4:
            st.subheader("📋 Extra Hrs Details")
            # use teacher_id_norm computed above
            overfiltered = filter_overlimit_for_teacher(overlimit_df, teacher_id_norm)
            if overfiltered is None or overfiltered.empty:
                st.info("No overlimit/extra hours data found for your profile.")
            else:
                st.dataframe(overfiltered, use_container_width=True)

        with tab5:
            st.subheader("📋 Exam Details")
            exam_filtered = get_exam_data(teacher_id_norm, examlist_df)
            if exam_filtered is None or exam_filtered.empty:
                st.info("No exam data for your profile.")
            else:
                st.dataframe(exam_filtered, use_container_width=True)


if __name__ == "__main__":
    main()


