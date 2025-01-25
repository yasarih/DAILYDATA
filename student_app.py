import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Function to connect to Google Sheets and fetch data using GID
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

        # Find the worksheet by GID
        worksheet = next(
            (ws for ws in spreadsheet.worksheets() if ws.id == int(gid)), None
        )
        if not worksheet:
            raise ValueError(f"No worksheet found with GID: {gid}")

        # Fetch data from the worksheet
        data = worksheet.get_all_values()
        if not data or len(data) < 2:  # Ensure there is data
            raise ValueError(f"No data found in the sheet with GID: {gid}")

        # Use the first row as headers and remaining rows as data
        df = pd.DataFrame(data[1:], columns=data[0])
        return df

    except KeyError:
        st.error("Google credentials not found in Streamlit secrets.")
        st.stop()
    except Exception as e:
        st.error(f"Error fetching data from Google Sheets: {e}")
        st.stop()

def preprocess_data(data):
    """
    Normalize and preprocess data for case-insensitive matching.
    """
    # Normalize column names
    data.columns = data.columns.str.strip().str.lower()

    # Validate required columns
    required_columns = [
        "date", "subject", "hr", "teachers name",
        "chapter taken", "type of class", "Student ID", "student"
    ]
    missing_columns = set(required_columns) - set(data.columns)
    if missing_columns:
        raise ValueError(f"Missing columns in data: {missing_columns}")

    # Filter required columns
    data = data[required_columns]

    # Normalize relevant columns
    data["Student ID"] = data["Student ID"].astype(str).str.lower().str.strip()
    data["student"] = data["student"].astype(str).str.lower().str.strip()
    data["hr"] = pd.to_numeric(data["hr"], errors="coerce").fillna(0)

    # Convert 'date' to datetime format and drop invalid rows
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data.dropna(subset=["date", "hr"], inplace=True)

    return data

# Main application
def main():
    st.set_page_config(page_title="Student Insights App", layout="wide")
    st.title("Student Insights and Analysis")

    # Google Sheets configuration
    spreadsheet_id = "1CtmcRqCRReVh0xp-QCkuVzlPr7KDdEquGNevKOA1e4w"  # Replace with your spreadsheet ID
    gid = "1061281247"  # Default GID

    try:
        # Fetch data using GID
        raw_data = fetch_data_from_gid(spreadsheet_id, gid)
        student_data = preprocess_data(raw_data)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    # Inputs for verification
    student_id = st.text_input("Enter Your Student ID", placeholder="e.g., 12345").strip().lower()
    student_name_part = st.text_input(
        "Enter Any Part of Your Name (minimum 4 characters)",
        placeholder="e.g., John"
    ).strip().lower()

    # Real-time warning for name input
    if len(student_name_part) < 4 and student_name_part:
        st.warning("Please enter at least 4 characters of your name.")

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

        # Filter data based on Student ID, partial name match, and month
        filtered_data = student_data[
            (student_data["Student ID"] == student_id) &
            (student_data["student"].str.contains(student_name_part, na=False)) &
            (student_data["date"].dt.month == month)  # Filter by selected month
        ]

        if not filtered_data.empty:
            student_name = filtered_data["student"].iloc[0].title()  # Display name in title case
            st.subheader(f"Welcome, {student_name}!")

            # Format 'Date' as DD/MM/YYYY for display purposes
            filtered_data["date"] = filtered_data["date"].dt.strftime('%d/%m/%Y')

            # Remove "Student ID" and "student" columns before displaying
            final_data = filtered_data.drop(columns=["Student ID", "student"])
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
            st.info(f"No data found for the given Student ID, Name, and selected month ({pd.to_datetime(f'2024-{month}-01').strftime('%B')}).")

# Run the app
if __name__ == "__main__":
    main()
