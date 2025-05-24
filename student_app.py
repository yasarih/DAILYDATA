import streamlit as st
import pandas as pd
from common_utils import fetch_data_from_sheet

@st.cache_data
def load_data(spreadsheet_id, sheet_name):
    data = fetch_data_from_sheet(spreadsheet_id, sheet_name)
    data.columns = data.columns.str.strip().str.lower()

    required_columns = [
        "date", "subject", "hr", "teachers name", 
        "chapter taken", "type of class", "student id", "student"
    ]
    missing_columns = set(required_columns) - set(data.columns)
    if missing_columns:
        raise ValueError(f"Missing columns in data: {missing_columns}")

    data = data[required_columns]

    data["student id"] = data["student id"].astype(str).str.lower().str.strip()
    data["student"] = data["student"].astype(str).str.lower().str.strip()
    data["hr"] = pd.to_numeric(data["hr"], errors="coerce").fillna(0)

    # Try parsing dates with more flexibility:
    data["date"] = pd.to_datetime(data["date"], errors="coerce", dayfirst=True)

    # Debugging: show how many dates failed to parse
    failed_dates = data["date"].isna().sum()
    if failed_dates > 0:
        st.warning(f"Warning: {failed_dates} date entries could not be parsed and will show as empty.")

    return data

def main():
    st.set_page_config(page_title="Student Insights App", layout="wide")
    st.title("Student Insights and Analysis")

    spreadsheet_id = "1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4"
    try:
        student_data = load_data(spreadsheet_id, "Student class details")
    except ValueError as e:
        st.error(str(e))
        return

    student_id = st.text_input("Enter Your Student ID").strip().lower()
    student_name_part = st.text_input("Enter Any Part of Your Name (minimum 4 characters)").strip().lower()

    if st.button("Fetch Data"):
        if not student_id or len(student_name_part) < 4:
            st.error("Please enter a valid Student ID and at least 4 characters of your name.")
            return

        filtered_data = student_data[
            (student_data["student id"] == student_id) &
            (student_data["student"].str.contains(student_name_part, na=False))
        ]

        if not filtered_data.empty:
            student_name = filtered_data["student"].iloc[0].title()
            st.subheader(f"Welcome, {student_name}!")

            # Format date, fallback for missing dates
            filtered_data["date"] = filtered_data["date"].dt.strftime('%d/%m/%Y')
            filtered_data["date"] = filtered_data["date"].fillna("Date not available")

            final_data = filtered_data.drop(columns=["student id", "student"]).reset_index(drop=True)

            subject_hours = (
                filtered_data.groupby("subject")["hr"]
                .sum()
                .reset_index()
                .rename(columns={"hr": "Total Hours"})
            )

            st.write("**Your Class Details**")
            st.dataframe(final_data)
            st.subheader("Subject-wise Hour Breakdown")
            st.dataframe(subject_hours)

            total_hours = filtered_data["hr"].sum()
            st.write(f"**Total Hours:** {total_hours:.2f}")
        else:
            st.error("No data found for the given Student ID and Name.")

if __name__ == "__main__":
    main()
