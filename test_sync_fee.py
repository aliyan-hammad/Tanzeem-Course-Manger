from app import app
from google_sync import sync_entire_month_log
import gspread

with app.app_context():
    data_rows = [
        [1, 1, "Ali", "Course", 5000.0, "Cash", "June", "2026-06-30"],
        [2, 2, "Bob", "Course", 3000.0, "Bank", "June", "2026-06-30"]
    ]
    url = sync_entire_month_log("Fees", "Test_Month_Fees", data_rows)
    print("URL:", url)
