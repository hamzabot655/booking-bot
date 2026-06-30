# AGENTS.md — Goethe Booking Bot

## Session Context (June 30, 2026 — Part 4 — Full Cleanup)
- **CRITICAL BUG FIXED**: Login returned HTML (`"Unexpected token '<'"`) because `database.py` defined `init_db()` but NEVER called it — PostgreSQL tables (sessions, audit_log) didn't exist, login crashed on first DB write → unhandled 500 → Flask HTML error page
- **Fixes applied**: Added `init_db()` call in `database.py` at module level; added `@app.errorhandler(500)` and `@app.errorhandler(405)` to return JSON for API routes; fixed service worker to skip cross-origin API calls
- **Vercel fully cleaned**: ALL projects deleted from Hamza's Vercel account. Fresh project `goethe-frontend-v2` created from scratch. SPA routing fixed with `vercel.json` rewrites. Old domain `goethe-booking-dashboard.vercel.app` cannot be re-used (Vercel SSO intercepts deleted project names) — using `goethe-frontend-v2.vercel.app` as primary URL.
- **All changes pushed to GitHub** with classic token.
- **GitHub secret updated**: `VERCEL_PROJECT_ID` = `prj_jRIrDFcw3I2SDoAWEW78OGpIB0LY`

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
| Frontend | https://goethe-frontend-v2.vercel.app |
| Backend | https://goethe-booking-bot-production-21af.up.railway.app |
| GitHub | https://github.com/hamzabot655/booking-bot |

## Credentials
- **Auth login**: AUTH_EMAIL=`hamzarafiq655@gmail.com` / AUTH_PASSWORD=`Hamza@123` (Railway env vars)
- **ScrapingBee API**: RZCBXGW6IV3KM9YWEDPHGYG5GZGOKBUEM1Z2YC3XQIZYYMHVTI3LX6X3J0RRP9FXLTBJCIAQP1GWA3R1 (set via `SCRAPINGBEE_API_KEY` env var)
- **Google Sheet ID**: `1C7VD_52VnGmJqYSQGtdNzBZGekvCRHWUrdZCgTvvhAY` (`GOOGLE_SHEET_ID` env var)
- **Google Service Account**: Base64 in `GOOGLE_SERVICE_ACCOUNT_B64` env var

## Railway Project
- **Project**: hospitable-heart (ID: 520adb72-b1f4-4021-8c4b-21ca81f8a901)
- **Service**: goethe-booking-bot (ID: f568e242-4d2a-4b44-8205-07899abfbd26)
- **Environment**: production (ID: 20945f76-1cfa-4e38-b50b-a5cb8d5f47cd)
- **Region**: sfo
- **Database**: Postgres — internal URL `postgresql://postgres:WnUmpbOFrLLwToMsbXmyvGZnMPebYwvK@postgres.railway.internal:5432/railway` set via `DATABASE_URL` env var
- **API Token**: `bd239e8f-cf61-4d16-8521-7c48924ec745` (long-lived, set as GitHub secret)

## File Map
| File | Purpose |
|------|---------|
| `webapp.py` | Flask backend — API endpoints, CORS, auth, bot control |
| `booking_helper.py` | Core Selenium bot — login, 5-step wizard, smart_retry, polling |
| `goethe_scraper.py` | Pakistan exam schedule scraper — ScrapingBee → curl_cffi → Playwright → fallback |
| `google_sheets.py` | Google Sheets integration — read/write students, auto-fill dates, update schedule tab |
| `database.py` | Postgres DB via SQLAlchemy — runs `init_db()` on import (critical bug fixed June 30) |
| `db.py` | SQLite DB — students, logs, settings tables (local dev only) |
| `frontend/index.html` | Single-page dashboard — 6 sections (Dashboard, Controls, Schedule, Students, Logs, Settings) |
| `frontend/sw.js` | Service worker — fixed to skip cross-origin + `/api/` requests (was intercepting API calls) |
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
- **Vercel frontend** — https://goethe-frontend-v2.vercel.app (was goethe-booking-dashboard.vercel.app — domain not reusable after project deletion)
- Frontend is pure HTML/CSS/JS — no build step needed. SPA routing via `vercel.json` rewrites.
- Backend uses **Postgres** (`database.py`) via `DATABASE_URL` — data persists across restarts
- Local dev uses SQLite (`db.py`) when `DATABASE_URL` not set

## Env Vars (Railway)
| Var | Value/Purpose |
|-----|---------------|
| `DATABASE_URL` | `postgresql://postgres:WnUmpbOFrLLwToMsbXmyvGZnMPebYwvK@postgres.railway.internal:5432/railway` |
| `SCRAPINGBEE_API_KEY` | `RZCBXGW6IV3KM9YWEDPHGYG5GZGOKBUEM1Z2YC3XQIZYYMHVTI3LX6X3J0RRP9FXLTBJCIAQP1GWA3R1` |
| `AUTH_EMAIL` | `hamzarafiq655@gmail.com` |
| `AUTH_PASSWORD` | `Hamza@123` |
| `GOOGLE_SERVICE_ACCOUNT_B64` | Base64-encoded service account JSON |
| `VERCEL_ORG_ID` | `team_e9xBdY5fOoQQDcyJtoPIkfAW` |
| `VERCEL_PROJECT_ID` | `prj_jRIrDFcw3I2SDoAWEW78OGpIB0LY` (current — goethe-frontend-v2) |
| `ACTIVE_HOURS_START` | `07:00` (PKT, default) |
| `ACTIVE_HOURS_END` | `20:00` (PKT, default) |
| `REQUEUE_MAX_RETRIES` | `3` (default) |
| `REQUEUE_DELAY_SECONDS` | `300` (5 min, default) |
| `RAILWAY_API_TOKEN` | `bd239e8f-cf61-4d16-8521-7c48924ec745` (CI/CD) |

## Todo / Known Gaps

### ✅ Done (Part 4 — this session)
- [x] **All local fixes pushed to GitHub** (init_db, checkpoint/status fix, db.py cleanup)
- [x] **All Vercel projects deleted** (goethe-frontend-v2, frontend), fresh project created
- [x] **SPA routing fixed** — `vercel.json` rewrites handle subpaths (settings, logs, etc. → index.html)
- [x] **Frontend deployed** at https://goethe-frontend-v2.vercel.app
- [x] **GitHub secret `VERCEL_PROJECT_ID` updated** to new project ID

### ✅ Done (Part 3 — previous session)
- [x] **Login HTML bug fixed** — `database.py` now calls `init_db()` at module level
- [x] **Service worker fixed** — no longer intercepts cross-origin or `/api/` fetch requests
- [x] **Vercel restored** after corruption

### ✅ Done (earlier sessions)
- [x] Priority Queue — sort students by booking_datetime
- [x] Browser Profiles — reuse Chrome profile per student
- [x] Concurrent Booking — semaphore max 2 parallel
- [x] Selector Health Check — /api/health
- [x] Google Sheets retry — _retry_gsheet with backoff
- [x] Vercel migration from Netlify
- [x] Postgres connected
- [x] Post-booking verification
- [x] Session refresh before each wizard step
- [x] Failure evidence (screenshot + HTML)
- [x] Student retry up to 3x
- [x] Scheduled booking window check
- [x] Confirmation Capture
- [x] Slot Pre-check
- [x] Notifications (Telegram/Email)
- [x] Postgres Backups (Railway natively handles)

### ⬜ Still Pending
- [ ] **VERCEL_PROJECT_ID GitHub secret needs update** — still points to deleted old project, GH Actions deploy-vercel job will fail
- [ ] SPA routing for direct subpath URLs (e.g., `/logs`, `/settings`) — may 404 on Vercet
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
- [ ] Live booking test — cannot test until next booking window opens
- [ ] No automated tests for the booking flow (only scrapers and helpers tested)
