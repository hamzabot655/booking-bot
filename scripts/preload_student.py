"""Preload the booking-day student into the local SQLite DB.

Secrets (FERNET_KEY, Goethe password) are read from the ENVIRONMENT — never
hardcode them here. book_tomorrow.bat (local, gitignored) sets them before
calling this. The student's full wizard fields ARE included (dob, address,
phone, etc.) — the 5-step wizard fails without them.

Usage (env must be set):
  set FERNET_KEY=...
  set GOETHE_PASSWORD=...
  python scripts/preload_student.py
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///bot_data.db")

sys.path.insert(0, str(Path(__file__).parent.parent))
import crypto_utils
import db

FERNET_KEY = os.environ.get("FERNET_KEY", "")
GOETHE_PASSWORD = os.environ.get("GOETHE_PASSWORD", "")
if not FERNET_KEY or not GOETHE_PASSWORD:
    print("ERROR: set FERNET_KEY and GOETHE_PASSWORD env vars before running.")
    sys.exit(1)

# Full record (matches the Railway DB row for abeer meer) — all wizard fields
# populated so Steps 1-2 (name/birth, address/motivation) can complete.
student_data = {
    "name": "abeer meer",
    "email": "abeermeer7979@gmail.com",
    "password": crypto_utils.encrypt_password(GOETHE_PASSWORD, FERNET_KEY),
    "level": "A1",
    "city": "Islamabad",
    "booking_datetime": "2026-07-03T12:16",
    "first_name": "Abeer",
    "surname": "Meer",
    "dob": "19/03/2000",
    "place_of_birth": "Lahore",
    "contact_number": "+923124092886",
    "country": "Pakistan",
    "postal_code": "54000",
    "street": "PIA Society",
    "house_number": "House no 125",
    "additional_address": "Block F",
    "location_city": "Lahore",
    "phone_prefix": "92",
    "phone": "3124092886",
    "motivation": "Study",
    "promo_code": "",
}

db.init_db()
sid = db.add_student(student_data)
print(f"Student added with ID: {sid} — abeer meer / A1 / Islamabad / 2026-07-03T12:16")
print("All wizard fields populated. Now start webapp.py and click Start in the dashboard.")
