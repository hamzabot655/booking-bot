# Priority Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sort students by `booking_datetime` so earlier booking windows get processed first.

**Architecture:** Add `sorted()` call with `booking_datetime` as sort key in two places: `_get_loaded_students()` (source merge) and `api_start()` (after level filter). Telegram commander path automatically benefits from `_get_loaded_students()` change.

**Tech Stack:** Python 3.12, Flask

---

## Tasks

### Task 1: Sort in `_get_loaded_students()`

**File:** `webapp.py`

Find `return students` at end of `_get_loaded_students()` (around line 1389). Change to:

```python
return sorted(students, key=lambda s: s.get("booking_datetime", "") or "")
```

Empty/missing `booking_datetime` sorts after all valid datetimes (empty string < any non-empty string in Python is False, but `"" or ""` keeps it empty, and `""` < "2026-..." is True, so empty goes first... wait, that's not what we want.

Let me think: `sorted()` uses `<` comparison. Empty string `""` compared to ISO datetime string `"2026-07-17T10:00"`: Python string comparison compares lexicographically. `"" < "2"` is True (empty string is less than any non-empty string). So empty booking_datetime would sort FIRST, which is the opposite of what we want.

Fix: make the key function return a default high-value string for empty/missing:

```python
key=lambda s: s.get("booking_datetime", "") or "9999-12-31T23:59"
```

This way:
- Empty string → coerced to `"9999-12-31T23:59"` → sorts last
- Valid datetime → sorts normally
- None → `or` triggers → `"9999-12-31T23:59"` → sorts last

### Task 2: Sort in `api_start()` after level filter

**File:** `webapp.py`

After the level filter block (around line 824), add sort:

```python
students = sorted(students, key=lambda s: s.get("booking_datetime", "") or "9999-12-31T23:59")
```

This ensures that even if `_get_loaded_students()` loses order through the filter, the final list is sorted.

### Task 3: Verify

- Read `webapp.py` around lines 1346-1389 and 790-853 to confirm both changes are correct
- Check for any other call site that iterates students and might need sorting

### Task 4: Commit

```bash
git add -A; git commit -m "feat: priority queue — sort students by booking_datetime before processing"
```
