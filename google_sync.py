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

import json

# We will fill these in once we have both IDs
ADMIN_SPREADSHEET_ID = '1tWcgbHLmzQ9wWzGUkr9P4ANCxqjr0B3o-ecpfRYze34'
DAILY_SPREADSHEET_ID = '1VCvZXl-xTo1OEHb9uAMzbyeMgXWkQKM-rhdnmhGHVy8'
def get_gspread_client():
    import base64
    env_creds = os.environ.get('GOOGLE_CREDENTIALS')
    if env_creds:
        # If it doesn't look like JSON, assume it is Base64 encoded to bypass Vercel newline mangling
        if not env_creds.strip().startswith('{'):
            try:
                env_creds = base64.b64decode(env_creds).decode('utf-8')
            except Exception:
                pass

        creds_dict = json.loads(env_creds, strict=False)
        if 'private_key' in creds_dict:
            # Vercel/Copy-Paste often mangles PEM keys by adding leading spaces or double-escaping newlines.
            key = creds_dict['private_key']
            key = key.replace('\\n', '\n')
            # Clean all leading/trailing whitespace on every line to prevent MalformedFraming errors
            creds_dict['private_key'] = '\n'.join(line.strip() for line in key.split('\n'))
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)

def get_or_create_worksheet(spreadsheet, title, headers=None, summary_formula=None):
    try:
        worksheet = spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=title, rows="100", cols="20")
        if headers:
            if summary_formula:
                rows = [[summary_formula] + [""] * (len(headers)-1), headers]
                worksheet.update('A1', rows, value_input_option='USER_ENTERED')
                try:
                    worksheet.format('A1:J1', {'textFormat': {'bold': True, 'fontSize': 14}, 'backgroundColor': {'red': 0.9, 'green': 0.95, 'blue': 1.0}})
                    worksheet.format('A2:J2', {'textFormat': {'bold': True, 'fontSize': 11}, 'backgroundColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95}})
                    worksheet.freeze(rows=2)
                except Exception:
                    pass
            else:
                worksheet.append_row(headers)
    return worksheet

def sync_admin_master_students(students_data):
    gc = get_gspread_client()
    spreadsheet = gc.open_by_key(ADMIN_SPREADSHEET_ID)
    
    headers = ["ID", "Registration ID", "Full Name", "Father Name", "Course", "Phone", "Status", "Enrollment Date"]
    summary = '="TOTAL STUDENTS: " & COUNTA(A3:A)'
    worksheet = get_or_create_worksheet(spreadsheet, "Master Students", headers, summary)
    
    worksheet.clear()
    rows = [[summary] + [""] * (len(headers)-1), headers]
    for s in students_data:
        rows.append([s['id'], s['registration_id'], s['full_name'], s['father_name'], s['course'], s['phone'], s['status'], str(s['enrollment_date'])])
    
    worksheet.update('A1', rows, value_input_option='USER_ENTERED')
    try:
        worksheet.format('A1:H1', {'textFormat': {'bold': True, 'fontSize': 14}, 'backgroundColor': {'red': 0.9, 'green': 0.95, 'blue': 1.0}})
        worksheet.format('A2:H2', {'textFormat': {'bold': True, 'fontSize': 11}, 'backgroundColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95}})
        worksheet.freeze(rows=2)
    except Exception:
        pass
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
    summary_formula = None
    if log_type == 'Fees':
        headers = ["Fee ID", "Student ID", "Student Name", "Course", "Amount Paid", "Payment Method", "Fee Month", "Date Collected"]
        summary_formula = '="TOTAL COLLECTION: Rs. " & SUM(E3:E)'
    elif log_type == 'Expenses':
        headers = ["Expense ID", "Title", "Amount", "Payment Method", "Course", "Expense Date"]
        summary_formula = '="TOTAL EXPENSES: Rs. " & SUM(C3:C)'
    elif log_type == 'Attendance':
        headers = ["Attendance ID", "Session ID", "Course", "Subject", "Session Date", "Student Name", "Status"]
        summary_formula = '="TOTAL STUDENTS: " & COUNTA(A3:A)'
        
    worksheet = get_or_create_worksheet(spreadsheet, tab_name, headers, summary_formula)
    worksheet.append_row(data_row, value_input_option='USER_ENTERED')
    return spreadsheet.url

def sync_daily_coordinator_report(date_str, today_absentees, yesterdays_absentees, consec_absentees, low_att):
    gc = get_gspread_client()
    spreadsheet = gc.open_by_key(DAILY_SPREADSHEET_ID)
    
    # We prefix tabs with date so they don't overwrite each other if the user wants historical tracking
    # E.g. "2026-06-25 Today's Abs"
    
    # Today's Absentees
    headers_today = ["Student Name", "Course", "Absence Type", "Missed Subjects", "Contact"]
    summary_today = '="TOTAL STUDENTS: " & COUNTA(A3:A)'
    ws_today = get_or_create_worksheet(spreadsheet, f"{date_str} Today's Abs", headers_today, summary_today)
    ws_today.clear()
    
    rows_today = [[summary_today] + [""] * (len(headers_today)-1), headers_today]
    for row in today_absentees:
        rows_today.append(row)
    ws_today.update('A1', rows_today, value_input_option='USER_ENTERED')
    try:
        ws_today.format('A1:E1', {'textFormat': {'bold': True, 'fontSize': 14}, 'backgroundColor': {'red': 0.9, 'green': 0.95, 'blue': 1.0}})
        ws_today.format('A2:E2', {'textFormat': {'bold': True, 'fontSize': 11}, 'backgroundColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95}})
        ws_today.freeze(rows=2)
    except Exception:
        pass

    # Consecutive Absentees
    headers_consec = ["Student Name", "Registration ID", "Course", "Contact"]
    summary_consec = '="TOTAL STUDENTS: " & COUNTA(A3:A)'
    ws_consec = get_or_create_worksheet(spreadsheet, f"{date_str} Consec. Abs", headers_consec, summary_consec)
    ws_consec.clear()
    
    rows_consec = [[summary_consec] + [""] * (len(headers_consec)-1), headers_consec]
    for row in consec_absentees:
        rows_consec.append(row)
    ws_consec.update('A1', rows_consec, value_input_option='USER_ENTERED')
    try:
        ws_consec.format('A1:D1', {'textFormat': {'bold': True, 'fontSize': 14}, 'backgroundColor': {'red': 0.9, 'green': 0.95, 'blue': 1.0}})
        ws_consec.format('A2:D2', {'textFormat': {'bold': True, 'fontSize': 11}, 'backgroundColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95}})
        ws_consec.freeze(rows=2)
    except Exception:
        pass
    
    # Daily Sync now only pushes Today's Absentees and Consecutive Absentees
    
    # Remove default 'Sheet1' if it exists and is empty
    try:
        sheet1 = spreadsheet.worksheet("Sheet1")
        spreadsheet.del_worksheet(sheet1)
    except:
        pass
        
    return spreadsheet.url

def sync_entire_month_log(log_type, month_year_str, data_rows):
    """
    Overwrites the entire monthly tab for the given log_type.
    data_rows: list of lists (headers not included, we add them)
    """
    gc = get_gspread_client()
    spreadsheet = gc.open_by_key(ADMIN_SPREADSHEET_ID)
    
    tab_name = f"{month_year_str} {log_type}"
    
    headers = []
    summary = None
    if log_type == 'Fees':
        headers = ["Fee ID", "Student ID", "Student Name", "Course", "Amount Paid", "Payment Method", "Fee Month", "Date Collected"]
        summary = '="TOTAL COLLECTION: Rs. " & SUM(E3:E)'
    elif log_type == 'Expenses':
        headers = ["Expense ID", "Title", "Amount", "Payment Method", "Course", "Expense Date"]
        summary = '="TOTAL EXPENSES: Rs. " & SUM(C3:C)'
        
    worksheet = get_or_create_worksheet(spreadsheet, tab_name, headers, summary)
    
    worksheet.clear()
    rows = [[summary] + [""] * (len(headers)-1), headers] + data_rows
    worksheet.update('A1', rows, value_input_option='USER_ENTERED')
    
    try:
        worksheet.format('A1:J1', {'textFormat': {'bold': True, 'fontSize': 14}, 'backgroundColor': {'red': 0.9, 'green': 0.95, 'blue': 1.0}})
        worksheet.format('A2:J2', {'textFormat': {'bold': True, 'fontSize': 11}, 'backgroundColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95}})
        worksheet.freeze(rows=2)
    except Exception:
        pass
        
    return spreadsheet.url
