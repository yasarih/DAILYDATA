import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1CtmcRqCRReVh0xp-QCkuVzlPr7KDdEquGNevKOA1e4w"
WORKSHEET_NAME = "Student class details"

def load_credentials():
    """Load credentials from creds.json."""
    with open("creds.json") as f:
        return Credentials.from_service_account_info(json.load(f))

def test_google_sheets_connection(spreadsheet_id, worksheet_name):
    credentials = load_credentials()
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    data = sheet.get_all_values()
    if data:
        print("Data fetched successfully!")
        print("Headers:", data[0])
        print("First row of data:", data[1])
    else:
        print("No data found in the worksheet.")

# Run the test
test_google_sheets_connection(SPREADSHEET_ID, WORKSHEET_NAME)

