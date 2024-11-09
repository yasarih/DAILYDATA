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

# Load credentials from Streamlit secrets
def load_credentials():
    try:
        # Load and parse the JSON data from the 'data' field in secrets
        credentials_info = json.loads(st.secrets["google_credentials_new_project"]["data"])

        # Define scopes and create the credentials object
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(credentials_info, scopes=scopes)

        # Authorize the client with gspread
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Error loading credentials: {e}")
        return None

# Fetch data from a Google Sheet without a timeout parameter
def fetch_data_from_sheet(spreadsheet_id, worksheet_name):
    client = load_credentials()
    if not client:
        return pd.DataFrame()
    try:
        sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
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
    except Exception as e:
        st.error(f"Error fetching data from '{worksheet_name}': {e}")
        return pd.DataFrame()

# Function to merge student and EM data
def get_merged_data_with_em():
    main_data = fetch_data_from_sheet("17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y", "Student class details")
    em_data = fetch_data_from_sheet("17_Slyn6u0G6oHSzzXIpuuxPhzxx4ayOKYkXfQTLtk-Y", "Student Data")

    main_data = main_data.rename(columns={'Student id': 'Student ID'})
    em_data = em_data.rename(columns={'Student id': 'Student ID', 'EM': 'EM', 'EM Phone': 'Phone Number'})

    # Merge on Student ID to get EM details
    merged_data = main_data.merge(em_data[['Student ID', 'EM', 'Phone Number']], on="Student ID", how="left")
    return merged_data

# Function to show student EM data with phone numbers
def show_student_em_table(data, teacher_name):
    required_columns = ["Student ID", "Teachers Name", "EM", "Phone Number"]

    # Check if required columns are present
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        st.error(f"The following required columns are missing from the data: {', '.join(missing_columns)}")
        return  # Exit the function if required columns are missing

    student_em_table = data[data["Teachers Name"] == teacher_name][["Student ID", "Student", "EM", "Phone Number"]].drop_duplicates()
    st.subheader("List of Students with Corresponding EM and EM's Phone Number")
    st.write(student_em_table)

# Optimized function to display filtered data based on the role (Student or Teacher)
def show_filtered_data(filtered_data, role):
    if role == "Student":
        required_columns = ["Date", "Subject", "Chapter taken", "Teachers Name", "Hr", "Type of class"]
    else:  # role == "Teacher"
        required_columns = ["Date", "Student ID", "Student", "Class", "Syllabus", "Type of class", "Hr"]

    # Check if required columns are present
    missing_columns = [col for col in required_columns if col not in filtered_data.columns]
    if missing_columns:
        st.error(f"The following required columns are missing from the data: {', '.join(missing_columns)}")
        return

    # Filter data based on role and display
    if role == "Student":
        filtered_data = filtered_data[required_columns]
        total_hours = filtered_data["Hr"].sum()
        st.write(f"**Total Hours of Classes:** {total_hours:.2f}")
        st.write(filtered_data)

    elif role == "Teacher":
        filtered_data = filtered_data[required_columns]
        total_hours = filtered_data["Hr"].sum()
        st.write(f"**Total Hours:** {total_hours:.2f}")
        st.write(filtered_data)

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

# Main function to handle user role selection and page display
def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=170)
    st.title("Angle Belearn: Your Daily Class Insights")

    if "data" not in st.session_state:
        st.session_state.data = get_merged_data_with_em()

    role = st.sidebar.radio("Select your role:", ["Select", "Student", "Teacher"], index=0)

    if st.sidebar.button("Refresh Data"):
        st.session_state.data = get_merged_data_with_em()

    if role != "Select":
        manage_data(st.session_state.data, role)
    else:
        st.info("Please select a role from the sidebar.")

def manage_data(data, role):
    st.subheader(f"{role} Data")
    if "MM" in data.columns:
        month = st.sidebar.selectbox("Select Month", sorted(data["MM"].unique()))
    else:
        st.warning("Month data ('MM' column) not found.")
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

if __name__ == "__main__":
    main()
