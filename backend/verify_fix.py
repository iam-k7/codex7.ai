from sheets_service import SheetsDB
import os

print("-" * 50)
print("Verifying Sheets Solution...")
print(f"GOOGLE_SHEET_ID: {os.getenv('GOOGLE_SHEET_ID')}")
db = SheetsDB()
print(f"Is Connected: {db.is_connected()}")
print("-" * 50)
