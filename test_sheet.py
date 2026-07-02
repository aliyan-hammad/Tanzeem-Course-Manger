import os
from google_sync import sync_entire_month_log
data_rows = [[1, 1, "Ali", "Course", 5000.0, "Cash", "June", "2026-06-30"]]
sync_entire_month_log("Fees", "Test_Month", data_rows)
print("Done")
