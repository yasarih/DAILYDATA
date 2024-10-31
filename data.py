import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# Set page layout and title
st.set_page_config(
    page_title="Angle Belearn Insights",
    page_icon="🎓",
    layout="wide"
)

# Function to load credentials from Streamlit secrets
def load_credentials_from_secrets():
    credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])
    return credentials_info

# Cached function to connect to Google Sheets using credentials from Streamlit secrets
@st.cache_data
def connect_to_google_sheets(spreadsheet_id, worksheet_name):
    credentials_info = load_credentials_from_secrets()
    
    # Define scopes required for Google Sheets API
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ]
    
    # Create credentials and authorize gspread
    credentials = Credentials.from_service_account_info(
        credentials_info,
        scopes=scopes
    )
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    return sheet

# Cached function to fetch data from Google Sheets and standardize column names
@st.cache_data
def fetch_all_data(spreadsheet_id, worksheet_name):
    sheet = connect_to_google_sheets(spreadsheet_id, worksheet_name)
    data = sheet.get_all_values()
    if data and len(data) > 1:
        headers = pd.Series(data[0]).fillna('').str.strip()
        headers = headers.where(headers != '', other='Unnamed')
        headers = headers + headers.groupby(headers).cumcount().astype(str).replace('0', '')
        df = pd.DataFrame(data[1:], columns=headers)
        
        # Standardize column names by stripping whitespace and converting to lowercase
        df.columns = df.columns.str.strip().str.lower()
        
        df.replace('', pd.NA, inplace=True)
        df.ffill(inplace=True)
        
        # Convert 'hr' column to numeric if it exists
        if 'hr' in df.columns:
            df['hr'] = pd.to_numeric(df['hr'], errors='coerce').fillna(0)
        
        # Check for month column or extract month from 'date' column
        if 'mm' not in df.columns:
            if 'date' in df.columns:
                # Attempt to parse 'date' column to extract month names
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                df['mm'] = df['date'].dt.strftime('%B')  # Extract month name
            else:
                st.error("No 'mm' or 'date' column found. Unable to determine month.")
        
        return df
    else:
        st.warning("No data found or the sheet is incorrectly formatted.")
        return pd.DataFrame()

# Function to merge student data with emergency contact (EM) data
@st.cache_data
def get_merged_data_with_em():
    main_data = fetch_all_data("17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y", "Student class details")
    em_data = fetch_all_data("17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y", "Student Data")
    
    # Normalize column names in both DataFrames
    main_data.columns = main_data.columns.str.lower().str.strip()
    em_data.columns = em_data.columns.str.lower().str.strip()
    
    # Rename columns to ensure compatibility for merging
    main_data = main_data.rename(columns={'student id': 'student id'})
    em_data = em_data.rename(columns={'student id': 'student id', 'em': 'em', 'em phone': 'phone number'})

    # Merge main_data with em_data on 'student id'
    merged_data = main_data.merge(em_data[['student id', 'em', 'phone number']], on="student id", how="left")
    return merged_data

# Function to display a welcome message for the teacher
def welcome_teacher(teacher_name):
    st.markdown(f"""
        <div style="background-color:#f9f9f9; padding:10px; border-radius:10px; margin-bottom:20px;">
            <h1 style="color:#4CAF50; text-align:center; font-family:Georgia; font-size:45px;">
                👩‍🏫 Welcome, {teacher_name}!
            </h1>
            <p style="text-align:center; color:#555; font-size:18px; font-family:Arial;">
                We're thrilled to have you here today! Let's dive into your teaching insights 📊.
            </p>
        </div>
    """, unsafe_allow_html=True)

# Main function to handle user role selection and page display
def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=170)
    st.title("Angle Belearn: Your Daily Class Insights")

    role = st.sidebar.radio("Select your role:", ["Select", "Student", "Teacher"], index=0)

    if st.sidebar.button("Refresh Data"):
        st.session_state.data = get_merged_data_with_em()
    
    if "data" not in st.session_state:
        st.session_state.data = get_merged_data_with_em()

    if role != "Select":
        manage_data(st.session_state.data, role)
    else:
        st.info("Please select a role from the sidebar.")

def manage_data(data, role):
    st.subheader(f"{role} Data")

    # Select month from 'mm' column
    if 'mm' in data.columns:
        month = st.sidebar.selectbox("Select Month", sorted(data["mm"].dropna().unique()))
    else:
        st.error("The 'mm' column is missing from the data, and month selection is unavailable.")
        return

    if role == "Student":
        with st.expander("Student Verification", expanded=True):
            student_id = st.text_input("Enter Student ID").strip().lower()
            student_name_part = st.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

            if st.button("Verify Student"):
                filtered_data = data[(data["mm"] == month) & 
                                     (data["student id"].str.lower().str.strip() == student_id) & 
                                     (data["student"].str.lower().str.contains(student_name_part))]
                
                if not filtered_data.empty:
                    show_filtered_data(filtered_data, role)
                else:
                    st.error("Verification failed. Please check your details.")

    elif role == "Teacher":
        with st.expander("Teacher Verification", expanded=True):
            teacher_id = st.text_input("Enter Teacher ID").strip().lower()
            teacher_name_part = st.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

            if st.button("Verify Teacher"):
                filtered_data = data[(data["mm"] == month) & 
                                     (data["teachers id"].str.lower().str.strip() == teacher_id) & 
                                     (data["teachers name"].str.lower().str.contains(teacher_name_part))]
                
                if not filtered_data.empty:
                    teacher_name = filtered_data["teachers name"].iloc[0]
                    welcome_teacher(teacher_name)
                    show_filtered_data(filtered_data, role)
                else:
                    st.error("Verification failed. Please check your details.")

if __name__ == "__main__":
    main()
