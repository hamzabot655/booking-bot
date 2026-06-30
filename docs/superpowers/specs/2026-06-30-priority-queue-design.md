# Priority Queue — Design Doc

## Problem
Students are processed in source order (CSV → DB → Sheets) regardless of their `booking_datetime`. A student with a 10:00 slot might get its thread created after a student with a 15:00 slot, wasting critical early-window time on thread creation overhead.

## Approach (Option A: Simple Sort)
Sort the merged student list by `booking_datetime` (ascending) before spawning threads. Students whose booking window opens earliest get their threads created first. Each thread still independently waits in `scheduled_wait()`, so no functional change to the booking logic — only the startup order changes.

## Changes
- `webapp.py` — `_get_loaded_students()`: add `sorted(..., key=lambda s: s.get("booking_datetime", ""))` before returning
- `webapp.py` — `api_start()`: add same sort after optional level filter
- `webapp.py` — `start_bot_from_telegram()`: already uses `_get_loaded_students()` → automatically benefits

## Edge Cases Handled
- Missing/empty `booking_datetime` → sorted to end (empty string sorts last)
- Students with identical `booking_datetime` → preserve existing order (stable sort)
- Malformed datetime → no crash, just sorted as string (lexicographic order works for ISO format)
- Level filter applied before sort → correct: filtered students then sorted

## Files Changed
- `webapp.py` — 2 sort calls, ~6 lines total

## Testing
- Existing tests cover thread spawning behavior
- Manual verify: `/api/start` students appear in datetime order in logs
