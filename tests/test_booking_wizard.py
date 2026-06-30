"""Lightweight tests for the booking-wizard helper logic in booking_helper.py.

The full Selenium flow can't run headless in CI, so these use a fake driver +
monkeypatched selector lookup to exercise the branching that the 5-step wizard
relies on (field fill, empty-value short-circuit, session re-login detection).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import booking_helper as bot


class FakeEl:
    def __init__(self, tag="input", displayed=True):
        self._tag = tag
        self._displayed = displayed
        self.value = ""
        self.cleared = False
        self.clicked = False

    def clear(self):
        self.cleared = True
        self.value = ""

    def click(self):
        self.clicked = True

    def send_keys(self, ch):
        self.value += ch

    def is_displayed(self):
        return self._displayed

    @property
    def tag_name(self):
        return self._tag


class FakeDriver:
    def __init__(self, url="https://www.goethe.de/coe/options"):
        self.current_url = url

    def execute_script(self, *a, **k):
        return None


def test_fill_text_input_empty_value_is_noop(monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(bot, "find_element_fallback", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or FakeEl())
    assert bot._fill_text_input(FakeDriver(), ["first_name"], "", bot.logging.getLogger("t")) is False
    assert called["n"] == 0  # never even looked up a selector for empty value


def test_fill_text_input_fills_when_found(monkeypatch):
    el = FakeEl()
    monkeypatch.setattr(bot, "find_element_fallback", lambda *a, **k: el)
    ok = bot._fill_text_input(FakeDriver(), ["first_name"], "Abeer", bot.logging.getLogger("t"))
    assert ok is True
    assert el.value == "Abeer"
    assert el.cleared is True


def test_fill_text_input_returns_false_when_not_found(monkeypatch):
    monkeypatch.setattr(bot, "find_element_fallback", lambda *a, **k: None)
    ok = bot._fill_text_input(FakeDriver(), ["first_name"], "Abeer", bot.logging.getLogger("t"))
    assert ok is False


def test_is_cas_login_page_detection():
    assert bot._is_cas_login_page(FakeDriver("https://login.goethe.de/cas/login")) is True
    assert bot._is_cas_login_page(FakeDriver("https://www.goethe.de/coe/options")) is False


def test_ensure_session_relogins_on_cas_page(monkeypatch):
    calls = []
    monkeypatch.setattr(bot, "_handle_cas_login_if_needed",
                        lambda d, s, l: calls.append(True) or True)
    bot._ensure_session(FakeDriver("https://login.goethe.de/cas/login"),
                        {"email": "a@b.com", "password": "x"},
                        bot.logging.getLogger("t"), "Step 1")
    assert calls == [True]


def test_ensure_session_skips_when_not_on_login(monkeypatch):
    calls = []
    monkeypatch.setattr(bot, "_handle_cas_login_if_needed",
                        lambda d, s, l: calls.append(True) or True)
    bot._ensure_session(FakeDriver("https://www.goethe.de/coe/options"),
                        {"email": "a@b.com", "password": "x"},
                        bot.logging.getLogger("t"), "Step 1")
    assert calls == []
