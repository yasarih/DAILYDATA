import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np

st.set_page_config(page_title="Angle Belearn Insights", page_icon="🎓", layout="wide")


# =========================
# 🔐 CREATE CLIENT (CACHED)
# =========================
@st.cache_data(show_spinner=False)
def load_credentials():
    return dict(st.secrets["google_credentials_new_project"])


@st.cache_data(show_spinner=False)
def get_client():
    creds_info = load_credentials()
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    return gspread.authorize(creds)


# =========================
# 📂 FETCH SHEET DATA (CACHED FOR 5 MIN)
# =========================
@st.cache_data(ttl=300, show_spinner=True)
def fetch_data(sheet_id, worksheet):
    try:
        client = get_client()
        ws = client.open_by_key(sheet_id).worksheet(worksheet)
        data = ws.get_all_values()
    except Exception as e:
        st.error(f"Error loading sheet: {e}")
        return pd.DataFrame()

    if not data:
        return pd.DataFrame()

    headers = pd.Series(data[0]).fillna("").astype(str).str.strip()
    # avoid duplicate names
    headers = headers.where(headers != "", other="Unnamed")
    headers = headers + headers.groupby(headers).cumcount().astype(str).replace("0", "")

    df = pd.DataFrame(data[1:], columns=headers)
    df.columns = df.columns.str.strip()
    df.replace("", np.nan, inplace=True)
    df.fillna("", inplace=True)

    # Normalize Hr column
    if "Hr" in df.columns:
        df["Hr"] = pd.to_numeric(df["Hr"], errors="coerce").fillna(0)

    return df


# =========================
# 🔗 MERGE TEACHER + STUDENT
# =========================
@st.cache_data(show_spinner=False)
def merge_teacher_student(main_df, student_df):
    if main_df.empty or student_df.empty:
        return main_df

    main_df = main_df.copy()
    student_df = student_df.copy()

    # Normalize Student ID
    if "Student id" in main_df.columns:
        main_df.rename(columns={"Student id": "Student ID"}, inplace=True)
    if "Student id" in student_df.columns:
        student_df.rename(columns={"Student id": "Student ID"}, inplace=True)

    if "Student ID" not in student_df.columns:
        return main_df

    # Normalize EM Phone → Phone Number
    if "EM Phone" in student_df.columns and "Phone Number" not in student_df.columns:
        student_df.rename(columns={"EM Phone": "Phone Number"}, inplace=True)

    merge_cols = [c for c in ["Student ID", "EM", "Phone Number"] if c in student_df.columns]

    try:
        return main_df.merge(student_df[merge_cols], on="Student ID", how="left")
    except:
        return main_df


# =========================
# 🎨 HIGHLIGHT DUPLICATES
# =========================
def highlight_duplicates(df):
    if df.empty:
        return df
    dupes = df[df.duplicated(["Date", "Student ID"], keep=False)]
    return df.style.apply(
        lambda r: ["background-color: lightcoral" if r.name in dupes.index else "" for _ in r],
        axis=1,
    )


# =========================
# 🔍 FILTER OVERLIMIT
# =========================
@st.cache_data(show_spinner=False)
def filter_overlimit_for_teacher(df, teacher_id_norm):
    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    teacher_col = next(
        (c for c in df.columns if "teacher" in c.lower() and "id" in c.lower()),
        None,
    )
    if teacher_col:
        df[teacher_col] = df[teacher_col].astype(str).str.lower().str.strip()
        df = df[df[teacher_col] == teacher_id_norm]

    cols = [
        "EM",
        "Student ID",
        "Student",
        "Chapter Taken",
        "Hours Taken",
        "Max. Hours Alloted",
    ]
    final_cols = [c for c in cols if c in df.columns]
    if not final_cols:
        return pd.DataFrame()

    df = df[final_cols]

    # compute difference
    if "Hours Taken" in df.columns and "Max. Hours Alloted" in df.columns:
        df["Difference"] = (
            pd.to_numeric(df["Hours Taken"], errors="coerce")
            - pd.to_numeric(df["Max. Hours Alloted"], errors="coerce")
        )

    return df


# =========================
# 👨‍🏫 TEACHER PROFILE
# =========================
@st.cache_data(show_spinner=False)
def get_teacher_profile(teacher_id, profile_df):
    if profile_df.empty:
        return pd.DataFrame()

    df = profile_df.copy()

    teacher_col = next(
        (c for c in df.columns if "teacher" in c.lower() and "id" in c.lower()),
        None,
    )
    if not teacher_col:
        return pd.DataFrame()

    df[teacher_col] = df[teacher_col].astype(str).str.strip().str.lower()

    return df[df[teacher_col] == teacher_id]


# =========================
# 📊 MAIN STREAMLIT UI
# =========================
def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=250)
    st.title("Angle Belearn - Teacher Dashboard")

    # Refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Load sheets (cached)
    sheet_id = "1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4"
    sheet_id2 = "1Edkaa-mlW1Huc6ereT8vu6ZNlusInc998zLHrJYDswk"

    class_df = fetch_data(sheet_id, "Student class details")
    student_df = fetch_data(sheet_id, "Student Data")
    profile_df = fetch_data(sheet_id, "Profile")
    supa_demofit_df = fetch_data(sheet_id, "ForSupalearnID")
    demoBonus_df = fetch_data(sheet_id, "DemoBonus")
    overlimit_df = fetch_data(sheet_id2, "OverlimitCall")
    examlist_df = fetch_data(sheet_id2, "ExamList")

    # -------------------
    # 🔐 LOGIN
    # -------------------
    st.subheader("🔐 Login")
    input_teacher_id = st.text_input("Enter Your Teacher ID").strip().lower()
    teacher_pass = st.text_input("Enter last 4 digits of your phone number")
    month = st.selectbox("Pick Month", list(range(8, 13)))
    month_str = f"{month:02}"

    if st.button("Login"):
        df = class_df.copy()
        if df.empty:
            st.error("Class data not available.")
            return

        # Normalize
        df["Teachers ID"] = df.get("Teachers ID", "").astype(str).str.lower().str.strip()
        df["Password"] = df.get("Password", "").astype(str).str.strip()
        df["MM"] = df.get("MM", "").astype(str).str.zfill(2)

        filtered = df[
            (df["Teachers ID"] == input_teacher_id)
            & (df["Password"] == teacher_pass)
            & (df["MM"] == month_str)
        ]

        if filtered.empty:
            st.error("Invalid credentials or data not found.")
            return

        # Save session
        st.session_state.teacher_id = input_teacher_id
        st.session_state.teacher_name = filtered["Teachers Name"].iloc[0].title()
        st.session_state.filtered_data = filtered
        st.session_state.merged_data = merge_teacher_student(filtered, student_df)
        st.session_state.profile_data = get_teacher_profile(input_teacher_id, profile_df)

        st.rerun()

    # =========================
    # AFTER LOGIN
    # =========================
    if "teacher_name" in st.session_state:
        st.success(f"Welcome, {st.session_state.teacher_name}! 🎉")

        teacher_id_norm = st.session_state.teacher_id.lower()

        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            ["👩‍🏫 Profile", "📖 Daily Class Data", "👥 Student Details", "📋 Extra Hrs", "📋 Exam Details"]
        )

        # ------------------
        # PROFILE TAB
        # ------------------
        with tab1:
            profile_data = st.session_state.profile_data
            if not profile_data.empty:
                st.dataframe(profile_data, use_container_width=True)
            else:
                st.info("Profile data not available.")

        # ------------------
        # DAILY DATA
        # ------------------
        with tab2:
            merged = st.session_state.merged_data
            if merged.empty:
                st.info("No class data available.")
            else:
                summary_cols = ["Date", "Student ID", "Student", "Class", "Syllabus", "Hr", "Type of class"]
                cols = [c for c in summary_cols if c in merged.columns]

                df_show = merged[cols].sort_values(["Date", "Student ID"])
                st.dataframe(highlight_duplicates(df_show), use_container_width=True)

        # ------------------
        # STUDENT DETAILS
        # ------------------
        with tab3:
            merged = st.session_state.merged_data
            cols = [c for c in ["Student ID", "Student", "EM", "Phone Number"] if c in merged.columns]
            st.dataframe(merged[cols].drop_duplicates(), use_container_width=True)

        # ------------------
        # EXTRA HRS
        # ------------------
        with tab4:
            result = filter_overlimit_for_teacher(overlimit_df, teacher_id_norm)
            st.dataframe(result, use_container_width=True)

        # ------------------
        # EXAM DETAILS
        # ------------------
        with tab5:
            df = examlist_df.copy()
            teacher_col = next((c for c in df.columns if "teacher" in c.lower()), None)
            df[teacher_col] = df[teacher_col].astype(str).str.lower().str.strip()
            st.dataframe(df[df[teacher_col] == teacher_id_norm], use_container_width=True)


if __name__ == "__main__":
    main()
