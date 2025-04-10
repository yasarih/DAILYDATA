import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
import json


# Set page layout and title
st.set_page_config(
    page_title="Angle Belearn Insights",
    page_icon="🎓",
    layout="wide",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": None
    }
)

# Function to load credentials from Streamlit secrets for the new project
def load_credentials_from_secrets():
    try:
        credentials_info = dict(st.secrets["google_credentials_new_project"])
        print("ccccccccccccccccc",credentials_info)
        # credentials_info1 = json.loads(st.secrets["google_credentials_new_project"]["data"])
        # print("ccccccccccc2",credentials_info1)
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
        st.write("client",client)
        sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
        print("sheet",sheet)
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

# Function to merge student and EM data, including "Supalearn Password" from main sheet
def get_merged_data_with_em():
    main_data = fetch_data_from_sheet("1c6Nybs4I08MYoyv4b9Cv8uqqkR365gU4ppsHa6qgYOk", "test")

    # main_data = fetch_data_from_sheet("1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4", "Student class details")
    em_data = fetch_data_from_sheet("1v3vnUaTrKpbozrE1sZ7K5a-HtEttOPjMQDt4Z_Fivb4", "Student Data")

    if main_data.empty:
        st.warning("Main data is empty. Please check the 'Student class details' sheet.")
    if em_data.empty:
        st.warning("EM data is empty. Please check the 'Student Data' sheet.")
    if main_data.empty or em_data.empty:
        return pd.DataFrame()

    main_data = main_data.rename(columns={'Student id': 'Student ID'})
    em_data = em_data.rename(columns={'Student id': 'Student ID', 'EM': 'EM', 'EM Phone': 'Phone Number'})

    # Merge data including the "Supalearn Password" from the main sheet
    merged_data = main_data.merge(em_data[['Student ID', 'EM', 'Phone Number']], on="Student ID", how="left")
    merged_data = merged_data.merge(main_data[['Student ID', 'Supalearn Password']], on="Student ID", how="left")

    return merged_data

# Function to show student EM data with phone numbers and Supalearn Password for Teacher
def show_student_em_table(data, teacher_name, role):
    """
    Display a unique list of students taken by the logged-in teacher, 
    showing their ID, name, EM, and EM's phone number.
    Args:
    - data: Merged DataFrame containing student and EM details.
    - teacher_name: Name of the logged-in teacher.
    - role: Role of the logged-in user ('Teacher' or 'Student').
    """
    st.subheader(f"Unique List of Students for Teacher: {teacher_name}")

    # Check if required columns exist in the data
    required_columns = {"Student ID", "Student", "EM", "Phone Number", "Teachers Name"}
    if not required_columns.issubset(data.columns):
        st.error(f"Missing columns in the data. Expected: {required_columns}.")
        return

    # Filter data for the logged-in teacher
    teacher_students = data[data["Teachers Name"].str.lower() == teacher_name.lower()]

    if teacher_students.empty:
        st.warning("No students found for the logged-in teacher.")
        return

    # Remove duplicate students
    teacher_students = teacher_students.drop_duplicates(subset=["Student ID", "Student"])

    # Select relevant columns for display
    display_columns = ["Student ID", "Student", "EM", "Phone Number"]
    
    # Add "Supalearn Password" if the role is Teacher
    if role == "Teacher":
        display_columns.append("Supalearn Password")
    
    teacher_students = teacher_students[display_columns]

    # Display the unique list of students
    st.write(teacher_students)

    # Display suMMary stats
    st.write(f"**Total Unique Students:** {len(teacher_students)}")

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
def highlight_duplicates_html(df, subset_columns):
    # Identify duplicate rows based on specified columns
    df['is_duplicate'] = df.duplicated(subset=subset_columns, keep=False)

    # Start building an HTML table with conditional cell styling
    styled_table = "<style> .highlight-cell { background-color: red; color: white; } </style>"
    styled_table += '<table border="1" class="dataframe">'

    # Add table headers
    styled_table += '<thead><tr style="text-align: right;">'
    for column in df.columns:
        if column != 'is_duplicate':  # Exclude helper column
            styled_table += f'<th>{column}</th>'
    styled_table += '</tr></thead>'

    # Add table rows with conditional cell highlighting
    styled_table += '<tbody>'
    for _, row in df.iterrows():
        styled_table += '<tr>'
        for col in df.columns:
            if col != 'is_duplicate':  # Exclude helper column
                cell_value = row[col]
                # Apply red background if the row is marked as duplicate
                cell_class = 'highlight-cell' if row['is_duplicate'] else ''
                styled_table += f'<td class="{cell_class}">{cell_value}</td>'
        styled_table += '</tr>'
    styled_table += '</tbody></table>'

    return styled_table

# Example usage inside the show_filtered_data function
# Function to display filtered data based on the role (Student or Teacher)
def show_filtered_data(filtered_data, role, data, teacher_name):
    if role == "Teacher":
        # Select relevant columns for display
        filtered_data = filtered_data[["Date", "Student ID", "Student", "Class", "Syllabus", "Type of class", "Hr"]]
        filtered_data["Hr"] = filtered_data["Hr"]

        # Apply row highlighting for duplicates in "Date" and "Student ID" columns
        if "Date" in filtered_data.columns and "Student ID" in filtered_data.columns:
            filtered_data['Duplicate'] = filtered_data.duplicated(subset=["Date", "Student ID"], keep=False)
        else:
            st.error("Required columns 'Date' or 'Student ID' not found in the data.")
            return

        # Generate HTML with highlighting and display in Streamlit
        styled_table_html = highlight_duplicates_html(filtered_data, subset_columns=["Date", "Student ID"])

        st.subheader("Daily Class Data")
        st.markdown(styled_table_html, unsafe_allow_html=True)

        # Drop the 'Duplicate' column safely if it exists
        filtered_data = filtered_data.drop(columns=['Duplicate'], errors='ignore')

        # Calculate and display salary
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
        show_student_em_table(data, teacher_name, role)

# Function to show teacher's weekly schedule from the schedule sheet
def show_teacher_schedule(teacher_id):
    st.subheader("Your Weekly Schedule")
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    schedule_data = pd.DataFrame()

    for day in days:
        try:
            day_data = fetch_data_from_sheet("1RTJrYtD0Fo4GlLyZ2ds7M_1jnQJPk1cpeAvtsTwttdU", day)
            if day_data.empty or not {"Teacher ID", "Time Slot", "Student ID", "Status"}.issubset(day_data.columns):
                st.warning(f"Missing columns in {day} sheet. Expected columns: Teacher ID, Time Slot, Student ID, Status")
                continue

            # Filter by the specified teacher ID and active status
            day_data = day_data[(day_data['Teacher ID'].str.lower().str.strip() == teacher_id) & (day_data['Status'].str.lower() == 'active')]
            day_data['Day'] = day
            schedule_data = pd.concat([schedule_data, day_data], ignore_index=True)
        except Exception as e:
            st.error(f"Error loading {day} schedule: {e}")

    if not schedule_data.empty:
        # Combine duplicate entries by concatenating 'Student ID' with a coMMa separator
        schedule_data = schedule_data.groupby(['Time Slot', 'Day'])['Student ID'].apply(lambda x: ', '.join(x)).reset_index()

        # Perform pivot operation after handling duplicates
        schedule_pivot = schedule_data.pivot(index="Time Slot", columns="Day", values="Student ID").reindex(columns=days)
        st.write(schedule_pivot)
    else:
        st.write("No active schedule found for this teacher.")

# Function to manage data based on the selected role
def manage_data(data, role):
    st.subheader(f"{role} Data")
    print("role",role,data)
    st.write(data)
    st.write(role)

    if "MM" in data.columns:
        month = st.sidebar.selectbox("Select Month", sorted(data["MM"].unique()))
        year = st.sidebar.selectbox("Select Year", sorted(data["Year"].unique()))
    else:
        st.warning("Month data ('MM' column) not found. Available columns are:")
        st.write(data.columns.tolist())
        return

    if role == "Teacher":
        if "Teachers ID" not in data.columns:
            st.error("The column 'Teacher ID' is missing from the data. Please check the source sheet.")
            return

        teacher_id = st.text_input("Enter Your Teacher ID").strip().lower()
        teacher_name_part = st.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

        if st.button("Verify Teacher"):
            filtered_data = data[
                (data["MM"] == month) & 
                (data["Year"] == year) &  # Added condition to filter by year
                (data["Teachers ID"].str.lower().str.strip() == teacher_id) &
                (data["Teachers Name"].str.lower().str.contains(teacher_name_part))
            ]

            if not filtered_data.empty:
                teacher_name = filtered_data["Teachers Name"].iloc[0]
                # Fetch the Supalearn Password for the teacher
                supalearn_password = filtered_data["Supalearn Password"].iloc[0]

                # Display the welcome message along with Supalearn Password
                st.subheader(f"👩‍🏫 Welcome, {teacher_name}!")
                st.write(f"Your Supalearn Password is: **{supalearn_password}**")

                required_columns = ["Date", "Student ID", "Student", "Class", "Syllabus", "Type of class", "Hr"]
                missing_columns = [col for col in required_columns if col not in filtered_data.columns]

                if missing_columns:
                    st.error(f"The following required columns are missing: {missing_columns}")
                else:
                    show_filtered_data(filtered_data, role, data, teacher_name)

                    if teacher_id:
                        show_teacher_schedule(teacher_id)
            else:
                st.error("Verification failed. Please check your Teacher ID and name.")

    elif role == "Student":
        student_id = st.text_input("Enter Student ID").strip().lower()
        student_name_part = st.text_input("Enter any part of your name (minimum 4 characters)").strip().lower()

        if st.button("Verify Student"):
            filtered_data = data[(data["MM"] == month) &
                                 (data["Student ID"].str.lower().str.strip() == student_id) &
                                 (data["Student"].str.lower().str.contains(student_name_part))]

            if not filtered_data.empty:
                # Display student's name at the top
                student_name = filtered_data["Student"].iloc[0]
                st.subheader(f"👨‍🎓 Welcome, {student_name}!")

                required_columns = ["Date", "Subject", "Hr", "Teachers Name", "Chapter taken", "Type of class"]
                missing_columns = [col for col in required_columns if col not in filtered_data.columns]

                if missing_columns:
                    st.error(f"The following required columns are missing: {missing_columns}")
                    st.write("Available columns in filtered_data:", filtered_data.columns.tolist())
                else:
                    # Select relevant columns for display
                    filtered_data = filtered_data[required_columns]
                    st.subheader("📚 Your Monthly Class Data")
                    st.write(filtered_data)

                    # Calculate total hours
                    total_hours = filtered_data["Hr"].sum()
                    st.write(f"**Total Hours for {month}th month :** {total_hours:.2f}")

                    # Subject-wise breakdown
                    subject_hours = filtered_data.groupby("Subject")["Hr"].sum().reset_index()
                    subject_hours = subject_hours.rename(columns={"Hr": "Total Hours"})
                    st.subheader("📊 Subject-wise Hour Breakdown")
                    st.write(subject_hours)

            else:
                st.error("Verification failed. Please check your details.")

# Main function to handle user role selection and page display
def main():
    st.image("https://anglebelearn.kayool.com/assets/logo/angle_170x50.png", width=250)
    st.title("Angle Belearn: Your Daily Class Insights")

    # Refresh Data button in the sidebar
    if st.sidebar.button("Refresh Data"):
        # Clear cached data if it exists to ensure a fresh fetch
        st.session_state.data = get_merged_data_with_em()  # Forcefully reload data from Google Sheets
        st.success("Data refreshed successfully!")

    # Load data if it is not already in session state
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
