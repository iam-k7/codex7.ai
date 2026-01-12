import json
import datetime
from sheets_service import SheetsDB, JSONDB
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
# JSON_DB_PATH not needed if using JSONDB class

def sync_json_to_google_sheet():
    db = SheetsDB()
    local_db = JSONDB()

    if not db.spreadsheet:
        print("Google Sheet not connected")
        return

    data = local_db._read_db()

    # ---------------- USERS ----------------
    users = data.get("users", [])
    for user in users:
        result = db.store_user({
            "name": user.get("name"),
            "user_id": user.get("user_id"),
            "email": user.get("gmail"),
            "country": user.get("country"),
            "created_at": user.get("created_at")
        })
        print(f"User {user.get('gmail')} → {result}")

    # ---------------- FEEDBACK ----------------
    feedbacks = data.get("feedbacks", [])
    for fb in feedbacks:
        db.store_feedback({
            "user_id": fb.get("email"),
            "email": fb.get("gmail"),
            "rating": fb.get("rating"),
            "message": fb.get("message"),
            "feature": fb.get("feature"),
            "language": fb.get("language")
        })
        print(f"Feedback saved for {fb.get('gmail')}")

    print("JSON data synced to Google Sheets")

if __name__ == "__main__":
    sync_json_to_google_sheet()
