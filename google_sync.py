import os
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Ensure we use absolute path for credentials
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')

# We will fill these in once we have both IDs
ADMIN_SPREADSHEET_ID = '1tWcgbHLmzQ9wWzGUkr9P4ANCxqjr0B3o-ecpfRYze34'
DAILY_SPREADSHEET_ID = '1VCvZXl-xTo1OEHb9uAMzbyeMgXWkQKM-rhdnmhGHVy8'

def get_gspread_client():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)

def get_or_create_worksheet(spreadsheet, title, headers=None):
    try:
        worksheet = spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=title, rows="100", cols="20")
        if headers:
            worksheet.append_row(headers)
    return worksheet

def sync_admin_master_students(students_data):
    gc = get_gspread_client()
    spreadsheet = gc.open_by_key(ADMIN_SPREADSHEET_ID)
    worksheet = get_or_create_worksheet(spreadsheet, "Master Students", ["ID", "Registration ID", "Full Name", "Father Name", "Course", "Phone", "Status", "Enrollment Date"])
    
    worksheet.clear()
    headers = ["ID", "Registration ID", "Full Name", "Father Name", "Course", "Phone", "Status", "Enrollment Date"]
    rows = [headers]
    for s in students_data:
        rows.append([s['id'], s['registration_id'], s['full_name'], s['father_name'], s['course'], s['phone'], s['status'], str(s['enrollment_date'])])
    
    worksheet.update('A1', rows)
    return spreadsheet.url

def append_to_monthly_log(log_type, month_year_str, data_row):
    """
    log_type: 'Fees', 'Expenses', 'Attendance'
    data_row: list of strings (the row to append)
    """
    gc = get_gspread_client()
    spreadsheet = gc.open_by_key(ADMIN_SPREADSHEET_ID)
    
    # E.g. "June 2026 Fees"
    tab_name = f"{month_year_str} {log_type}"
    
    headers = []
    if log_type == 'Fees':
        headers = ["Fee ID", "Student ID", "Student Name", "Course", "Amount Paid", "Payment Method", "Fee Month", "Date Collected"]
    elif log_type == 'Expenses':
        headers = ["Expense ID", "Title", "Amount", "Payment Method", "Course", "Expense Date"]
    elif log_type == 'Attendance':
        headers = ["Attendance ID", "Session ID", "Course", "Subject", "Session Date", "Student Name", "Status"]
        
    worksheet = get_or_create_worksheet(spreadsheet, tab_name, headers)
    worksheet.append_row(data_row)
    return spreadsheet.url

def sync_daily_coordinator_report(date_str, today_absentees, yesterdays_absentees, consec_absentees, low_att):
    gc = get_gspread_client()
    spreadsheet = gc.open_by_key(DAILY_SPREADSHEET_ID)
    
    # We prefix tabs with date so they don't overwrite each other if the user wants historical tracking
    # E.g. "2026-06-25 Today's Abs"
    
    # Today's Absentees
    ws_today = get_or_create_worksheet(spreadsheet, f"{date_str} Today's Abs")
    ws_today.clear()
    headers_today = ["Student Name", "Course", "Absence Type", "Missed Subjects", "Contact"]
    rows_today = [headers_today]
    for row in today_absentees:
        rows_today.append(row)
    ws_today.update('A1', rows_today)

    # Consecutive Absentees
    ws_consec = get_or_create_worksheet(spreadsheet, f"{date_str} Consec. Abs")
    ws_consec.clear()
    headers_consec = ["Student Name", "Registration ID", "Course", "Contact"]
    rows_consec = [headers_consec]
    for row in consec_absentees:
        rows_consec.append(row)
    ws_consec.update('A1', rows_consec)
    
    # Daily Sync now only pushes Today's Absentees and Consecutive Absentees
    
    # Remove default 'Sheet1' if it exists and is empty
    try:
        sheet1 = spreadsheet.worksheet("Sheet1")
        spreadsheet.del_worksheet(sheet1)
    except:
        pass
        
    return spreadsheet.url
