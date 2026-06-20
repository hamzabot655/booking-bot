"""Read student data from Google Sheets."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import gspread as _gspread
    from google.oauth2.service_account import Credentials as _Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "1C7VD_52VnGmJqYSQGtdNzBZGekvCRHWUrdZCgTvvhAY")
SA_PATH = Path(__file__).parent / "goethe-bot-sa.json"

COLUMNS = [
    "name", "email", "password", "level", "city", "booking_datetime",
    "first_name", "surname", "dob", "contact_number",
    "country", "postal_code", "street", "house_number", "additional_address",
    "location_city", "phone_prefix", "phone", "place_of_birth", "motivation", "promo_code",
]


def get_client(write: bool = False):
    import gspread
    from google.oauth2.service_account import Credentials
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
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
        return "Connected! %d student(s) loaded: %s" % (len(students), ", ".join(s["name"] for s in students))
    except Exception as e:
        return "Connection failed: %s" % e


def get_sheet_headers() -> List[str]:
    """Return current header row from the sheet."""
    try:
        gc = get_client()
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.sheet1
        return [h.strip().lower() for h in ws.row_values(1) if h.strip()]
    except Exception:
        return COLUMNS


def auto_fill_booking_datetimes() -> str:
    """For students missing booking_datetime, fetch from Goethe scraper and fill."""
    try:
        import goethe_scraper
        schedule = goethe_scraper.get_schedule(force_refresh=True)
    except Exception as e:
        return "Failed to fetch Goethe schedule: %s" % e

    try:
        gc = get_client(write=True)
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.sheet1
        rows = ws.get_all_values()
        if len(rows) < 2:
            return "No data rows in sheet"
        headers = [h.strip().lower() for h in rows[0]]
        invalid = {"dt", "_", "n/a", "na", "none", "tbd", ""}
        dt_col = None
        for i, h in enumerate(headers):
            if h == "booking_datetime":
                dt_col = i
                break
        if dt_col is None:
            return "booking_datetime column not found in sheet"

        updates = 0
        for row_idx, row in enumerate(rows[1:], start=2):
            raw = row[dt_col].strip() if dt_col < len(row) else ""
            if raw.lower() not in invalid:
                continue
            student = dict(zip(headers, row))
            level = student.get("level", "").upper().strip()
            city = student.get("city", "").strip()
            if not level or not city:
                continue
            best = None
            for entry in schedule:
                if entry.level.upper() == level and entry.city.lower() == city.lower():
                    dt_str = entry.reg_open + "T" + entry.reg_open_time if entry.reg_open_time else entry.reg_open
                    if dt_str:
                        best = dt_str
                        break
            if best:
                ws.update_cell(row_idx, dt_col + 1, best)
                updates += 1
        return "Auto-filled %d student(s) with booking datetimes from Goethe schedule" % updates
    except Exception as e:
        return "Auto-fill failed: %s" % e


def _find_sheet_id_by_title(sh, title: str) -> Optional[int]:
    for ws in sh.worksheets():
        if ws.title == title:
            return ws.id
    return None


SCHEDULE_TAB = "Schedule"


def update_schedule_tab() -> str:
    """Create/update Schedule tab with all Goethe exam dates."""
    try:
        import goethe_scraper
        schedule = goethe_scraper.get_schedule(force_refresh=True)
    except Exception as e:
        return "Failed to fetch Goethe schedule: %s" % e

    try:
        gc = get_client(write=True)
        sh = gc.open_by_key(SHEET_ID)
        try:
            ws = sh.worksheet(SCHEDULE_TAB)
        except Exception:
            ws = sh.add_worksheet(title=SCHEDULE_TAB, rows=100, cols=3)
        rows_data = [["Level", "City", "BookingDateTime"]]
        for entry in schedule:
            dt_str = entry.reg_open + "T" + entry.reg_open_time if entry.reg_open_time else entry.reg_open
            rows_data.append([entry.level.upper(), entry.city, dt_str])
        ws.clear()
        ws.update(values=rows_data, range_name="A1")
        return "Schedule tab updated with %d entries" % len(schedule)
    except Exception as e:
        return "Update Schedule tab failed: %s" % e


def setup_dropdown() -> str:
    """Set up data validation dropdown on booking_datetime pointing to Schedule tab."""
    try:
        gc = get_client(write=True)
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.sheet1
        rows = ws.get_all_values()
        if len(rows) < 2:
            return "No data rows in sheet"
        headers = [h.strip().lower() for h in rows[0]]
        dt_col = None
        for i, h in enumerate(headers):
            if h == "booking_datetime":
                dt_col = i
                break
        if dt_col is None:
            return "booking_datetime column not found"

        sid = _find_sheet_id_by_title(sh, SCHEDULE_TAB)
        if sid is None:
            return "Schedule tab not found — run update_schedule_tab first"

        total_rows = len(rows)
        body = {
            "requests": [{
                "setDataValidation": {
                    "range": {
                        "sheetId": ws.id,
                        "startColumnIndex": dt_col,
                        "endColumnIndex": dt_col + 1,
                        "startRowIndex": 1,
                        "endRowIndex": total_rows
                    },
                    "rule": {
                        "condition": {
                            "type": "ONE_OF_RANGE",
                            "values": [{"userEnteredValue": "='%s'!C2:C" % SCHEDULE_TAB}]
                        },
                        "strict": True,
                        "showCustomUi": True
                    }
                }
            }]
        }
        sh.batch_update(body)
        return "Dropdown set on booking_datetime from Schedule tab"
    except Exception as e:
        return "Setup dropdown failed: %s" % e
