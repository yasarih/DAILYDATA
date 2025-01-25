import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Set Streamlit page configuration
st.set_page_config(page_title="Student Insights App", layout="wide")

# Function to fetch data from Google Sheets using GID
@st.cache_data(show_spinner=False)
def fetch_data_from_sheet(spreadsheet_id, gid):
    """
    Fetch data from a specific Google Sheets worksheet using its GID and return it as a DataFrame.
    """
    try:
        # Load credentials from Streamlit secrets
        credentials_info = st.secrets.get("google_credentials_new_project", {}).get("data")
        if not credentials_info:
            st.error("Google API credentials are missing in Streamlit secrets.")
            st.stop()
        
        credentials = Credentials.from_service_account_info(credentials_info)
        client = gspread.authorize(credentials)

        # Open the spreadsheet
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = next((ws for ws in spreadsheet.worksheets() if ws.id == int(gid)), None)
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
def load_data(spreadsheet_id, gid):
    """
    Fetch data from the specified spreadsheet and preprocess it.
    Normalize column names and prepare data for case-insensitive matching.
    """
    data = fetch_data_from_sheet(spreadsheet_id, gid)
    
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
    
    # Convert 'date' to datetime format
    data["date"] = pd.to_datetime(data["date"], errors="coerce")  # Coerce invalid dates to NaT

    return data

# Main application
def main():
    st.title("Student Insights and Analysis")

    # Inputs for Google Sheets configuration
    spreadsheet_id = st.text_input("Enter Google Spreadsheet ID", value="1CtmcRqCRReVh0xp-QCkuVzlPr7KDdEquGNevKOA1e4w")
    sheet_gid = st.text_input("Enter Worksheet GID", value="0")  # Default GID value is often 0

    if spreadsheet_id and sheet_gid:
        try:
            student_data = load_data(spreadsheet_id, sheet_gid)
        except ValueError as e:
            st.error(str(e))
            return

        # Inputs for student verification
        student_id = st.text_input("Enter Your Student ID").strip().lower()
        student_name_part = st.text_input("Enter Any Part of Your Name (minimum 4 characters)").strip().lower()

        # Month dropdown
        month = st.selectbox(
            "Select Month",
            options=list(range(1, 13)),
            format_func=lambda x: pd.to_datetime(f"2024-{x}-01").strftime('%B')  # Show month names
        )

        # Fetch and display data
        if st.button("Fetch Data"):
            if not student_id or len(student_name_part) < 4:
                st.error("Please enter a valid Student ID and at least 4 characters of your name.")
                return

            # Filter data based on student ID, partial name match, and month
            filtered_data = student_data[
                (student_data["student id"] == student_id) &
                (student_data["student"].str.contains(student_name_part, na=False, regex=False)) &
                (student_data["date"].dt.month == month)
            ]

            if filtered_data.empty:
                st.error(f"No data found for the given Student ID, Name, and selected month ({pd.to_datetime(f'2024-{month}-01').strftime('%B')}).")
                return

            # Debug columns in filtered data
            st.write("Filtered Data Columns:", filtered_data.columns.tolist())

            if "subject" not in filtered_data.columns or "hr" not in filtered_data.columns:
                st.error("Required columns ('subject' or 'hr') are missing from the data.")
                return

            student_name = filtered_data["student"].iloc[0].title()  # Display name in title case
            st.subheader(f"Welcome, {student_name}!")

            # Format 'date' as DD/MM/YYYY for display purposes
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

# Run the app
if __name__ == "__main__":
    main()
