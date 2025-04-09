import streamlit as st
import pandas as pd
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials
import json

# ----------------------- Google Sheet Authentication ---------------------- #

def authenticate_gsheets():
    # Load credentials from Streamlit secrets
    credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])
    credentials = Credentials.from_service_account_info(credentials_info)
    
    # Authenticate with Google Sheets
    client = gspread.authorize(credentials)
    return client

# ----------------------- Fetch Data ---------------------- #

def fetch_data_from_sheet(spreadsheet_id, worksheet_name):
    client = authenticate_gsheets()
    sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    data = sheet.get_all_values()
    
    if not data:
        st.error("No data found in the Google Sheet.")
        return pd.DataFrame()

    # Clean headers
    headers = pd.Series(data[0]).fillna('').str.strip().str.title()
    df = pd.DataFrame(data[1:], columns=headers)

    # Normalize column names
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    return df

# ----------------------- Data Cache ---------------------- #

@st.cache_data(ttl=600)
def fetch_cached_data(spreadsheet_id, worksheet_name):
    return fetch_data_from_sheet(spreadsheet_id, worksheet_name)

# ----------------------- Verify User ---------------------- #

def verify_user(data, teacher_id, name_part):
    required_columns = ['teachers_id', 'teachers_name', 'supalearn_password']
    
    if not all(col in data.columns for col in required_columns):
        st.error(f"Required columns missing in the data. Found columns: {data.columns.tolist()}")
        return False

    teacher_data = data[data['teachers_id'].str.lower() == teacher_id.lower()]
    
    if teacher_data.empty:
        return False

    teacher_name = teacher_data['teachers_name'].iloc[0]
    
    if name_part.lower() in teacher_name.lower():
        return teacher_data  # Return the teacher's full data (including Supalearn password)

    return False

# ----------------------- Main App ---------------------- #

def main():
    st.title("Teacher Attendance App")

    # Google Sheet details
    spreadsheet_id = "1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4"
    worksheet_name = "Student class details"

    # Load data
    data = fetch_cached_data(spreadsheet_id, worksheet_name)
    if data.empty:
        st.stop()

    # Month Selection first
    unique_months = pd.to_datetime(data['date'], errors='coerce').dt.month.dropna().unique()
    selected_month = st.selectbox("Select Month", sorted(unique_months))

    # Inputs for Teacher after selecting month
    teacher_id = st.text_input("Enter your Teacher ID:").strip()
    teacher_name = st.text_input("Enter your Name (partial or full):").strip()

    if teacher_id and teacher_name:
        teacher_data = verify_user(data, teacher_id, teacher_name)
        
        if teacher_data is not False:
            # Teacher Verified
            full_name = teacher_data['teachers_name'].iloc[0]
            supalearn_password = teacher_data['supalearn_password'].iloc[0]
            
            st.success(f"Welcome {full_name}!")
            st.write(f"Your Supalearn password: {supalearn_password}")

            # Filter data for the selected month and teacher
            teacher_filtered_data = data[data['teachers_id'].str.lower() == teacher_id.lower()]
            teacher_filtered_data['month'] = pd.to_datetime(teacher_filtered_data['date'], errors='coerce').dt.month

            # Filter by selected month
            teacher_filtered_data = teacher_filtered_data[teacher_filtered_data['month'] == selected_month]

            # Display only required columns for the logged-in teacher
            selected_columns = ['date', 'student', 'hr', 'class', 'board', 'subject', 'topic']
            teacher_filtered_data = teacher_filtered_data[selected_columns]

            # Show Teacher-specific Data for the selected month
            st.subheader(f"Data for Teacher: {full_name} (Month: {selected_month})")
            st.dataframe(teacher_filtered_data)
            
        else:
            st.error("Invalid Teacher ID or Name. Please check and try again.")

if __name__ == "__main__":
    main()
