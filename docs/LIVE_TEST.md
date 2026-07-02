# Live Booking Test Runbook

Run this on the next real registration window. Goal: prove the full flow works against the
**live** goethe.de DOM (the wizard has never been confirmed end-to-end on a real booking).

> **Login status (verified July 2, 2026):** Login WORKS from a home IP (headless or headful) after the
> Usercentrics consent fix (`5ea24bd`). **Railway does NOT log in — its datacenter IP is blocked** (tested:
> fails with uc AND plain Selenium AND consent-fix live). **So run the booking LOCAL** (`scripts\run_local.bat`),
> not on Railway. The wizard/confirm pages past login are still unproven and may have their own reCAPTCHA.

## Preconditions
- [ ] reCAPTCHA path solved: bot runs from a clean IP (VPS, see `VPS_SETUP.md`) **or** an
      IP-whitelisted residential proxy in `PROXY_LIST` **or** `CAPTCHA_API_KEY` set (2Captcha).
- [ ] Secrets rotated (see `SECURITY_ROTATION.md`) and set in the runtime env.
- [ ] `FERNET_KEY` set (or DB-persisted) so the student password decrypts.
- [ ] One **real** student row with a fresh Goethe account, correct level/city, and the exact
      `booking_datetime` (registration-open time) from the official schedule.
- [ ] Telegram configured and verified (`python scripts/test_notifications.py`).

## Dry checks (before the window)
```bash
# selectors still match the live form (residential IP / local run):
python scripts/scan_form_local.py --email <goethe-email> --password <goethe-pw>
# slot availability pre-check:
curl -s -X POST "$BACKEND/api/slots/check" -H "Authorization: Bearer $TOKEN" -d '{}'
```

## During the window
1. Start a screen recording (OBS) — you want evidence of each step.
2. Load 1 student only; click **Start** (or `/start` via Telegram).
3. Watch the live log feed / `journalctl` and confirm each milestone appears:
   - `★ Slot found! Clicking 'Select modules'`
   - Wizard Step 1 (Name & Birth) → Step 2 (Address & Motivation) → Step 3 (Payment/Invoice)
     → Step 4 (Promo) → Step 5 (Review & Confirm)
   - `✅✅ BOOKING CONFIRMED — Ref: …` (and profile verification)
4. If a step stalls, check `debug_step*_*.png` / `.html` (failure evidence) for the live DOM,
   and update `selector_fallbacks.py` if a field name/id changed.

## After
- [ ] Confirm the booking reference on the student's mein.goethe.de profile.
- [ ] Confirm the Telegram success alert arrived.
- [ ] Note any selector drift and commit selector fixes.

## Fast rollback / stop
- Dashboard **Stop** or `/stop` (Telegram) sets the stop event; in-progress students checkpoint.
