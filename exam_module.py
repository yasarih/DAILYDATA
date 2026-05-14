import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials


# =========================
# 🧠 SAFE COLUMN FINDER
# =========================
def get_col(df, name):

    target = str(name).lower().replace(" ", "").replace(".", "")

    for col in df.columns:

        clean = str(col).lower().replace(" ", "").replace(".", "")

        if clean == target:
            return col

    return None


# =========================
# 📊 SUMMARY + WARNINGS
# =========================
def render_exam_summary(df):

    if df is None or df.empty:
        return

    df = df.copy()

    df["Exam Status"] = df["Exam Status"].replace("", "Not Scheduled")

    df["Exam Schedule"] = pd.to_datetime(
        df["Exam Schedule"],
        errors="coerce",
        dayfirst=True
    )

    today = pd.to_datetime("today").normalize()

    # -------------------------
    # 📊 COUNTS
    # -------------------------
    total = len(df)

    completed = (df["Exam Status"] == "Completed").sum()

    scheduled = (df["Exam Status"] == "Schedule").sum()

    not_completed = (
        df["Exam Status"] == "Chapter Not Completed"
    ).sum()

    not_scheduled = (
        df["Exam Status"] == "Not Scheduled"
    ).sum()

    # -------------------------
    # 🎯 METRICS
    # -------------------------
    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Total", total)
    c2.metric("Completed", completed)
    c3.metric("Scheduled", scheduled)
    c4.metric("Chapter Not Completed", not_completed)
    c5.metric("Not Scheduled", not_scheduled)

    st.divider()

    # -------------------------
    # ⚠️ WARNINGS
    # -------------------------

    # 1️⃣ Not Scheduled
    missing_status = df[
        df["Exam Status"] == "Not Scheduled"
    ]

    if not missing_status.empty:
        st.warning(
            f"⚠️ {len(missing_status)} exams are NOT SCHEDULED"
        )

    # 2️⃣ Overdue Exams
    overdue = df[
        (df["Exam Status"] == "Schedule")
        &
        (df["Exam Schedule"].notna())
        &
        (df["Exam Schedule"] < today)
    ]

    if not overdue.empty:
        st.error(
            f"⏰ {len(overdue)} exams are OVERDUE — mark completed & enter marks"
        )

    # 3️⃣ Completed but No Marks
    missing_marks = df[
        (df["Exam Status"] == "Completed")
        &
        (
            (df["Score"].isna())
            |
            (df["Max Score"].isna())
        )
    ]

    if not missing_marks.empty:
        st.error(
            f"🚫 {len(missing_marks)} completed exams have NO MARKS"
        )

    st.divider()


# =========================
# 📊 EXAM TAB UI
# =========================
def render_exam_tab(
    df,
    teacher_id,
    sheet_id,
    load_credentials
):

    if df is None or df.empty:
        st.info("No exam data found.")
        return

    df = df.copy()

    # -------------------------
    # COLUMN MAPPING
    # -------------------------
    col_student = get_col(df, "StudentID")
    col_teacher = get_col(df, "TeacherID")
    col_subject = get_col(df, "Subject")
    col_chapter = get_col(df, "Chapters")
    col_status = get_col(df, "Exam Status")
    col_schedule = get_col(df, "Exam Schedule")
    col_score = get_col(df, "Score")
    col_max = get_col(df, "Max Score")
    col_name = get_col(df, "StudentName")

    # -------------------------
    # CREATE MISSING COLUMNS
    # -------------------------
    for c in [
        "Exam Status",
        "Exam Schedule",
        "Score",
        "Max Score"
    ]:
        if get_col(df, c) is None:
            df[c] = ""

    # refresh mapping
    col_status = get_col(df, "Exam Status")
    col_schedule = get_col(df, "Exam Schedule")
    col_score = get_col(df, "Score")
    col_max = get_col(df, "Max Score")

    # -------------------------
    # FILTER TEACHER
    # -------------------------
    if col_teacher:

        df[col_teacher] = (
            df[col_teacher]
            .astype(str)
            .str.lower()
            .str.strip()
        )

        df = df[
            df[col_teacher]
            ==
            teacher_id.lower().strip()
        ]

    if df.empty:
        st.info("No exam data for your profile.")
        return

    # -------------------------
    # RESET INDEX
    # -------------------------
    df = df.reset_index()

    # -------------------------
    # BUILD TABLE
    # -------------------------
    edit_df = pd.DataFrame({

        "index":
            df["index"],

        "Student ID":
            df[col_student] if col_student else "",

        "Student Name":
            df[col_name] if col_name else "",

        "Subject":
            df[col_subject] if col_subject else "",

        "Chapter":
            df[col_chapter] if col_chapter else "",

        "Exam Status":
            df[col_status],

        "Exam Schedule":
            df[col_schedule],

        "Score":
            df[col_score],

        "Max Score":
            df[col_max]
    })

    # -------------------------
    # DEFAULT STATUS
    # -------------------------
    edit_df["Exam Status"] = (
        edit_df["Exam Status"]
        .replace("", "Not Scheduled")
    )

    # -------------------------
    # DATE FORMAT
    # -------------------------
    edit_df["Exam Schedule"] = pd.to_datetime(
        edit_df["Exam Schedule"],
        errors="coerce",
        dayfirst=True
    )

    # -------------------------
    # SAFE NUMBER CONVERSION
    # -------------------------
    edit_df["Score"] = pd.to_numeric(
        edit_df["Score"],
        errors="coerce"
    )

    edit_df["Max Score"] = pd.to_numeric(
        edit_df["Max Score"],
        errors="coerce"
    )

    # -------------------------
    # 🔥 SUMMARY
    # -------------------------
    render_exam_summary(edit_df)

    # -------------------------
    # ✏️ DATA EDITOR
    # -------------------------
    edited = st.data_editor(

        edit_df,

        use_container_width=True,

        hide_index=True,

        column_config={

            # 🔒 DROPDOWN ONLY
            "Exam Status": st.column_config.SelectboxColumn(
                "Exam Status",

                options=[
                    "Not Scheduled",
                    "Completed",
                    "Schedule",
                    "Chapter Not Completed"
                ],

                required=True,

                width="medium"
            ),

            # 📅 DATE ONLY
            "Exam Schedule": st.column_config.DateColumn(
                "Exam Schedule",

                format="DD/MM/YYYY",

                required=False
            ),

            # 🔢 SCORE
            "Score": st.column_config.NumberColumn(
                "Score",

                min_value=0.0,

                step=0.01,

                format="%.2f"
            ),

            # 🔢 MAX SCORE
            "Max Score": st.column_config.NumberColumn(
                "Max Score",

                min_value=0.0,

                step=0.01,

                format="%.2f"
            ),
        },

        # 🔒 LOCK NON-EDITABLE COLUMNS
        disabled=[
            "Student ID",
            "Student Name",
            "Subject",
            "Chapter"
        ]
    )

    # -------------------------
    # 💾 SAVE BUTTON
    # -------------------------
    if st.button("💾 Save Exam Updates"):

        updates = []

        today = pd.to_datetime(
            "today"
        ).normalize()

        for _, row in edited.iterrows():

            sheet_row = int(row["index"]) + 2

            status = row["Exam Status"]

            schedule = row["Exam Schedule"]

            # -------------------------
            # SAFE SCORE FORMAT
            # -------------------------
            score = (
                round(float(row["Score"]), 2)
                if pd.notna(row["Score"])
                else ""
            )

            max_score = (
                round(float(row["Max Score"]), 2)
                if pd.notna(row["Max Score"])
                else ""
            )

            # -------------------------
            # DATE FORMAT
            # -------------------------
            if pd.notna(schedule):

                schedule_str = pd.to_datetime(
                    schedule
                ).strftime("%d/%m/%Y")

            else:
                schedule_str = ""

            # -------------------------
            # 🧠 VALIDATION LOGIC
            # -------------------------

            # ✅ COMPLETED
            if status == "Completed":

                if not schedule_str:
                    st.warning(
                        f"Select exam date for row {sheet_row}"
                    )
                    return

                if (
                    pd.isna(row["Score"])
                    or
                    pd.isna(row["Max Score"])
                ):
                    st.warning(
                        f"Enter marks for row {sheet_row}"
                    )
                    return

            # ✅ SCHEDULE
            elif status == "Schedule":

                if not schedule_str:
                    st.warning(
                        f"Select date for row {sheet_row}"
                    )
                    return

            # ✅ CHAPTER NOT COMPLETED
            elif status == "Chapter Not Completed":

                score = ""
                max_score = ""

            # ✅ NOT SCHEDULED
            elif status == "Not Scheduled":

                schedule_str = ""
                score = ""
                max_score = ""

            # -------------------------
            # UPDATE RANGE
            # -------------------------
            updates.append({

                "range":
                    f"E{sheet_row}:H{sheet_row}",

                "values":
                    [[
                        status,
                        schedule_str,
                        score,
                        max_score
                    ]]
            })

        # -------------------------
        # 🚀 GOOGLE SHEETS UPDATE
        # -------------------------
        if updates:

            creds = Credentials.from_service_account_info(

                load_credentials(),

                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
            )

            client = gspread.authorize(creds)

            ws = client.open_by_key(
                sheet_id
            ).worksheet("ExamDetails")

            ws.batch_update(updates)

            st.success("✅ Updated successfully")

            st.rerun()