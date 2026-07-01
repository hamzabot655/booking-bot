"""Mock tests for the 5-step Wicket wizard field mapping.

Drives _fill_step_* against a fake driver with the low-level fill helpers
stubbed, so we assert each student CSV field lands in the correct selector key
and each step advances — without a live browser/DOM. This is the coverage that
catches "wrong field mapping" regressions before a live window.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import booking_helper as bot


class FakeDriver:
    def __init__(self, url="https://www.goethe.de/coe/options"):
        self.current_url = url

    def execute_script(self, *a, **k):
        return None

    def find_elements(self, *a, **k):
        return []


@pytest.fixture()
def capture(monkeypatch):
    """Stub the low-level helpers and record (selector_key, value) calls."""
    calls = {"text": [], "select": [], "continue": 0, "human_click": 0}
    monkeypatch.setattr(bot, "_ensure_session", lambda *a, **k: None)
    monkeypatch.setattr(bot, "wait_for_document_ready", lambda *a, **k: None)
    monkeypatch.setattr(bot, "random_human_delay", lambda *a, **k: None)
    monkeypatch.setattr(bot, "random_scroll", lambda *a, **k: None)
    monkeypatch.setattr(bot, "human_move_and_click",
                        lambda *a, **k: calls.__setitem__("human_click", calls["human_click"] + 1))

    def fake_text(driver, selectors, value, logger, timeout=5):
        calls["text"].append((selectors[0], value))
        return True

    def fake_select(driver, selectors, value, logger, timeout=5):
        calls["select"].append((selectors[0], value))
        return True

    monkeypatch.setattr(bot, "_fill_text_input", fake_text)
    monkeypatch.setattr(bot, "_fill_select_by_visible", fake_select)
    monkeypatch.setattr(bot, "_click_continue_wizard",
                        lambda *a, **k: calls.__setitem__("continue", calls["continue"] + 1) or True)
    return calls


def test_step1_personal_data_maps_fields(capture):
    student = {
        "first_name": "Ali", "surname": "Khan", "name": "Ali Khan",
        "dob": "15/03/2000", "email": "ali@example.com", "contact_number": "923001234567",
    }
    ok = bot._fill_step_personal_data_1(FakeDriver(), student, bot.logging.getLogger("t"))
    assert ok is True
    text = dict(capture["text"])
    sel = dict(capture["select"])
    assert text["first_name"] == "Ali"
    assert text["surname"] == "Khan"
    assert text["email_field"] == "ali@example.com"
    assert text["contact_number"] == "923001234567"
    assert (sel["dob_day"], sel["dob_month"], sel["dob_year"]) == ("15", "03", "2000")
    assert capture["continue"] == 1


def test_step1_dob_dot_separator(capture):
    student = {"name": "A B", "dob": "01.12.1999", "email": "a@b.com"}
    assert bot._fill_step_personal_data_1(FakeDriver(), student, bot.logging.getLogger("t")) is True
    sel = dict(capture["select"])
    assert (sel["dob_day"], sel["dob_month"], sel["dob_year"]) == ("01", "12", "1999")


def test_step2_address_and_motivation_maps_fields(capture):
    student = {
        "country": "Pakistan", "postal_code": "75500", "street": "Main St",
        "house_number": "12", "additional_address": "Apt 3B", "city": "Karachi",
        "phone_prefix": "+92", "phone": "3001234567", "place_of_birth": "Lahore",
        "motivation": "Study",
    }
    ok = bot._fill_step_personal_data_2(FakeDriver(), student, bot.logging.getLogger("t"))
    assert ok is True
    text = dict(capture["text"])
    sel = dict(capture["select"])
    assert text["postal_code"] == "75500"
    assert text["street_field"] == "Main St"
    assert text["house_number"] == "12"
    assert text["additional_address"] == "Apt 3B"
    assert text["location_city"] == "Karachi"
    assert text["form_phone"] == "3001234567"
    assert text["form_place_of_birth"] == "Lahore"
    assert sel["country_dropdown"] == "Pakistan"
    assert sel["phone_prefix"] == "+92"
    assert sel["motivation_dropdown"] == "Study"
    assert capture["continue"] == 1


def test_step2_country_defaults_to_pakistan(capture):
    bot._fill_step_personal_data_2(FakeDriver(), {"city": "Lahore"}, bot.logging.getLogger("t"))
    assert dict(capture["select"])["country_dropdown"] == "Pakistan"


def test_promo_step_skips_when_no_code(capture, monkeypatch):
    # No promo_code → should not look up the promo field, just continue.
    monkeypatch.setattr(bot, "find_element_fallback", lambda *a, **k: None)
    ok = bot._fill_step_promo(FakeDriver(), {}, bot.logging.getLogger("t"))
    assert ok is True
    assert capture["continue"] == 1
    assert all(k != "promo_code" for k, _ in capture["text"])
