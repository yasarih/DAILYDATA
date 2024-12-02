import streamlit as st
import pandas as pd
from common_utils import fetch_data_from_sheet

# Function to load and preprocess data
@st.cache_data
def load_data(spreadsheet_id, sheet_name):
    """
    Fetch data from the specified spreadsheet and preprocess it.
    Normalize column names and prepare data for case-insensitive matching.
    """
    data = fetch_data_from_sheet(spreadsheet_id, sheet_name)
    
    # Normalize column names
    data.columns = data.columns.str.strip().str.lower()

    # Validate required columns
    required_columns = [
        "date", "subject", "hr", "teachers name", 
        "chapter taken", "type of class", "student id", "student"
    ]
    missing_columns = set(required_columns) - set(data.columns)
    if missing_columns:
        raise ValueError(f"Missing columns in data: {missing_columns}")

    # Filter required columns
    data = data[required_columns]

    # Normalize relevant columns for matching
    data["student id"] = data["student id"].astype(str).str.lower().str.strip()
    data["student"] = data["student"].astype(str).str.lower().str.strip()
    data["hr"] = pd.to_numeric(data["hr"], errors="coerce").fillna(0)
    
    # Convert 'Date' to datetime format
    data["date"] = pd.to_datetime(data["date"], errors="coerce")  # Coerce invalid dates to NaT

    return data

# Main application
def main():
    st.set_page_config(page_title="Student Insights App", layout="wide")
    st.title("Student Insights and Analysis")

    # Load data
    spreadsheet_id = "17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y"  # Replace with your spreadsheet ID
    try:
        student_data = load_data(spreadsheet_id, "Student class details")
    except ValueError as e:
        st.error(str(e))
        return

    # Inputs for verification
    student_id = st.text_input("Enter Your Student ID").strip().lower()
    student_name_part = st.text_input("Enter Any Part of Your Name (minimum 4 characters)").strip().lower()

    # Month dropdown
    month = st.selectbox(
        "Select Month",
        options=list(range(1, 13)),
        format_func=lambda x: pd.to_datetime(f"2024-{x}-01").strftime('%B')  # Show month names
    )

    if st.button("Fetch Data"):
        if not student_id or len(student_name_part) < 4:
            st.error("Please enter a valid Student ID and at least 4 characters of your name.")
            return

        # Filter data based on student ID, partial name match, and month
        filtered_data = student_data[
            (student_data["student id"] == student_id) &
            (student_data["student"].str.contains(student_name_part, na=False)) &
            (student_data["date"].dt.month == month)  # Filter by selected month
        ]

        if not filtered_data.empty:
            student_name = filtered_data["student"].iloc[0].title()  # Display name in title case
            st.subheader(f"Welcome, {student_name}!")

            # Format 'Date' as DD/MM/YYYY for display purposes
            filtered_data["date"] = filtered_data["date"].dt.strftime('%d/%m/%Y')

            # Remove "student id" and "student" columns before displaying
            final_data = filtered_data.drop(columns=["student id", "student"])
            final_data = final_data.reset_index(drop=True)

            # Display subject breakdown
            subject_hours = (
                filtered_data.groupby("subject")["hr"]
                .sum()
                .reset_index()
                .rename(columns={"hr": "Total Hours"})
            )

            st.write("**Your Monthly Class Details**")
            st.dataframe(final_data)  # Display final data without hidden columns
            st.subheader("Subject-wise Hour Breakdown")
            st.dataframe(subject_hours)

            total_hours = filtered_data["hr"].sum()
            st.write(f"**Total Hours:** {total_hours:.2f}")
        else:
            st.error(f"No data found for the given Student ID, Name, and selected month ({pd.to_datetime(f'2024-{month}-01').strftime('%B')}).")

# Run the app
if __name__ == "__main__":
    main()
