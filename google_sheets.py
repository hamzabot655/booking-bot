"""Read student data from Google Sheets."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "1C7VD_52VnGmJqYSQGtdNzBZGekvCRHWUrdZCgTvvhAY")
SA_PATH = Path(__file__).parent / "goethe-bot-sa.json"

COLUMNS = [
    "name", "email", "password", "level", "city", "booking_datetime",
    "first_name", "surname", "dob", "contact_number",
    "country", "postal_code", "street", "house_number", "additional_address",
    "location_city", "phone_prefix", "phone", "place_of_birth", "motivation", "promo_code",
]


def get_client():
    import gspread
    from google.oauth2.service_account import Credentials
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(str(SA_PATH), scopes=scopes)
    return gspread.authorize(creds)


def load_sheet_data(sheet_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read all rows from Google Sheet, return list of student dicts."""
    if not SA_PATH.exists():
        return []
    try:
        gc = get_client()
        sh = gc.open_by_key(sheet_id or SHEET_ID)
        ws = sh.sheet1
        rows = ws.get_all_values()
        if len(rows) < 2:
            return []
        headers = [h.strip().lower() for h in rows[0]]
        students = []
        for row in rows[1:]:
            if not any(cell.strip() for cell in row):
                continue
            student = {}
            for i, val in enumerate(row):
                if i < len(headers):
                    student[headers[i]] = val.strip()
            if student.get("name"):
                students.append(student)
        return students
    except Exception as e:
        logging.getLogger("google_sheets").warning("Google Sheets read error: %s", e)
        return []


def test_connection() -> str:
    """Test connection and return status message."""
    try:
        students = load_sheet_data()
        if not students:
            return "Sheet connected but no data found (check headers match template)"
        return f"✅ Connected! {len(students)} student(s) loaded: {', '.join(s['name'] for s in students)}"
    except Exception as e:
        return f"❌ Connection failed: {e}"
