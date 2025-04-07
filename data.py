import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

def load_credentials_from_secrets():
    # Directly load the credentials from the secrets.toml file
    credentials_info = dict(st.secrets["google_credentials_new_project"])  # No need to use json.loads() now
    
    # Create credentials from the loaded info
    credentials = service_account.Credentials.from_service_account_info(credentials_info)
    
    return credentials

def connect_to_google_sheets(spreadsheet_id, worksheet_name):
    credentials = load_credentials_from_secrets()  # Load credentials
    
    # Build the service object using the loaded credentials
    service = build('sheets', 'v4', credentials=credentials)
    
    # Fetch the data from the specified worksheet
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=worksheet_name).execute()
    
    return result
