import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
import json

# Constants
SPREADSHEET_ID = "1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4"
WORKSHEET_NAME = "Student class details"

# Page config
st.set_page_config(page_title="Student Insights App", page_icon="🎓", layout="wide")

# Load credentials
def load_credentials_from_secrets():
    try:
        credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])
        return credentials_info
    except KeyError:
        st.error("Google credentials not found in Streamlit secrets.")
        return None

# Connect to Google Sheets
def connect_to_google_sheets(spreadsheet_id, worksheet_name):
    credentials_info = load_credentials_from_secrets()
    if not credentials_info:
        return None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
    ]

    try:
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
        return sheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

# Fetch data
def fetch_data(spreadsheet_id, worksheet_name):
    sheet = connect_to_google_sheets(spreadsheet_id, worksheet_name)
    if not sheet:
        return pd.DataFrame()

    data = sheet.get_all_values()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data[1:], columns=[h.strip().lower() for h in data[0]])
    return df

# Preprocess data
@st.cache_data
def load_data():
    df = fetch_data(SPREADSHEET_ID, WORKSHEET_NAME)

    # Basic cleaning
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.replace('', pd.NA)
    df.dropna(subset=["student id", "student", "mm"], inplace=True)

    # Lowercase for consistent filtering
    df["student id"] = df["student id"].str.lower()
    df["student"] = df["student"].str.lower()

    # Convert mm to int (from '04' etc.)
    df["mm"] = pd.to_numeric(df["mm"], errors="coerce").fillna(0).astype(int)

    # Date and hr cleanup
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["hr"] = pd.to_numeric(df["hr"], errors="coerce").fillna(0)

    return df

# Streamlit main
def main():
    st.title("🎓 Student Insights")

    df = load_data()

    student_id = st.text_input("Enter Student ID").strip().lower()
    name_part = st.text_input("Enter part of your name (min 4 characters)").strip().lower()
    month = st.selectbox("Pick Month", list(range(1, 13)))

    if st.button("Fetch Data"):
        if not student_id or len(name_part) < 4:
            st.error("Enter a valid Student ID and at least 4 letters of your name.")
            return

        # First filter: by ID and partial name
        filtered = df[
            (df["student id"] == student_id) &
            (df["student"].str.contains(name_part, na=False))
        ]

        if filtered.empty:
            st.warning("No matching student found.")
            return

        # Second filter: by selected month
        filtered = filtered[filtered["mm"] == month]

        if filtered.empty:
            st.warning(f"No data found for month {month:02d}.")
            return

        student_name = filtered["student"].iloc[0].title()
        st.subheader(f"Welcome, {student_name}")

        # Show class details
        show_cols = [c for c in filtered.columns if c not in ["teacher id ", "student", "mm","year"]]
        st.dataframe(filtered[show_cols].reset_index(drop=True))

        # Subject-wise summary
        subject_summary = filtered.groupby("subject")["hr"].sum().reset_index()
        subject_summary.rename(columns={"hr": "Total Hours"}, inplace=True)
        st.subheader("Subject-wise Hours")
        st.dataframe(subject_summary)

        # Weekly summary
        filtered["week"] = filtered["date"].dt.isocalendar().week
        weekly_summary = filtered.groupby("week")["hr"].sum().reset_index()
        weekly_summary.rename(columns={"hr": "Weekly Total Hours"}, inplace=True)
        st.subheader("Weekly Hours")
        st.dataframe(weekly_summary)

        # Total
        st.write(f"**Total Hours this month:** {filtered['hr'].sum():.2f}")

if __name__ == "__main__":
    main()
