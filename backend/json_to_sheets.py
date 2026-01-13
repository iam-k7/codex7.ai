from backend.sheets_service import SheetsDB, JSONDB

def sync_json_to_google_sheet():
    """Manual trigger to sync local data to Google Sheets"""
    sheets = SheetsDB()
    local = JSONDB()

    if not sheets.is_connected():
        print("❌ Google Sheets connection required for sync.")
        return

    data = local._read()

    # -------- Sync Users --------
    for user in data.get("users", []):
        email = user.get("email", user.get("gmail"))
        result = sheets.store_user({
            "user_id": user.get("user_id"),
            "name": user.get("name"),
            "email": email,
            "country": user.get("country"),
            "created_at": user.get("created_at"),
        })
        print(f"User {email} → {result}")

    # -------- Sync Feedback --------
    for fb in data.get("feedbacks", []):
        email = fb.get("email", fb.get("gmail"))
        sheets.store_feedback({
            "user_id": fb.get("user_id", ""),
            "email": email,
            "rating": fb.get("rating"),
            "message": fb.get("message"),
            "feature": fb.get("feature", ""),
            "language": fb.get("language", "en"),
        })
        print(f"Feedback from {email} synced")

    print("\n✅ End-to-end sync completed.")

if __name__ == "__main__":
    sync_json_to_google_sheet()
