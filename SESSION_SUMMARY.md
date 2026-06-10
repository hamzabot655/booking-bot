# Goethe Booking Bot — Session Summary (Updated 11 Jun 2026 v3)

## Project
Automated bot for booking Goethe-Institut Pakistan German language exams (A1, A2, B1) — multi-student, multi-city.

## Session Files (new this session)
| File | Purpose |
|------|---------|
| `C:\Users\brosp\AppData\Local\Temp\opencode\make_pdf.py` | PDF presentation generator (fpdf2 + Inter font) |
| `C:\Users\brosp\Downloads\Goethe Bot Presentation.pdf` | Client pitch presentation for Hamza (12 slides, v6) |
| `C:\Users\brosp\AppData\Local\Temp\opencode\Inter-Regular.ttf` | Inter Regular font (downloaded from Google Fonts) |
| `C:\Users\brosp\AppData\Local\Temp\opencode\Inter-Bold.ttf` | Inter Bold font (downloaded from Google Fonts) |

## User
- GitHub: `abeermeer`
- Goethe My Goethe.de: `student@example.com` / `GOETHE_PASSWORD_REDACTED`
- 3 students: A1 Karachi, A2 Lahore, B1 Karachi
- A1 & B1 Karachi + A2 Lahore bookable from July 17, 2026
- Python: `C:\Users\brosp\AppData\Local\Programs\Python\Python312\python.exe`
- Project dir: `C:\Users\brosp\Downloads\goethe-bot` (also `AppData\Local\Temp\opencode\goethe-bot`)
- Platform: Windows

## Deployments
| Service | URL | Status |
|---------|-----|--------|
| **Frontend (Netlify)** | https://aesthetic-alpaca-769b17.netlify.app | ✅ Live |
| **Backend (Railway)** | https://goethe-booking-bot-production-a6a6.up.railway.app | ✅ Online (fixed) |
| **GitHub** | https://github.com/abeermeer/goethe-booking-bot | ✅ Latest code pushed |
| **Custom Domain** | User purchased a domain — needs to connect to Netlify | ⏳ Pending |

## Presentation
- **File:** `C:\Users\brosp\Downloads\Goethe Bot Presentation.pdf` (client pitch for Hamza)
- **Font:** Inter (embedded) — `C:\Users\brosp\AppData\Local\Temp\opencode\Inter-*.ttf`
- **Generator script:** `C:\Users\brosp\AppData\Local\Temp\opencode\make_pdf.py`
- **Latest version:** v6 — 12 slides, dark theme, professional design with dashboard mockup, phone+desktop mockup, workflow diagram, speed table, architecture flow
- **Versions created:** v1 (basic) → v2 (bigger fonts, rounded corners) → v3 (fixed naming conflicts) → v4 (width-aware text, no overlap) → v5 (clean light theme) → v6 (advanced diagrams, mockups)
- **Status:** User took the latest version, will finalize manually (adding images, fixing text overflow, adjusting font sizes)

## What's Fixed This Session (11 Jun v1)
- **Level field mismatch** — CSV header was `level` but code read `exam_level` → all students showed A1. Fixed: `student.get("level", student.get("exam_level", ""))` in booking_helper.py, webapp.py, gui.py, frontend
- **Chrome OOM crash** — 3 Chrome instances on 512MB RAM killed each other at simultaneous launch. Fixed: auto-retry `create_driver` up to 3 times with 5s delay
- **Logger handler overwrite** — all 3 students used logger name `bot_Abeer Meer`, causing `handlers.clear()` to drop logs from previous students. Fixed: unique logger names per student (`bot_{name}_{level}`)
- **Status key collision** — `student_status` dict used `name` as key, so all 3 "Abeer Meer" entries overwrote each other. Fixed: compound key `name|level|city`

## What's Done This Session (11 Jun v2 — Presentation & Misc)
- **Created client pitch presentation** for Hamza — 6 iterations (v1→v6) using fpdf2 + Inter font
  - v1: basic text
  - v2: bigger fonts, rounded corners
  - v3: fixed naming conflicts with fpdf2 methods
  - v4: width-aware text, zero overlap
  - v5: clean light theme, simple
  - v6: advanced dark theme with dashboard mockup, phone+desktop mockup, workflow diagram, speed table, architecture flow
  - User took v6, will finalize manually (adding images, fixing text overflow, font sizes)
- **Explained polling constants** in booking_helper.py — which timings control what, how to optimize, realistic limits
- **Discussed testing strategy** — local test HTML page vs pointing to current bookable Goethe page
- **Discussed frontend improvements** — current UI rated 5.5/10, may revisit later
- **Made GitHub repo private** — repo is now PRIVATE, only user can see it
- **No code changes to core project files** (booking_helper.py, webapp.py etc.)

## Current Config (3 students)
| Name | Level | City | Booking DateTime |
|------|-------|------|-----------------|
| Abeer Meer | A1 | Karachi | 2026-07-17T10:00:00 |
| Abeer Meer | A2 | Lahore | 2026-07-17T10:05:00 |
| Abeer Meer | B1 | Karachi | 2026-07-17T10:10:00 |

## Bot Behavior
- Starts polling 10s before booking time (burst mode: every 2-3s)
- Normal mode: polls every 45s
- Finds "Book Now" button by text matching (book, next, buchen, weiter)
- Clicks button → CAS login (My Goethe.de) → fills registration form → submits
- Captures confirmation screenshot
- Stops gracefully via stop event
- Each student runs in separate thread with separate Chrome profile
- Chrome auto-retries on launch failure (3 attempts, 5s apart)

## Key Files
| File | Purpose |
|------|---------|
| `booking_helper.py` | Core bot engine (Selenium, multi-student, polling, retry logic) |
| `webapp.py` | Flask backend API (start/stop/status/logs/results/schedule) |
| `frontend/index.html` | Web dashboard (Netlify) |
| `config.csv` | Student credentials (`.gitignore`'d) |
| `Dockerfile` | Container definition (python:3.12-slim + google-chrome-stable) |
| `gui.py` | Alternative Tkinter desktop GUI (not deployed) |
| `SESSION_SUMMARY.md` | This file — full session memory for resume |

## CSV Format
```
name,email,password,level,city,booking_datetime,dob,place_of_birth,address,phone
```

## Registration Form Fields (confirmed by user)
1. Name (single field)
2. Date of Birth
3. Place of Birth
4. Address
5. Phone number
6. Level (A1/A2/B1 dropdown)

## Selectors (confirmed)
- `form_name` — single name input
- `form_place_of_birth` — place of birth input
- `form_level` — exam level dropdown
- Removed unused: form_firstname, form_lastname, form_gender, form_nationality, form_passport, form_cnic, form_city

## Known Issues
1. Railway free tier (512MB) barely handles 3 Chrome instances — retry logic helps but upgrade to $5 Starter for reliability
2. Chrome 148 + `--user-data-dir` + `excludeSwitches` still crashes on Windows — removed `excludeSwitches`

## Pre-July 17 Checklist
- [x] All code deployed to Railway
- [x] config.csv uploaded to Railway backend
- [x] Frontend deployed to Netlify
- [ ] Connect custom domain to Netlify (CNAME or nameservers)
- [ ] On July 17: open Netlify URL, click Start Bot 5-10 min before 10:00

## Netlify Deploy Token
`NETLIFY_DEPLOY_TOKEN_REDACTED`
Site ID: `NETLIFY_SITE_ID_REDACTED`

## Railway Token & IDs
- API Token: `1d7f1696-f7ca-4ffa-b00f-d53feb2caf3f`
- Project ID: `6aee17f5-fe9f-4496-a02d-e5f366d37c2a`
- Environment ID: `785a6cb2-284c-4e4a-b3cc-71afa8f24378`
- Service ID: `783d4933-1de1-45b6-a198-08b6f07692cd`

## Commands
```powershell
# Run locally
cd C:\Users\brosp\Downloads\goethe-bot
python webapp.py

# Deploy frontend
$env:NETLIFY_AUTH_TOKEN = "NETLIFY_DEPLOY_TOKEN_REDACTED"
netlify deploy --prod --dir frontend --site "NETLIFY_SITE_ID_REDACTED"

# Deploy backend to Railway
$env:RAILWAY_API_TOKEN = "1d7f1696-f7ca-4ffa-b00f-d53feb2caf3f"
railway up --detach --environment 785a6cb2-284c-4e4a-b3cc-71afa8f24378

# Upload config to Railway
$csv = Get-Content "config.csv" -Raw
Invoke-RestMethod -Uri "https://goethe-booking-bot-production-a6a6.up.railway.app/api/config/upload" -Method POST -Body $csv -ContentType "text/plain"

# Git
git add -A; git commit -m "message"; git push
```
