import os
import json
import gspread
import datetime
from pathlib import Path
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

# --- Environment Configuration ---
_backend_dir = Path(__file__).resolve().parent
_env_locations = [
    _backend_dir / ".env",          # Preferred: backend folder
    _backend_dir.parent / ".env"   # Fallback: project root
]

_env_loaded = False
for loc in _env_locations:
    if loc.exists():
        load_dotenv(loc, override=True)
        _env_loaded = True
        break

# ===================== GOOGLE SHEETS DB =====================

class SheetsDB:
    def __init__(self):
        self.scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        creds_path = os.getenv(
            "GOOGLE_SHEETS_CREDS_PATH",
            "/etc/secrets/credentials.json"
        )

        creds_path = Path(creds_path) 

        if not creds_path.exists():
            raise FileNotFoundError(f"Credentials not found at {creds_path}")


        self.client = None
        self.spreadsheet = None
        self.user_sheet = None
        self.feedback_sheet = None
        self._connected = False

        self._connect()

    def _connect(self):
        """Standardized connection logic with graceful fallback"""
        try:
            if not self.creds_path.exists():
                raise FileNotFoundError(f"Credentials not found at {self.creds_path}")

            creds = ServiceAccountCredentials.from_json_keyfile_name(
                str(self.creds_path), self.scope
            )
            self.client = gspread.authorize(creds)

            sheet_id = os.getenv("GOOGLE_SHEET_ID")
            if not sheet_id:
                raise ValueError("GOOGLE_SHEET_ID not set in environment.")

            self.spreadsheet = self.client.open_by_key(sheet_id)
            self._ensure_sheets_exist()
            self._connected = True
            print(f"Connected to Google Sheets: {self.spreadsheet.title}")
            
        except Exception as e:
            self._connected = False
            print(f"Google Sheets connection failed: {e}")
            print("Falling back to local storage only.")

    def is_connected(self):
        return self._connected and self.spreadsheet is not None

    def _ensure_sheets_exist(self):
        """Creates worksheets if they don't exist"""
        if not self.spreadsheet:
            return

        # --- User_Data ---
        try:
            self.user_sheet = self.spreadsheet.worksheet("User_Data")
        except gspread.WorksheetNotFound:
            self.user_sheet = self.spreadsheet.add_worksheet(
                title="User_Data", rows=1000, cols=10
            )
            self.user_sheet.append_row(["User ID", "Name", "Email", "Country", "Timestamp"])

        # --- User_Feedback ---
        try:
            self.feedback_sheet = self.spreadsheet.worksheet("User_Feedback")
        except gspread.WorksheetNotFound:
            self.feedback_sheet = self.spreadsheet.add_worksheet(
                title="User_Feedback", rows=1000, cols=10
            )
            self.feedback_sheet.append_row(
                ["User ID", "Email", "Rating", "Feedback", "Feature", "Language", "Timestamp"]
            )

    # ---------------- USERS ----------------
    def store_user(self, user_data):
        """Updates or creates a user row in Google Sheets"""
        if not self.is_connected():
            return False

        try:
            email = user_data.get("email")
            if not email: return False

            name = user_data.get("name", "")
            country = user_data.get("country", "")
            user_id = user_data.get("user_id", "")
            timestamp = user_data.get("created_at") or datetime.datetime.now().isoformat()

            # Search only in email column (Column C)
            emails = self.user_sheet.col_values(3)

            if email in emails:
                row = emails.index(email) + 1
                self.user_sheet.update(
                    f"A{row}:E{row}",
                    [[user_id, name, email, country, timestamp]]
                )
                print(f"Updated user in sheet: {email}")
                return "updated"
            else:
                self.user_sheet.append_row([user_id, name, email, country, timestamp])
                print(f"Created new user in sheet: {email}")
                return "created"
                
        except Exception as e:
            print(f"Error storing user to Sheets: {e}")
            return False

    # ---------------- FEEDBACK ----------------
    def store_feedback(self, feedback_data):
        """Appends a feedback entry to Google Sheets"""
        if not self.is_connected():
            return False

        try:
            timestamp = datetime.datetime.now().isoformat()
            self.feedback_sheet.append_row([
                feedback_data.get("user_id", "Anonymous"),
                feedback_data.get("email", ""),
                feedback_data.get("rating"),
                feedback_data.get("message"),
                feedback_data.get("feature", ""),
                feedback_data.get("language", "en"),
                timestamp
            ])
            print(f"Feedback stored for {feedback_data.get('email', 'Anonymous')}")
            return True
        except Exception as e:
            print(f"Error storing feedback: {e}")
            return False

    def get_user_by_email(self, email):
        """Helper for main app lookup"""
        if not self.is_connected(): return None
        try:
            emails = self.user_sheet.col_values(3)
            if email in emails:
                row_idx = emails.index(email) + 1
                row = self.user_sheet.row_values(row_idx)
                if len(row) >= 3:
                    return {
                        "user_id": row[0],
                        "name": row[1],
                        "email": row[2],
                        "country": row[3] if len(row) > 3 else "",
                    }
            return None
        except Exception:
            return None


# ===================== LOCAL JSON DB =====================

class JSONDB:
    def __init__(self):
        self.db_path = _backend_dir.parent / "datastore" / "mock_db.json"
        # Accessing datastore outside backend folder for security
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self):
        if not self.db_path.exists():
            return {"users": [], "feedbacks": [], "history": []}
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"users": [], "feedbacks": [], "history": []}

    def store_user(self, user_data):
        data = self._read()
        email = user_data.get("email")
        if not email: return None

        # Check for existing user
        for u in data["users"]:
            if u.get("email", u.get("gmail")) == email:
                u.update({
                    "name": user_data.get("name"),
                    "country": user_data.get("country"),
                    "email": email
                })
                self._write(data)
                return {"action": "updated", "user_id": u["user_id"]}

        # New user
        user_id = str(len(data["users"]) + 1001)
        data["users"].append({
            "user_id": user_id,
            "name": user_data.get("name"),
            "email": email,
            "country": user_data.get("country"),
            "created_at": datetime.datetime.now().isoformat()
        })
        self._write(data)
        return {"action": "created", "user_id": user_id}

    def store_feedback(self, feedback_data):
        data = self._read()
        data["feedbacks"].append({
            **feedback_data,
            "timestamp": datetime.datetime.now().isoformat()
        })
        return self._write(data)

    def save_history(self, history_data):
        data = self._read()
        data["history"] = data.get("history", [])
        data["history"].append(history_data)
        return self._write(data)

    def get_user_history(self, user_id):
        data = self._read()
        return [h for h in data.get("history", []) if h.get("user_id") == user_id]

    def _write(self, data):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False
