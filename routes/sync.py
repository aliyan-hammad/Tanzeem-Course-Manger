import threading
from flask import Blueprint, request, jsonify
from google_sync import sync_daily_coordinator_report
from datetime import date

sync_bp = Blueprint('sync_bp', __name__)

def run_in_background(func, *args, **kwargs):
    thread = threading.Thread(target=func, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()

@sync_bp.route('/dashboard/sync_sheets', methods=['POST'])
def sync_dashboard_sheets():
    data = request.json
    today_absentees = data.get('today', [])
    yesterday_absentees = data.get('yesterday', [])
    consecutive_absentees = data.get('consecutive', [])
    low_attendance = data.get('low', [])
    
    date_str = date.today().strftime('%Y-%m-%d')
    
    def do_sync():
        try:
            sync_daily_coordinator_report(date_str, today_absentees, yesterday_absentees, consecutive_absentees, low_attendance)
        except Exception as e:
            print(f"Error syncing coordinator dashboard: {e}")
            
    run_in_background(do_sync)
    return jsonify({"status": "success", "message": "Sync started in background."})
