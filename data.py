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

# Function to load credentials from Streamlit secrets for the new project
def load_credentials_from_secrets():
    try:
        credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])
        return credentials_info
    except KeyError:
        st.error("Google credentials not found in Streamlit secrets.")
        return None

# Function to connect to Google Sheets using the credentials from secrets for the new project
def connect_to_google_sheets(spreadsheet_id, worksheet_name):
    credentials_info = load_credentials_from_secrets()
    if not credentials_info:
        return None
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ]
    
    try:
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=scopes
        )
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
        return sheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet with ID '{spreadsheet_id}' not found. Check the spreadsheet ID and permissions.")
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet '{worksheet_name}' not found in the spreadsheet. Verify the worksheet name.")
    except Exception as e:
        st.error(f"Unexpected error connecting to Google Sheets: {e}")
    return None
# Function to fetch all data without caching to always get updated values
def fetch_data_from_sheet(spreadsheet_id, worksheet_name):
    sheet = connect_to_google_sheets(spreadsheet_id, worksheet_name)
    if not sheet:
        st.warning(f"Could not establish a connection to the worksheet '{worksheet_name}'.")
        return pd.DataFrame()  # Return empty DataFrame if connection fails
    try:
        data = sheet.get_all_values()
        if data:
            headers = pd.Series(data[0]).fillna('').str.strip()
            headers = headers.where(headers != '', other='Unnamed')
            headers = headers + headers.groupby(headers).cumcount().astype(str).replace('0', '')
            df = pd.DataFrame(data[1:], columns=headers)
            df.replace('', pd.NA, inplace=True)
            df.ffill(inplace=True)
            if 'Hr' in df.columns:
                df['Hr'] = pd.to_numeric(df['Hr'], errors='coerce').fillna(0)
            return df
        else:
            st.warning(f"No data found in worksheet '{worksheet_name}'.")
            return pd.DataFrame()
    except gspread.exceptions.APIError as api_error:
        st.error(f"Google Sheets API error fetching data from '{worksheet_name}': {api_error}")
    except Exception as e:
        st.error(f"Error fetching data from '{worksheet_name}': {e}")
    return pd.DataFrame()

# Function to merge student and EM data
def get_merged_data_with_em():
    main_data = fetch_data_from_sheet("17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y", "Student class details")
    em_data = fetch_data_from_sheet("17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y", "Student Data")
    
    if main_data.empty:
        st.warning("Main data is empty. Please check the 'Student class details' sheet.")
    if em_data.empty:
        st.warning("EM data is empty. Please check the 'Student Data' sheet.")
    if main_data.empty or em_data.empty:
        return pd.DataFrame()

    main_data = main_data.rename(columns={'Student id': 'Student ID'})
    em_data = em_data.rename(columns={'Student id': 'Student ID', 'EM': 'EM', 'EM Phone': 'Phone Number'})

    merged_data = main_data.merge(em_data[['Student ID', 'EM', 'Phone Number']], on="Student ID", how="left")
    return merged_data

# Function to show student EM data with phone numbers
def show_student_em_table(data, teacher_name):
    st.subheader("List of Students with Corresponding EM and EM's Phone Number")
    if "Student" in data.columns:
        student_column = "Student"
    else:
        st.error("Student name column not found.")
        return

    student_em_table = data[data["Teachers Name"] == teacher_name][["Student ID", student_column, "EM", "Phone Number"]].drop_duplicates()
    st.write(student_em_table)

# Function to calculate salary
def calculate_salary(row):
    student_id = row['Student ID'].strip().lower()
    syllabus = row['Syllabus'].strip().lower()
    class_type = row['Type of class'].strip().lower()
    hours = row['Hr']

    if 'demo class i - x' in student_id:
        return hours * 150
    elif 'demo class xi - xii' in student_id:
        return hours * 180
    elif class_type.startswith("paid"):
        return hours * 4 * 100
    else:
        class_level = int(row['Class']) if row['Class'].isdigit() else None
        if syllabus in ['igcse', 'ib']:
            if class_level is not None:
                if 1 <= class_level <= 4:
                    return hours * 120
                elif 5 <= class_level <= 7:
                    return hours * 150
                elif 8 <= class_level <= 10:
                    return hours * 170
                elif 11 <= class_level <= 13:
                    return hours * 200
        else:
            if class_level is not None:
                if 1 <= class_level <= 4:
                    return hours * 120
                elif 5 <= class_level <= 10:
                    return hours * 150
                elif 11 <= class_level <= 12:
                    return hours * 180
    return 0
# Function to display filtered data based on the role (Student or Teacher)
def show_filtered_data(filtered_data, role):
    # Clean column names to ensure consistency
    filtered_data.columns = filtered_data.columns.str.strip()  # Remove any leading/trailing spaces

    # Define required columns for duplicate check and print available columns for debugging
    required_columns = ["Date", "Student ID", "Teachers Name"]
    st.write("Available columns in filtered data:", filtered_data.columns.tolist())  # Debugging line

    # Check for the required columns in the dataframe
    missing_columns = [col for col in required_columns if col not in filtered_data.columns]
    if missing_columns:
        st.error(f"Cannot perform duplicate check. Missing columns: {', '.join(missing_columns)}.")
        return  # Stop further processing if required columns are missing
    
    if role == "Student":
        filtered_data = filtered_data[["Date", "Subject", "Chapter taken", "Teachers Name", "Hr", "Type of class"]]
        filtered_data["Hr"] = filtered_data["Hr"].round(2)

        total_hours = filtered_data["Hr"].sum()
        st.write(f"**Total Hours of Classes:** {total_hours:.2f}")
        subject_hours = filtered_data.groupby("Subject")["Hr"].sum()
        st.write("**Subject-wise Hours:**")
        st.write(subject_hours)  
        st.write(filtered_data)

    elif role == "Teacher":
        filtered_data = filtered_data[["Date", "Student ID", "Student", "Class", "Syllabus", "Type of class", "Hr"]]
        filtered_data["Hr"] = filtered_data["Hr"].round(2)
        
        # Identify duplicate entries by teacher for a student on the same day
        try:
            filtered_data['Duplicate Entry'] = filtered_data.duplicated(subset=["Date", "Student ID", "Teachers Name"], keep=False)
        except KeyError as e:
            st.error(f"Error identifying duplicates: {e}")
            return  # Stop processing if there's a KeyError

        st.subheader("Daily Class Data (Duplicates Highlighted)")
        st.write(filtered_data.style.apply(lambda x: ['background-color: yellow' if x['Duplicate Entry'] else '' for i in x], axis=1))
        
        # Salary calculation and summary
        filtered_data['Salary'] = filtered_data.apply(calculate_salary, axis=1)
        total_salary = filtered_data['Salary'].sum()
        total_hours = filtered_data["Hr"].sum()
        st.write(f"**Total Hours:** {total_hours:.2f}")
        st.write(f"**Total Salary (_It is based on rough calculations and may change as a result._):** ₹{total_salary:.2f}")

        salary_split = filtered_data.groupby(['Class', 'Syllabus', 'Type of class']).agg({
            'Hr': 'sum', 'Salary': 'sum'
        }).reset_index()
        st.subheader("Salary Breakdown by Class and Board")
        st.write(salary_split)

# Function to show teacher's weekly schedule from the schedule sheet
def show_teacher_schedule(teacher_id):
    st.subheader("Your Weekly Schedule")
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    schedule_data = pd.DataFrame()

    for day in days:
        try:
            day_data = fetch_data_from_sheet("1RTJrYtD0Fo4GlLyZ2ds7M_1jnQJPk1cpeAvtsTwttdU", day)
            if day_data.empty or not {"Teacher ID", "Time Slot", "Student ID"}.issubset(day_data.columns):
                st.warning(f"Missing columns in {day} sheet. Expected columns: Teacher ID, Time Slot, Student ID")
                continue

            day_data = day_data[day_data['Teacher ID'].str.lower().str.strip() == teacher_id]
            day_data['Day'] = day
            schedule_data = pd.concat([schedule_data, day_data], ignore_index=True)
        except Exception as e:
            st.error(f"Error loading {day} schedule: {e}")

    if not schedule_data.empty:
        schedule_pivot = schedule_data.pivot(index="Time Slot", columns="Day", values="Student ID").reindex(columns=days)
        st.write(schedule_pivot)
    else:
        st.write("No schedule found for this teacher.")

# Function to manage data based on the selected role
def manage_data(data, role):
    st.subheader(f"{role} Data")
    #st.write("Available columns in data:", data.columns.tolist())  # Display columns in the data for debugging

    if "MM" in data.columns:
        month = st.sidebar.selectbox("Select Month", sorted(data["MM"].unique()))
    else:
        st.warning("Month data ('MM' column) not found. Available columns are:")
        st.write(data.columns.tolist())
        return

    if role == "Student":
        student_id = st.text_input("Enter Student ID").strip().lower()
        student_name_part = st.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

        if st.button("Verify Student"):
            filtered_data = data[(data["MM"] == month) & 
                                 (data["Student ID"].str.lower().str.strip() == student_id) & 
                                 (data["Student"].str.lower().str.contains(student_name_part))]
            
            if not filtered_data.empty:
                show_filtered_data(filtered_data, role)
            else:
                st.error("Verification failed. Please check your details.")

    elif role == "Teacher":
        teacher_id = st.text_input("Enter Teacher ID").strip().lower()
        teacher_name_part = st.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

        if st.button("Verify Teacher"):
            filtered_data = data[(data["MM"] == month) & 
                                 (data["Teachers ID"].str.lower().str.strip() == teacher_id) & 
                                 (data["Teachers Name"].str.lower().str.contains(teacher_name_part))]
            
            if not filtered_data.empty:
                teacher_name = filtered_data["Teachers Name"].iloc[0]
                st.subheader(f"👩‍🏫 Welcome, {teacher_name}!")
                
                # Show filtered data and other relevant details
                show_filtered_data(filtered_data, role)
                
                # Show EM data with phone numbers
                show_student_em_table(data, teacher_name)
                
                # Show teacher's weekly schedule
                show_teacher_schedule(teacher_id)
            else:
                st.error("Verification failed. Please check your details.")

# Main function to handle user role selection and page display
def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=170)
    st.title("Angle Belearn: Your Daily Class Insights")

    # Refresh button to force data update
    if st.sidebar.button("Refresh Data"):
        # Clear any existing data to force reload
        if "data" in st.session_state:
            del st.session_state["data"]

    # If no data is loaded or refresh button was clicked, fetch new data
    if "data" not in st.session_state:
        st.session_state.data = get_merged_data_with_em()

    # Role selection and data management
    role = st.sidebar.radio("Select your role:", ["Select", "Student", "Teacher"], index=0)

    if role != "Select":
        manage_data(st.session_state.data, role)
    else:
        st.info("Please select a role from the sidebar.")

if __name__ == "__main__":
    main()
