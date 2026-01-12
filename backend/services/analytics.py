import os
import json
import asyncio
import datetime
from typing import Optional, Dict, Any
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path

class AnalyticsService:
    def __init__(self):
        self.scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.creds_path = os.getenv("GOOGLE_SHEETS_CREDS_PATH", "credentials.json")
        self.sheet_id = os.getenv("GOOGLE_SHEETS_ID")
        self.client = None
        self.sheet = None
        
        # Local fallback path
        self.fallback_path = Path("datastore/analytics_fallback.json")
        if not self.fallback_path.exists():
            self.fallback_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.fallback_path, "w") as f:
                json.dump([], f)

        self._initialize_client()

    def _initialize_client(self):
        try:
            if os.path.exists(self.creds_path):
                self.creds = ServiceAccountCredentials.from_json_keyfile_name(self.creds_path, self.scope)
                self.client = gspread.authorize(self.creds)
                
                if self.sheet_id:
                    self.sheet = self.client.open_by_key(self.sheet_id).get_worksheet(0)
                else:
                    # Attempt to find by name if ID is missing
                    try:
                        self.sheet = self.client.open("codex7_analytics").get_worksheet(0)
                    except:
                        print("Analytics Sheet not found. Logging to fallback.")
        except Exception as e:
            print(f"Analytics Initialization Error: {e}")

    async def log_event(self, event_type: str, data: Dict[str, Any]):
        """
        Non-blocking background logging.
        """
        asyncio.create_task(self._process_log(event_type, data))

    async def _process_log(self, event_type: str, data: Dict[str, Any]):
        timestamp = datetime.datetime.now().isoformat()
        row = [
            timestamp,
            data.get("user_id", "anonymous"),
            event_type,
            data.get("user_query", "N/A"),
            data.get("detected_language", "N/A"),
            data.get("rating", "N/A"),
            data.get("feedback_message", "N/A"),
            data.get("error_log", "N/A")
        ]

        # 1. Try Google Sheets
        if self.sheet:
            try:
                self.sheet.append_row(row)
                return
            except Exception as e:
                print(f"Sheets Logging Failed: {e}")

        # 2. Fallback to Local JSON
        try:
            with open(self.fallback_path, "r") as f:
                logs = json.load(f)
            logs.append({
                "timestamp": timestamp,
                "event_type": event_type,
                **data
            })
            with open(self.fallback_path, "w") as f:
                json.dump(logs, f, indent=4)
        except Exception as e:
            print(f"Fallback Logging Failed: {e}")

# Global Instance
analytics = AnalyticsService()
