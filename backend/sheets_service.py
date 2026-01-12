import os
import json
import gspread
import datetime
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path


class SheetsDB:
    def __init__(self):
        # Modern & correct scopes
        self.scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        # credentials.json must be inside backend/
        self.creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")

        self.client = None
        self.spreadsheet = None
        self.SHEET_NAME = "codex7.ai"

        # Connect on init
        self._connect()

    def _connect(self):
        try:
            if not os.path.exists(self.creds_path):
                print(f"credentials.json not found at {self.creds_path}")
                return

            self.creds = ServiceAccountCredentials.from_json_keyfile_name(
                self.creds_path, self.scope
            )
            self.client = gspread.authorize(self.creds)

            # Open by Sheet ID (reliable)
            SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "18HDgCWNHOE1T24OZlIhY86kgymkicxa9tFU5rhpaOzo") # Fallback to default if not set
            if not SHEET_ID or "your_" in SHEET_ID:
                 print("WARNING: GOOGLE_SHEET_ID not set correctly in .env. Sheets integration may fail.")
            
            self.spreadsheet = self.client.open_by_key(SHEET_ID)

            self._ensure_sheets_exist()
            print("Successfully connected to Google Sheets")

        except Exception as e:
            print(f"Google Sheets Connection Error: {e}")

    def _ensure_sheets_exist(self):
        if not self.spreadsheet:
            return

        # ---------- User_Data ----------
        try:
            self.user_sheet = self.spreadsheet.worksheet("User_Data")
        except gspread.WorksheetNotFound:
            self.user_sheet = self.spreadsheet.add_worksheet(
                title="User_Data", rows=1000, cols=10
            )
            self.user_sheet.append_row(["Name", "Email", "Country", "Timestamp"])
            self.user_sheet.format("A1:D1", {"textFormat": {"bold": True}})

        # ---------- User_Feedback ----------
        try:
            self.feedback_sheet = self.spreadsheet.worksheet("User_Feedback")
        except gspread.WorksheetNotFound:
            self.feedback_sheet = self.spreadsheet.add_worksheet(
                title="User_Feedback", rows=1000, cols=10
            )
            self.feedback_sheet.append_row(
                [
                    "Name",
                    "Email",
                    "Rating",
                    "Feedback",
                    "Feature",
                    "Language",
                    "Timestamp",
                ]
            )
            self.feedback_sheet.format("A1:G1", {"textFormat": {"bold": True}})

    def store_user(self, user_data):
        if not self.client or not self.spreadsheet:
            print("No DB connection, skipping save.")
            return False

        try:
            email = user_data.get("email")
            if not email:
                print("Email missing, skipping user")
                return False

            name = user_data.get("name", "")
            country = user_data.get("country", "")
            timestamp = datetime.datetime.now().isoformat()

            try:
                # Try to find existing user
                cell = self.user_sheet.find(email)

                # Update row
                self.user_sheet.update(
                    f"A{cell.row}:D{cell.row}",
                    [[name, email, country, timestamp]],
                )

                print(f"Updated user: {email}")
                return "updated"

            except Exception:
                # Not found → append
                self.user_sheet.append_row([name, email, country, timestamp])

                print(f"Created user: {email}")
                return "created"

        except Exception as e:
            print(f"Error storing user: {e}")
            return False

    def store_feedback(self, feedback_data):
        if not self.client or not self.spreadsheet:
            return False

        try:
            timestamp = datetime.datetime.now().isoformat()

            self.feedback_sheet.append_row(
                [
                    feedback_data.get("user_id", "Anonymous"),
                    feedback_data.get("email", ""),
                    feedback_data.get("rating"),
                    feedback_data.get("message"),
                    feedback_data.get("feature", ""),
                    feedback_data.get("language", "en"),
                    timestamp,
                ]
            )

            return True

        except Exception as e:
            print(f"Error storing feedback: {e}")
            return False

    # ---------- Optional helpers ----------

    def get_user_by_email(self, email):
        if not self.spreadsheet:
            return None

        try:
            cell = self.user_sheet.find(email)
            row = self.user_sheet.row_values(cell.row)

            return {
                "name": row[0],
                "email": row[1],
                "country": row[2],
                "user_id": row[1],
            }

        except Exception:
            return None

    def add_user(self, user_data):
        self.store_user(user_data)

    def get_user_history(self, user_id):
        return []


class JSONDB:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.db_path = self.base_dir / "datastore" / "mock_db.json"
        
        # Ensure dir exists (file is created by cleanup/init usually, but good to have check)
        if not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_db(self):
        try:
            if not self.db_path.exists():
                return {"users": [], "feedbacks": [], "history": []}
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure all keys exist
                changed = False
                for key in ["users", "feedbacks", "history"]:
                    if key not in data:
                        data[key] = []
                        changed = True
                if changed:
                    self._write_db(data)
                return data
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error reading JSON DB (corrupt?), resetting: {e}")
            empty_db = {"users": [], "feedbacks": [], "history": []}
            self._write_db(empty_db)
            return empty_db
        except Exception as e:
            print(f"Error reading JSON DB: {e}")
            return {"users": [], "feedbacks": [], "history": []}

    def _write_db(self, data):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error writing to JSON DB: {e}")
            return False

    def store_user(self, user_data):
        data = self._read_db()
        email = user_data.get("email")
        if not email:
            return False

        existing_user = next((u for u in data["users"] if u.get("gmail") == email), None)
        
        timestamp = datetime.datetime.now().isoformat()
        new_user = {
            "user_id": user_data.get("user_id", str(os.urandom(8).hex())),
            "name": user_data.get("name"),
            "gmail": email,
            "country": user_data.get("country"),
            "created_at": timestamp
        }

        if existing_user:
            # Update existing
            for i, u in enumerate(data["users"]):
                if u.get("gmail") == email:
                    data["users"][i].update(new_user)
                    break
            action = "updated"
        else:
            data["users"].append(new_user)
            action = "created"
        
        self._write_db(data)
        return action

    def store_feedback(self, feedback_data):
        data = self._read_db()
        timestamp = datetime.datetime.now().isoformat()
        new_feedback = {
            "email": feedback_data.get("user_id", "anonymous"),
            "gmail": feedback_data.get("email", feedback_data.get("user_id")),
            "rating": feedback_data.get("rating"),
            "message": feedback_data.get("message"),
            "feature": feedback_data.get("feature", "Editor"),
            "language": feedback_data.get("language_pref", feedback_data.get("language", "en")),
            "timestamp": timestamp
        }
        data["feedbacks"].append(new_feedback)
        return self._write_db(data)

    def save_history(self, history_data):
        data = self._read_db()
        data["history"].append(history_data)
        return self._write_db(data)

    def get_user_history(self, user_id_or_email):
        data = self._read_db()
        return [h for h in data["history"] if h.get("user_id") == user_id_or_email or h.get("email") == user_id_or_email]
