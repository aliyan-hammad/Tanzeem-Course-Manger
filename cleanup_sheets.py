import gspread
from app import create_app
from google_sync import get_gspread_client, ADMIN_SPREADSHEET_ID, DAILY_SPREADSHEET_ID

app = create_app()

def cleanup_sheets():
    with app.app_context():
        gc = get_gspread_client()
        
        # Admin Sheet Cleanup
        admin_sheet = gc.open_by_key(ADMIN_SPREADSHEET_ID)
        worksheets = admin_sheet.worksheets()
        for ws in worksheets:
            if "Attendance" in ws.title:
                print(f"Deleting Admin tab: {ws.title}")
                admin_sheet.del_worksheet(ws)
                
        # Daily Sheet Cleanup
        daily_sheet = gc.open_by_key(DAILY_SPREADSHEET_ID)
        worksheets = daily_sheet.worksheets()
        for ws in worksheets:
            if "Yest" in ws.title or "At Risk" in ws.title:
                print(f"Deleting Daily tab: {ws.title}")
                daily_sheet.del_worksheet(ws)
                
if __name__ == '__main__':
    cleanup_sheets()
