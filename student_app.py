import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Set Streamlit page configuration
st.set_page_config(page_title="Student Insights App", layout="wide")

# Function to fetch data from Google Sheets using GID
@st.cache_data(show_spinner=False)
def fetch_data_from_gid(spreadsheet_id, gid):
    """
    Fetch data from a specific Google Sheets worksheet using its GID and return it as a DataFrame.
    """
    try:
        # Load credentials from Streamlit secrets
        credentials_info = st.secrets["google_credentials_new_project"]
        credentials = Credentials.from_service_account_info(credentials_info)
        client = gspread.authorize(credentials)

        # Open the spreadsheet
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = next(
            (ws for ws in spreadsheet.worksheets() if ws.id == int(gid)), None
        )
        if not worksheet:
            raise ValueError(f"No worksheet found with GID: {gid}")

        # Fetch data from the worksheet
        data = worksheet.get_all_values()
        if not data or len(data) < 2:
            raise ValueError(f"No data found in the sheet with GID: {gid}")

        # Use the first row as headers and remaining rows as data
        df = pd.DataFrame(data[1:], columns=data[0])
        return df

    except Exception as e:
        st.error(f"Error fetching data from Google Sheets: {e}")
        st.stop()

# Function to preprocess data
@st.cache_data(show_spinner=False)
def preprocess_data(data):
    """
    Normalize and preprocess data for case-insensitive matching.
    """
    st.write("Columns in dataset:", data.columns.tolist())  # Debugging

    # Normalize column names to match new required columns
    data.columns = data.columns.str.strip()

    # Validate required columns
    required_columns = [
        "Date", "Subject", "Hr", "Teachers Name",
        "Chapter taken", "Type of class", "Student ID", "Student"
    ]
    missing_columns = set(required_columns) - set(data.columns)
    if missing_columns:
        raise ValueError(f"Missing columns in data: {missing_columns}")

    # Filter and normalize data
    data = data[required_columns]
    data.rename(columns=lambda x: x.strip().lower(), inplace=True)  # Normalize columns to lowercase

    # Normalize relevant columns
    data["student id"] = data["student id"].astype(str).str.lower().str.strip()
    data["student"] = data["student"].astype(str).str.lower().str.strip()
    data["hr"] = pd.to_numeric(data["hr"], errors="coerce").fillna(0)
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data.dropna(subset=["date", "hr"], inplace=True)
    return data

# Main application
def main():
    st.title("Student Insights and Analysis")

    # Google Sheets configuration
    spreadsheet_id = "1CtmcRqCRReVh0xp-QCkuVzlPr7KDdEquGNevKOA1e4w"
    gid = "1061281247"

    try:
        raw_data = fetch_data_from_gid(spreadsheet_id, gid)
        st.write("Raw data from Google Sheets:", raw_data.head())  # Debugging
        student_data = preprocess_data(raw_data)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    student_id = st.text_input("Enter Your Student ID", placeholder="e.g., 12345").strip().lower()
    student_name_part = st.text_input(
        "Enter Any Part of Your Name (minimum 4 characters)",
        placeholder="e.g., John"
    ).strip().lower()

    if len(student_name_part) < 4 and student_name_part:
        st.warning("Please enter at least 4 characters of your name.")

    month = st.selectbox(
        "Select Month",
        options=list(range(1, 13)),
        format_func=lambda x: pd.to_datetime(f"2024-{x}-01").strftime('%B')
    )

    if st.button("Fetch Data"):
        if not student_id or len(student_name_part) < 4:
            st.error("Please enter a valid Student ID and at least 4 characters of your name.")
            return

        filtered_data = student_data[
            (student_data["student id"] == student_id) &
            (student_data["student"].str.contains(student_name_part, na=False)) &
            (student_data["date"].dt.month == month)
        ]

        if not filtered_data.empty:
            student_name = filtered_data["student"].iloc[0].title()
            st.subheader(f"Welcome, {student_name}!")
            filtered_data["date"] = filtered_data["date"].dt.strftime('%d/%m/%Y')
            final_data = filtered_data.drop(columns=["student id", "student"]).reset_index(drop=True)

            subject_hours = (
                filtered_data.groupby("subject")["hr"]
                .sum()
                .reset_index()
                .rename(columns={"hr": "Total Hours"})
            )

            st.write("**Your Monthly Class Details**")
            st.dataframe(final_data)
            st.subheader("Subject-wise Hour Breakdown")
            st.dataframe(subject_hours)

            total_hours = filtered_data["hr"].sum()
            st.write(f"**Total Hours:** {total_hours:.2f}")
        else:
            st.info(f"No data found for the selected criteria.")

if __name__ == "__main__":
    main()
