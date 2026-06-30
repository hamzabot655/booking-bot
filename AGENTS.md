# AGENTS.md — Goethe Booking Bot

## Session Context (June 30, 2026)
- **All 5 Critical fixes deployed**: verification, session refresh, failure evidence, retry, scheduled polling
- **Postgres connected**: `DATABASE_URL` set to Railway Postgres internal URL — data persists across restarts
- **psycopg2-binary deployed**: Railway builds now succeed (was missing from requirements.txt, caused 14 failed deploys)
- **Netlix blocked**: Account credit exceeded — frontend deploys won't work until credits added
- **Next**: 8 remaining todos (Priority Queue, Slot Pre-check, Browser Profiles, Confirmation Capture, Notifications, Concurrent Booking, Selector Health Check, Postgres Backups)

## Project Overview
Selenium bot that auto-books Goethe Institut exam slots for Pakistan region. Web control panel (Flask) + dashboard frontend. Students loaded from Google Sheets or SQLite/Postgres DB.

## Quick Commands
```bash
# Deploy backend to Railway (auto-deploys from GitHub main; manual)
railway up -d C:\Users\brosp\Downloads\goethe-bot

# Deploy frontend to Vercel
vercel deploy --prod --cwd frontend --token $VERCEL_TOKEN

# Set Railway env var
railway variable set KEY=VALUE

# Check Railway logs
railway logs --service goethe-booking-bot -n 100

# Trigger Railway redeploy
railway service redeploy --yes
# or: git commit --allow-empty -m "redeploy" && git push origin main
```

## URLs
| Service | URL |
|---------|-----|
| Frontend | https://goethe-booking-dashboard.vercel.app |
| Backend | https://goethe-booking-bot-production-21af.up.railway.app |
| GitHub | https://github.com/hamzabot655/booking-bot (new repo) |

## Credentials
- **Auth login**: AUTH_EMAIL=`hamzarafiq655@gmail.com` / AUTH_PASSWORD=`REDACTED` (Railway env vars)
- **ScrapingBee API**: REDACTED (set via `SCRAPINGBEE_API_KEY` env var)
- **Google Sheet ID**: `1C7VD_52VnGmJqYSQGtdNzBZGekvCRHWUrdZCgTvvhAY` (`GOOGLE_SHEET_ID` env var)
- **Google Service Account**: Base64 in `GOOGLE_SERVICE_ACCOUNT_B64` env var

## Railway Project
- **Project**: hospitable-heart (ID: 520adb72-b1f4-4021-8c4b-21ca81f8a901)
- **Service**: goethe-booking-bot (ID: f568e242-4d2a-4b44-8205-07899abfbd26)
- **Environment**: production (ID: 20945f76-1cfa-4e38-b50b-a5cb8d5f47cd)
- **Region**: sfo
- **Database**: Postgres — internal URL `postgresql://postgres:REDACTED@postgres.railway.internal:5432/railway` set via `DATABASE_URL` env var
- **API Token**: `REDACTED` (long-lived, set as GitHub secret)

## File Map
| File | Purpose |
|------|---------|
| `webapp.py` | Flask backend — API endpoints, CORS, auth, bot control |
| `booking_helper.py` | Core Selenium bot — login, 5-step wizard, smart_retry, polling |
| `goethe_scraper.py` | Pakistan exam schedule scraper — ScrapingBee → curl_cffi → Playwright → fallback |
| `google_sheets.py` | Google Sheets integration — read/write students, auto-fill dates, update schedule tab |
| `db.py` | SQLite DB — students, logs, settings tables |
| `frontend/index.html` | Single-page dashboard — 6 sections (Dashboard, Controls, Schedule, Students, Logs, Settings) |
| `Dockerfile` | Railway deployment — Python + Chrome + Playwright |
| `pk_fallback.json` | Offline exam schedule data (10 entries, Jul-Oct 2026) |
| `.vercel/` | Vercel project link config |

## Architecture

### API Endpoints (all prefixed with `/api`)
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/login` | POST | No | Returns JWT token |
| `/students` | GET | Yes | List all students (DB + sheet + config merged) |
| `/students` | POST | Yes | Add student to DB + Google Sheet |
| `/students/<id>` | DELETE | Yes | Delete DB student (negative id = sheet-only, returns 400) |
| `/goethe-schedule` | GET | Yes | Pakistan exam schedule (`?refresh=1` for live, `?level=A1` to filter) |
| `/sheets/update-schedule` | POST | Yes | Update Google Sheets Schedule tab from Goethe data |
| `/sheets/auto-fill` | POST | Yes | Auto-fill booking_datetime for empty students |
| `/schedule` | GET | Yes | Load students from Google Sheet |
| `/start` | POST | Yes | Start bot on all students |
| `/stop` | POST | Yes | Stop bot |
| `/config` | GET/POST | Yes | Bot configuration |
| `/live-status` | GET | Yes | Live booking status per student |
| `/heartbeat` | GET | Yes | Dead man switch heartbeat |

### Student ID System
- **DB students**: positive `id` (SQLite auto-increment)
- **Sheet/config students**: negative `id` (e.g., -1, -2) assigned in `_get_loaded_students()`
- Delete button visible for all, but sheet-only delete returns error msg

### Bot Flow
1. Load students (DB + Sheet merged via `_get_loaded_students()`)
2. Each student gets own `threading.Thread` + own Chrome browser (parallel)
3. For each student: navigate to level URL → wait/poll for booking button → CAS login → 5-step wizard
4. Wizard steps: Personal Data 1 → Personal Data 2 → Payment (Invoice) → Promo Code → Review & Confirm
5. Status pushed via WebSocket to frontend live dashboard

### Schedule Fetch Chain
1. **ScrapingBee** (premium_proxy=true) — primary, ~15s per 3 levels parallel
2. **curl_cffi** (chrome131 impersonate) — fallback if ScrapingBee fails
3. **Playwright** (headless Chromium) — fallback if curl_cffi unavailable
4. **pk_fallback.json** — last resort offline data

### Google Sheets 429 Handling
- `_retry_gsheet()`: 5s → 10s → 20s → 40s exponential backoff
- 15s TTL in-memory cache on `load_sheet_data()` to reduce read frequency
- `strict=False` on data validation dropdown to avoid red dot on existing values

## Common Issues

### "Delete failed: Unexpected token '<'"
**Cause**: Student missing `id` field → URL `/api/students/undefined` → HTML 404
**Fix**: All students now get an id (positive for DB, negative for sheet/config). Already fixed.

### "Quota exceeded for quota metric 'Read requests'"
**Cause**: Google Sheets 60 reads/min/user limit exceeded
**Fix**: Retry with backoff + 15s cache. If persistent, wait 1 min.

### Schedule returns 0 entries
**Cause**: ScrapingBee monthly limit, Playwright browsers not installed, or Goethe API blocking
**Fix**: Fallback to `pk_fallback.json`. If ScrapingBee exhausted, replace API key.

### Bot timing — "5-10 min per student?"
**Reality**: ~1.5-2 min per student when booking open. Parallel for multiple students (same total time).

## Deployment Notes
- Railway auto-deploys from GitHub `main` branch pushes (uses Railway API token from GitHub secret)
- Railway env vars picked up on next deploy (not hot-reloaded)
- **Vercel frontend** — https://goethe-booking-dashboard.vercel.app
- Frontend is pure HTML/CSS/JS — no build step needed
- Backend uses **Postgres** (`database.py`) via `DATABASE_URL` — data persists across restarts
- Local dev uses SQLite (`db.py`) when `DATABASE_URL` not set

## Env Vars (Railway)
| Var | Value/Purpose |
|-----|---------------|
| `DATABASE_URL` | `postgresql://postgres:REDACTED@postgres.railway.internal:5432/railway` |
| `SCRAPINGBEE_API_KEY` | `REDACTED` |
| `AUTH_EMAIL` | `hamzarafiq655@gmail.com` |
| `AUTH_PASSWORD` | `REDACTED` |
| `GOOGLE_SERVICE_ACCOUNT_B64` | Base64-encoded service account JSON |
| `VERCEL_ORG_ID` | `team_e9xBdY5fOoQQDcyJtoPIkfAW` |
| `VERCEL_PROJECT_ID` | `prj_c6bzqPz9vMhYVl24HPhtKYLbKqzg` |
| `ACTIVE_HOURS_START` | `07:00` (PKT, default) |
| `ACTIVE_HOURS_END` | `20:00` (PKT, default) |
| `REQUEUE_MAX_RETRIES` | `3` (default) |
| `REQUEUE_DELAY_SECONDS` | `300` (5 min, default) |
| `RAILWAY_API_TOKEN` | `REDACTED` (CI/CD) |

## Todo / Known Gaps
- [x] **Postgres connected** (June 30) — `DATABASE_URL` set, `psycopg2-binary` in requirements
- [x] **Post-booking verification** — `verify_booking()` checks mein.goethe.de profile
- [x] **Session refresh** — `_ensure_session()` before each wizard step
- [x] **Failure evidence** — `save_failure_evidence()` captures screenshot + HTML
- [x] **Student retry** — re-queue failed students up to 3 times
- [x] **Scheduled polling** — `is_active_hours()` quiet hours (7pm-7am PKT)
- [ ] Priority Queue — order students by booking_datetime proximity
- [ ] Slot Pre-check — fast API/selenium check before full booking flow
- [ ] Browser Profiles — persistent Chrome profiles to avoid re-login
- [ ] Confirmation Capture — extract PTN/booking ref from confirmation page
- [ ] Notifications — Telegram/email on successful booking
- [ ] Concurrent Booking — rate-limit parallel students
- [ ] Selector Health Check — auto-detect stale CSS selectors
- [ ] Postgres Backups — automated DB snapshots
- [ ] India adaptation: change `/ins/pk/` to `/ins/in/`, add `undetected-chromedriver`, Indian proxies
- [ ] Google Sheets append_student doesn't retry on 429
- [ ] No automated tests for the booking flow (only scrapers and helpers tested)
