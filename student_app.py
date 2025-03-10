import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

st.set_page_config(
    page_title="Student Insights",
    page_icon="🎓",
    layout="wide"
)

def load_credentials_from_secrets():
    try:
        credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])
        return credentials_info
    except KeyError:
        st.error("Google credentials not found in Streamlit secrets.")
        return None

def connect_to_google_sheets(spreadsheet_id, worksheet_name):
    credentials_info = load_credentials_from_secrets()
    if not credentials_info:
        return None
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
        client = gspread.authorize(credentials)
        return client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

def fetch_data_from_sheet(spreadsheet_id, worksheet_name):
    sheet = connect_to_google_sheets(spreadsheet_id, worksheet_name)
    if not sheet:
        return pd.DataFrame()
    try:
        data = sheet.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0]) if data else pd.DataFrame()
        st.write("Available columns:", df.columns.tolist())  # Debugging statement
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def show_student_data(data, student_id, student_name_part):
    required_columns = ["MM", "Year", "Student ID", "Student", "Date", "Subject", "Hr", "Teachers Name", "Chapter taken", "Type of class"]
    missing_columns = [col for col in required_columns if col not in data.columns]
    
    if missing_columns:
        st.error(f"Missing required columns: {missing_columns}")
        return
    
    month = st.sidebar.selectbox("Select Month", sorted(data["MM"].unique()))
    year = st.sidebar.selectbox("Select Year", sorted(data["Year"].unique()))
    
    filtered_data = data[(data["MM"] == month) & (data["Year"] == year) &
                         (data["Student ID"].str.lower().str.strip() == student_id) &
                         (data["Student"].str.lower().str.contains(student_name_part))]
    
    if filtered_data.empty:
        st.error("No records found. Check your details.")
        return
    
    student_name = filtered_data["Student"].iloc[0]
    st.subheader(f"📚 Welcome, {student_name}!")
    
    st.subheader("Your Monthly Class Data")
    st.write(filtered_data[required_columns[4:]])  # Display relevant data columns
    
    total_hours = filtered_data["Hr"].astype(float).sum()
    st.write(f"**Total Hours:** {total_hours:.2f}")
    
    subject_hours = filtered_data.groupby("Subject")["Hr"].sum().reset_index()
    subject_hours.columns = ["Subject", "Total Hours"]
    st.subheader("📊 Subject-wise Hour Breakdown")
    st.write(subject_hours)

def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=250)
    st.title("Student Insights Dashboard")
    
    if "data" not in st.session_state:
        st.session_state.data = fetch_data_from_sheet("1CtmcRqCRReVh0xp-QCkuVzlPr7KDdEquGNevKOA1e4w", "Student Data")
    
    if st.sidebar.button("Refresh Data"):
        st.session_state.data = fetch_data_from_sheet("1CtmcRqCRReVh0xp-QCkuVzlPr7KDdEquGNevKOA1e4w", "Student Data")
        st.success("Data refreshed successfully!")
    
    student_id = st.text_input("Enter Student ID").strip().lower()
    student_name_part = st.text_input("Enter any part of your name (min 4 characters)").strip().lower()
    
    if st.button("Fetch Data"):
        show_student_data(st.session_state.data, student_id, student_name_part)

if __name__ == "__main__":
    main()
