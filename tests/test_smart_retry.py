"""Tests for booking_helper.smart_retry + _classify_error.

smart_retry is the core resilience logic (transient errors get the full retry
budget; permanent errors give up after one). We mock run_student_flow so no real
Selenium/browser is needed, and no-op the backoff sleeps + circuit-breaker wait.
"""
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import booking_helper as bot


@pytest.fixture(autouse=True)
def fast_and_isolated(monkeypatch):
    # Skip real backoff sleeps and circuit-breaker waiting.
    monkeypatch.setattr(bot.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(bot.CIRCUIT_BREAKER, "wait_until_allowed", lambda *a, **k: True)
    monkeypatch.setattr(bot, "MAX_SMART_RETRIES", 2)


def _run(monkeypatch, results):
    """Make run_student_flow return successive results from `results`, counting calls."""
    calls = {"n": 0}

    def fake_flow(student, use_headless, logger, stop_event=None, proxy=None, immediate=False):
        i = min(calls["n"], len(results) - 1)
        calls["n"] += 1
        return dict(results[i])

    monkeypatch.setattr(bot, "run_student_flow", fake_flow)
    return calls


def _args():
    import logging
    return {"name": "T", "level": "A1", "city": "Karachi"}, False, logging.getLogger("t"), threading.Event()


def test_success_first_try_no_retry(monkeypatch):
    calls = _run(monkeypatch, [{"status": "confirmed", "reference": "R1"}])
    s, h, lg, ev = _args()
    res = bot.smart_retry(s, h, lg, ev)
    assert res["status"] == "confirmed"
    assert calls["n"] == 1


def test_transient_error_uses_full_budget(monkeypatch):
    # "timeout" is transient → retried MAX_SMART_RETRIES times → MAX+1 total calls.
    calls = _run(monkeypatch, [{"status": "failed", "error": "connection timeout"}])
    s, h, lg, ev = _args()
    res = bot.smart_retry(s, h, lg, ev)
    assert res["status"] == "failed"
    assert calls["n"] == 3  # 1 initial + 2 retries


def test_permanent_error_gives_up_early(monkeypatch):
    # Non-transient error → only 1 retry (2 total calls), not the full budget.
    calls = _run(monkeypatch, [{"status": "failed", "error": "invalid email or password"}])
    s, h, lg, ev = _args()
    res = bot.smart_retry(s, h, lg, ev)
    assert res["status"] == "failed"
    assert calls["n"] == 2


def test_recovers_on_retry(monkeypatch):
    # First a transient fail, then success → stops retrying once confirmed.
    calls = _run(monkeypatch, [
        {"status": "failed", "error": "service unavailable"},
        {"status": "confirmed", "reference": "R2"},
    ])
    s, h, lg, ev = _args()
    res = bot.smart_retry(s, h, lg, ev)
    assert res["status"] == "confirmed"
    assert calls["n"] == 2


def test_stop_event_during_backoff(monkeypatch):
    # If the circuit breaker wait reports stop, smart_retry returns 'stopped'.
    monkeypatch.setattr(bot.CIRCUIT_BREAKER, "wait_until_allowed", lambda *a, **k: False)
    _run(monkeypatch, [{"status": "failed", "error": "connection timeout"}])
    s, h, lg, ev = _args()
    res = bot.smart_retry(s, h, lg, ev)
    assert res["status"] == "stopped"


@pytest.mark.parametrize("msg,expected", [
    ("HTTP 503 Service Unavailable", "block"),
    ("captcha required", "block"),
    ("rate limit exceeded (429)", "block"),
    ("connection timed out", "timeout"),
    ("read timeout", "timeout"),
    ("some random failure", "generic"),
])
def test_classify_error(msg, expected):
    assert bot._classify_error(Exception(msg)) == expected
