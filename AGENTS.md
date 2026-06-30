# AGENTS.md — Goethe Booking Bot

## Session Context (latest — maintenance + secret hygiene pass)
- **Production-breaking bugs fixed in `database.py`** (the Postgres path used in prod):
  `save_checkpoint`/`get_checkpoint` and `update_student_status` had signatures that
  did NOT match how `booking_helper.py`/`webapp.py` call them. A prior commit message
  (`2b90919`) claimed these were fixed but the code still had the broken versions.
  Now genuinely fixed: `save_checkpoint(key, step:int)`, `get_checkpoint(key)->int`,
  `update_student_status(student_key, ...)` matching `name|level|city`.
- **`db.py` cleanup**: removed a broken duplicate `add_student` (referenced an undefined
  `students` var and did `DELETE FROM students`).
- **`scripts/backup.py`** pointed at `booking_bot.db`; real file is `bot_data.db` — fixed
  (now also copies WAL/SHM sidecars). Local-SQLite only; Postgres backups are separate.
- **Secrets purged from the repo**: hardcoded Goethe credentials, Railway/dashboard tokens,
  ScrapingBee key, and admin login were removed from tracked files (scripts, `tests/k6_load.js`,
  `postman_collection.json`, `add_postgres.py`, this file) and replaced with env-var reads.
  **All previously-committed secrets must be rotated at their providers — see below.**
- **Regression tests added**: `tests/test_database.py` (checkpoint/status on the SQLAlchemy
  layer) and `tests/test_booking_wizard.py` (wizard helper logic).

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

### ✅ Done (verified against code)
- Login HTML bug — `database.py` calls `init_db()`; `/api/*` 404/405/500 return JSON
- Service worker scoped to same-origin non-API GET
- `vercel.json` SPA rewrites; WebSocket token auth (`validate_token`)
- **database.py checkpoint/status signatures fixed** (this pass)
- **db.py duplicate `add_student` removed** (this pass)
- **backup.py DB path fixed** (this pass)
- **Secrets purged from tracked files** (this pass)
- Priority queue (sort by datetime); browser profiles; concurrent booking (semaphore);
  selector health check in `/api/health`; gsheets retry/backoff; post-booking verification;
  session refresh per step; failure evidence (screenshot+HTML); student re-queue ×3;
  scheduled active-hours polling; confirmation capture; slot pre-check; Telegram/email notifications
- Regression tests: `tests/test_database.py`, `tests/test_booking_wizard.py`

### ⬜ Pending
- [ ] Rotate all leaked secrets at their providers (see table above) — values removed from repo, but they were public
- [ ] Automated Postgres backups (pg_dump cron) — Railway only auto-backs-up on paid plan
- [ ] Railway reCAPTCHA bypass for Goethe login — Hetzner VPS (≈€3.99/mo) or residential proxy / 2Captcha
- [ ] Live booking test — blocked until the next registration window opens
- [ ] Auto-connect: hide the connect bar when already authenticated (claimed before, not in UI)
- [ ] India adaptation — separate Webshop-based engine (different from Pakistan `pr_finder`)
- [ ] No automated tests for the *full* live booking flow (helpers + scrapers + db layer are covered)
