#!/usr/bin/env python3
"""Standalone one-click booking script. Bundled via PyInstaller for Windows.
On Mac: python3 book_one.py (Python comes with macOS)."""

import sys, os, json, time, logging, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import booking_helper as bot
import notifications
from db import db as sqldb

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "student.json")
CONFIG_FILE2 = os.path.join(os.path.dirname(__file__), "..", "student.json")

def load_student():
    for p in [CONFIG_FILE, CONFIG_FILE2, "student.json"]:
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
    return None

def main():
    student = load_student()
    if not student:
        print("=" * 50)
        print("  GOETHE BOOKING BOT")
        print("=" * 50)
        print("\nEnter student details:")
        student = {
            "name": input("Student name: ").strip(),
            "email": input("Goethe email: ").strip(),
            "password": input("Goethe password: ").strip(),
            "level": input("Level (A1/A2/B1): ").strip().upper(),
            "city": input("City (Karachi/Lahore/Islamabad): ").strip().title(),
            "booking_datetime": input("Booking datetime (e.g. 2026-07-03T12:16): ").strip(),
        }

    print(f"\n--- Booking for {student['name']} ---")
    print(f"  Level: {student['level']} | City: {student['city']}")
    print(f"  Time: {student.get('booking_datetime', 'ASAP')}")
    print(f"  Email: {student['email']}")
    print()

    logger = logging.getLogger("booker")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)

    logger.info("Starting booking bot...")
    logger.info("Chrome will open automatically. Do NOT close it.")

    try:
        result = bot.smart_retry(
            student,
            use_headless=False,
            logger=logger,
            stop_event=threading.Event(),
        )

        status = result.get("status", "failed")
        print()
        print("=" * 50)
        if status == "confirmed":
            print(f"  ✅ BOOKED! Ref: {result.get('reference', 'N/A')}")
        elif status == "verified":
            print(f"  ✅ VERIFIED! Ref: {result.get('reference', 'N/A')}")
        elif status == "submitted":
            print(f"  ✅ SUBMITTED!")
        else:
            print(f"  ❌ FAILED: {result.get('error', 'Unknown error')}")
        print("=" * 50)

        try:
            notifications.notify_all(
                "Booking Complete",
                f"{student['name']}: {status} | Ref: {result.get('reference', 'N/A')}",
                logger,
            )
        except Exception:
            pass

    except Exception as e:
        print(f"\n❌ CRASHED: {e}")
        import traceback
        traceback.print_exc()

    print("\nPress Enter to exit...")
    input()

if __name__ == "__main__":
    main()
