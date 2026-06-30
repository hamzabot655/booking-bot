"""Regression tests for the SQLAlchemy layer (database.py — the production
Postgres path). These guard the bugs where database.py's signatures had drifted
from db.py and from how booking_helper.py / webapp.py actually call them:

  - save_checkpoint(key, step:int) / get_checkpoint(key)->int  (was 3-arg / dict)
  - update_student_status(student_key, ...) matching name|level|city (was id:int)

Run on SQLite (set via DATABASE_URL) so they exercise the SQLAlchemy code path
without needing a real Postgres server.
"""
import importlib
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture()
def database(tmp_path):
    """Import database.py bound to a throwaway SQLite file."""
    db_file = tmp_path / "test_sa.db"
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    # Ensure a fresh module bound to the temp engine.
    sys.modules.pop("database", None)
    mod = importlib.import_module("database")
    try:
        yield mod
    finally:
        if old is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old
        sys.modules.pop("database", None)


def test_checkpoint_roundtrip_returns_int(database):
    database.save_checkpoint("Abeer|A1|Karachi", 3)
    val = database.get_checkpoint("Abeer|A1|Karachi")
    assert val == 3
    assert isinstance(val, int)


def test_checkpoint_default_is_zero_int(database):
    val = database.get_checkpoint("does|not|exist")
    assert val == 0
    assert isinstance(val, int)


def test_checkpoint_supports_gt_comparison(database):
    """booking_helper does `if resume_step > 0` — must not raise."""
    database.save_checkpoint("X|A1|Lahore", 5)
    assert database.get_checkpoint("X|A1|Lahore") > 0
    assert not (database.get_checkpoint("missing|A1|Lahore") > 0)


def test_clear_checkpoint(database):
    database.save_checkpoint("Y|B1|Karachi", 4)
    database.clear_checkpoint("Y|B1|Karachi")
    assert database.get_checkpoint("Y|B1|Karachi") == 0


def test_update_student_status_by_composite_key(database):
    sid = database.add_student({
        "name": "Ali", "email": "ali@x.com", "level": "A1", "city": "Karachi",
    })
    assert sid
    # webapp/booking_helper call this with the "name|level|city" key, NOT the id.
    database.update_student_status("Ali|A1|Karachi", "confirmed", {"reference": "REF1"})
    rows = database.get_students()
    row = [r for r in rows if r["name"] == "Ali"][0]
    assert row["status"] == "confirmed"
    assert row["result"]["reference"] == "REF1"


def test_update_student_status_unknown_key_noop(database):
    database.add_student({"name": "Bob", "level": "A2", "city": "Lahore"})
    # Must not raise on a non-matching / malformed key.
    database.update_student_status("Nobody|C1|Berlin", "failed", {})
    database.update_student_status("garbage-key", "failed", {})
    rows = database.get_students()
    assert [r for r in rows if r["name"] == "Bob"][0]["status"] != "failed"
