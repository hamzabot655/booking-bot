# AGENTS.md — Goethe Booking Bot

## ⏰ Booking Day Status (client: 1 student, A1 Islamabad, reg opens 03.07.2026 12:16 PM)
- **CONFIRMED: Railway CANNOT log in to Goethe.** Form Scanner from Railway prod →
  `Login failed: Still on login page — no visible error`. Cause = datacenter IP + invisible
  reCAPTCHA v3 (silent low-score block). Not removable; all datacenter IPs affected.
- **2Captcha key set** on Railway (`CAPTCHA_API_KEY=...`, $3 balance) — but code only solves
  reCAPTCHA **v2**; Goethe login is **v3**, so it does NOT fix Railway. Wired but ineffective here.
- **booking_datetime AM/PM bug FIXED** (`100a986`): student row was `2026-07-03T12:16 PM` (invalid ISO →
  bot errored). `parse_exam_time_str` now tolerates AM/PM; frontend Fetch-Dates converts to 24h.
  ⚠️ The exact reg-open time `12:16 PM` is unverified — check official goethe.de page.
- **Student loaded**: DB id 4, `abeer meer`, A1 Islamabad, email `abeermeer7979@gmail.com`, all wizard
  fields present. Password stored encrypted (FERNET key persisted in DB).
- **NOT YET TESTED: home/residential IP login.** Run `python scripts/scan_form_local.py --email .. --password ..`
  to confirm. If home works → IP block confirmed. If home also fails → it's a bug, not IP.
- **Booking-day options (ranked):** (1) run local from a clean IP — dev's home laptop or remote-in to
  client via AnyDesk (`scripts/run_local.bat` → dashboard → localhost:5000); (2) residential proxy on
  Railway (needs `selenium-wire` for user:pass auth — NOT yet implemented); (3) 2Captcha v3 (unreliable).

## Session Context (latest — maintenance, secret hygiene, Vercel rebuild)
- **CRITICAL backend-crash fixed** (`7c6294e`): `websocket_handler.py` had a committed
  `IndentationError` (from `e64dd94`) — a duplicated/orphaned `finally`/`except` tail.
  Because `webapp.py` imports it at startup, the **whole backend crashed on import** → every
  request 500'd → login returned HTML → the `"Unexpected token '<'"` symptom. Production was
  still up on an older build; `main` HEAD was a landmine that would crash on next deploy. Fixed.
- **Sheet-student delete fixed** (`a37f5c1`): deleting a student showed `"Not found"`. Sheet/
  config students get negative ids (-1, -2); the route was `<int:student_id>`, and Flask's int
  converter rejects negatives → generic 404. Route is now `<int(signed=True):student_id>`, and a
  negative id resolves back to name/level/city and deletes the matching Google Sheet row via the
  new `google_sheets.delete_student()`. Verified live (DeleteTest removed from the sheet).
- **Vercel rebuilt from scratch**: deleted the only project `goethe-frontend-v2`, created fresh
  **`goethe-frontend-v3`** (`prj_n3wa6LvxRTU36YhfUCfw0349fgc0`) → `https://goethe-frontend-v3.vercel.app`.
  Updated backend CORS + CSP to the new origin (verified live) and the GH secrets
  `VERCEL_PROJECT_ID` / `VERCEL_ORG_ID`.
- **Secrets purged from the repo** (`58f9df7`): hardcoded Goethe creds, Railway/dashboard tokens,
  ScrapingBee key, admin login removed from tracked files (scripts, `tests/k6_load.js`,
  `postman_collection.json`, `add_postgres.py`, `AGENTS.md`, `docs/session-summary.md`) and from
  the git remote URL; replaced with env-var reads. **Still must be rotated at providers — see below.**
- **Postgres backup workflow added**: `.github/workflows/pg-backup.yml` (daily `pg_dump`) +
  restore docs. Needs repo secret `DATABASE_URL_EXTERNAL` (Railway public URL).
- **Regression tests added**: `tests/test_database.py` (SQLAlchemy checkpoint/status) and
  `tests/test_booking_wizard.py` (wizard helper logic). 100 unit tests pass.
- **Verified already-correct**: the checkpoint/status signature fixes, `db.py` duplicate
  `add_student` removal, and `backup.py` DB path were already committed in `2b90919`; confirmed
  against HEAD and locked in with the new tests.

### Cleanup pass (`b5688b0`)
- **FERNET_KEY now persists**: if not set in env, `webapp.py` generates a key once and stores it
  in the DB (`bot_state`), reusing it on later boots — student passwords no longer break on restart.
- **Dead Netlify references removed**: a11y workflow + docs (SLA/BCP/TRAINING/STAGING) + `deploy.ps1`
  + `alexa.py` now reference Vercel; unused GitHub secrets `NETLIFY_AUTH_TOKEN`/`NETLIFY_SITE_ID` deleted.
- **Stale Railway URL fixed**: `...-092f...` → live `...-21af...` across scripts/tests/postman; stale
  origin dropped from the CORS whitelist.
- **Alexa system prompt** corrected (Vercel + right URLs, no hardcoded admin email).
- **Connect bar hides when authenticated** (shows again on logout/401/connect failure).
- **VPS prep**: `docs/VPS_SETUP.md` + `deploy/vps_setup.sh` (turnkey clean-IP host to bypass
  Railway reCAPTCHA). Provisioning still needs the owner.
- **More tests**: `tests/test_smart_retry.py` (retry/backoff + `_classify_error`). **111 unit tests pass.**

> ⚠️ **Do not put live secrets in this file or any tracked file.** Use env vars / `.env`
> (gitignored) and GitHub Actions / Railway secrets.

## Secrets to Rotate (were exposed in git history and/or chat)
| Secret | Where it was | Action |
|--------|--------------|--------|
| Goethe account password | scripts/*.py | Rotate the Goethe account password |
| Railway API token | AGENTS.md, add_postgres.py, CI | Revoke + reissue in Railway → set as GH secret `RAILWAY_API_TOKEN` |
| Postgres password | AGENTS.md | Rotate the Railway Postgres credentials, update `DATABASE_URL` |
| ScrapingBee API key | AGENTS.md | Rotate in ScrapingBee, set `SCRAPINGBEE_API_KEY` |
| Admin `AUTH_PASSWORD` | k6_load.js, postman, AGENTS.md | Rotate via `scripts/rotate_secrets.py`, set Railway env |
| Vercel token | shared in chat | Revoke in Vercel account settings, reissue |
| GitHub classic tokens | embedded in git remote + chat | Revoke at github.com/settings/tokens, reissue fine-scoped |

## Project Overview
Selenium bot that auto-books Goethe Institut exam slots for Pakistan region. Web control
panel (Flask) + dashboard frontend. Students loaded from Google Sheets or SQLite/Postgres DB.

## Quick Commands
```bash
# Deploy backend to Railway (auto-deploys from GitHub main; manual below)
railway up -d C:\Users\brosp\Downloads\goethe-bot

# Deploy frontend to Vercel (token via env, never inline)
vercel deploy --prod --cwd frontend --token "$VERCEL_TOKEN"

# Set Railway env var
railway variables set KEY=VALUE

# Check Railway logs
railway logs --service goethe-booking-bot -n 100

# Trigger Railway redeploy
git commit --allow-empty -m "redeploy" && git push origin main
```

## URLs
| Service | URL |
|---------|-----|
| Frontend | https://goethe-frontend-v3.vercel.app (project `prj_n3wa6LvxRTU36YhfUCfw0349fgc0`) |
| Backend | https://goethe-booking-bot-production-21af.up.railway.app |
| GitHub | https://github.com/hamzabot655/booking-bot |

## Credentials & Config (values live in env / secret stores, NOT here)
- **Auth login**: `AUTH_EMAIL` / `AUTH_PASSWORD` (Railway env vars)
- **ScrapingBee**: `SCRAPINGBEE_API_KEY`
- **Google Sheet**: `GOOGLE_SHEET_ID` (the public sheet id is non-secret; the service
  account is `GOOGLE_SERVICE_ACCOUNT_B64`)
- **Student password encryption**: `FERNET_KEY` (set a stable value or passwords are lost on restart)
- **Railway deploy**: `RAILWAY_API_TOKEN` (GitHub Actions secret)
- **Vercel deploy**: `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` (GitHub Actions secrets)

## Railway Project
- **Project**: hospitable-heart (ID: 520adb72-b1f4-4021-8c4b-21ca81f8a901)
- **Service**: goethe-booking-bot (ID: f568e242-4d2a-4b44-8205-07899abfbd26)
- **Environment**: production (ID: 20945f76-1cfa-4e38-b50b-a5cb8d5f47cd) · Region: sfo
- **Database**: Postgres via `DATABASE_URL` (internal Railway URL; credentials in env only)

## File Map
| File | Purpose |
|------|---------|
| `webapp.py` | Flask backend — API endpoints, CORS, auth, bot control, WS, scheduler |
| `booking_helper.py` | Core Selenium bot — login, 5-step wizard, smart_retry, polling |
| `goethe_scraper.py` | Pakistan exam schedule scraper — ScrapingBee → curl_cffi → Playwright → fallback |
| `google_sheets.py` | Google Sheets integration — read/write students, auto-fill dates |
| `database.py` | Postgres/SQLite via SQLAlchemy — used when `DATABASE_URL` is set; calls `init_db()` on import |
| `db.py` | SQLite layer — used when `DATABASE_URL` unset (local dev) |
| `crypto_utils.py` | bcrypt password hashing + Fernet encryption of student passwords |
| `frontend/index.html` | Single-page dashboard (6 sections) |
| `frontend/vercel.json` | SPA rewrites (`/*` → `/index.html`) — no build step |
| `frontend/sw.js` | Service worker — same-origin non-API GET only |
| `Dockerfile` | Railway deployment — Python + Chrome + Playwright |
| `pk_fallback.json` | Offline exam schedule data |

## Architecture

### Bot Flow
1. Load + merge students (DB + Sheet + CSV) via `_get_loaded_students()`, sorted by `booking_datetime`.
2. Each student → own thread + own Chrome profile (parallel, capped by `MAX_CONCURRENT` semaphore).
3. Navigate to level URL → poll for "Select modules" (burst mode near booking time) → CAS login.
4. 5-step Wicket wizard: Personal Data 1 → Personal Data 2 → Payment (Invoice) → Promo → Review & Confirm.
5. Checkpoint after each step (resume on restart); confirmation parse + profile verify; status pushed via WebSocket.

### Schedule Fetch Chain
ScrapingBee (premium_proxy) → curl_cffi (chrome131 impersonate) → Playwright (headless) → `pk_fallback.json`.

### Google Sheets 429 Handling
`_retry_gsheet()` 5→10→20→40s backoff; 15s TTL cache on `load_sheet_data()`; `strict=False` dropdown.

## Common Issues
- **"Unexpected token '<'" on any API call** → backend returned HTML (a 500 before the JSON
  error handlers, or a missing route). Check `/api/health`; error handlers now return JSON for `/api/*`.
- **Google Sheets "Quota exceeded"** → 60 reads/min/user; retry+cache handle it, else wait 1 min.
- **Schedule returns 0 entries** → ScrapingBee limit / Playwright not installed / Goethe block → falls back to `pk_fallback.json`.
- **Login fails only from Railway** → datacenter IP triggers reCAPTCHA on Goethe CAS. Needs VPS/residential proxy/2Captcha (see pending).

## Deployment Notes
- Railway auto-deploys from GitHub `main` (uses `RAILWAY_API_TOKEN` GH secret).
- Vercel frontend is static + `vercel.json` rewrites — no build step (a build step previously caused a 0-file outage).
- Backend uses Postgres (`database.py`) when `DATABASE_URL` is set; SQLite (`db.py`) otherwise.

## Todo / Known Gaps

### ✅ Done (verified against code / live)
- **websocket_handler.py IndentationError fixed** (`7c6294e`) — backend boots again; login returns JSON
- **Sheet-student delete fixed** (`a37f5c1`) — signed-int route + `google_sheets.delete_student()`; verified live
- **Vercel rebuilt** — old project deleted, fresh `goethe-frontend-v3` deployed; CORS/CSP + GH secrets updated
- **Postgres backup workflow** (`.github/workflows/pg-backup.yml`) + restore docs
- **Secrets purged** from tracked files + git remote URL (`58f9df7`)
- Login HTML bug — `database.py` calls `init_db()`; `/api/*` 404/405/500 return JSON
- Service worker scoped to same-origin non-API GET
- `vercel.json` SPA rewrites; WebSocket token auth (`validate_token`)
- checkpoint/status signatures, `db.py` duplicate `add_student`, `backup.py` DB path — already fixed in `2b90919`, verified + test-guarded
- Priority queue (sort by datetime); browser profiles; concurrent booking (semaphore);
  selector health check in `/api/health`; gsheets retry/backoff; post-booking verification;
  session refresh per step; failure evidence (screenshot+HTML); student re-queue ×3;
  scheduled active-hours polling; confirmation capture; slot pre-check; Telegram/email notifications
- **FERNET_KEY persists in DB** (`b5688b0`); **dead Netlify refs removed** + GH `NETLIFY_*` secrets deleted;
  **stale `092f`→`21af`** URL fix; **Alexa prompt** corrected; **connect bar hides when authed**;
  **VPS runbook** (`docs/VPS_SETUP.md` + `deploy/vps_setup.sh`)
- Regression tests: `tests/test_database.py`, `tests/test_booking_wizard.py`, `tests/test_smart_retry.py`

### Hardening batch (`6ac0d4e`)
- **CI now gates deploys**: `test` job runs on push+PR and both deploy jobs `needs:[test]`; added a
  `py_compile` + `import webapp` smoke step (catches the class of bug that was the Part-5 crash).
  Verified live: a push now runs tests before deploying.
- **2Captcha wired into login**: `_login_attempt` calls `detect_captcha`/`solve_captcha` (was dead code;
  no-op without `CAPTCHA_API_KEY`).
- **Alert webhook**: `notifications.notify_all` also POSTs to `ALERT_WEBHOOK_URL` (SMS/call bridge);
  `scripts/test_notifications.py` verifies all channels.
- **Wizard field-mapping tests**: `tests/test_wizard_steps.py` (116 unit tests pass).
- **Owner runbooks**: `docs/SECURITY_ROTATION.md`, `docs/LIVE_TEST.md`; proxy-auth limitation documented
  in `docs/VPS_SETUP.md`.

### Git history scrubbed
- Ran `git filter-repo` + force-push (`7e6ea15`) — all known leaked literals now redacted across
  history (verified: 0 commits contain them). **This does NOT rotate them** — the credentials still
  work until rotated at the provider (see below). Any other local clone is now divergent → re-clone.

### ⬜ Pending (owner action)
- [ ] **Rotate all leaked secrets — STILL REQUIRED.** History scrub ≠ rotation; the tokens/passwords
      remain valid until changed at each provider. Checklist: `docs/SECURITY_ROTATION.md`.
- [ ] Provision reCAPTCHA bypass — VPS (`docs/VPS_SETUP.md`) / IP-whitelisted residential proxy / set `CAPTCHA_API_KEY`.
- [ ] Set repo secret `DATABASE_URL_EXTERNAL` (Railway public Postgres URL) for pg-backup — I can set it once you paste the value.
- [ ] Live booking test — run `docs/LIVE_TEST.md` on the next registration window.

> India adaptation is **dropped** (client no longer engaged). Scope is Goethe **Pakistan** only.
