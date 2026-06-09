#!/usr/bin/env python3
"""
Goethe Booking Bot - API Backend
=================================
Flask-based API for the standalone frontend.

Deploy backend anywhere (Railway, Render, Fly.io, VPS).
Frontend (frontend/index.html) deploys on Netlify.

Usage:
  pip install flask
  python webapp.py

Frontend connects via Backend URL input.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional

import flask
from flask import Flask, Response, jsonify, request

PROJECT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_DIR))

import booking_helper as bot

app = Flask(__name__)

# ── Global state ──
bot_stop_event = threading.Event()
bot_thread: Optional[threading.Thread] = None
bot_running = False
log_queue: queue.Queue = queue.Queue()
student_status: Dict[str, Dict] = {}  # name -> {status, color, details}
student_results: List[Dict] = []
config_path: str = ""
telegram_token: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
telegram_chat_id: str = os.environ.get("TELEGRAM_CHAT_ID", "")


class WebLogHandler(logging.Handler):
    def __init__(self, lq: queue.Queue):
        super().__init__()
        self.lq = lq

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        self.lq.put({"time": record.asctime if hasattr(record, 'asctime') else '',
                     "level": record.levelname,
                     "message": msg,
                     "name": record.name})


def setup_web_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = WebLogHandler(log_queue)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger


def run_students_web(students: List[Dict], headless: bool):
    global bot_stop_event, bot_running, student_status, student_results
    bot_stop_event.clear()
    bot_running = True

    master_logger = setup_web_logger("web_bot")
    master_logger.info("Bot started with %d student(s)", len(students))

    threads = []
    results_lock = threading.Lock()

    def run_one(s: Dict):
        name = s.get("name", "Unknown")
        student_logger = setup_web_logger(f"bot_{name}")
        student_status[name] = {"status": "Waiting...", "color": "warning", "details": "Polling for slot"}

        result = bot.run_student_flow(
            s, use_headless=headless,
            logger=student_logger,
            stop_event=bot_stop_event,
        )
        with results_lock:
            student_results.append(result)

        status = result.get("status", "failed")
        if status == "confirmed":
            student_status[name] = {"status": "Confirmed!", "color": "success", "details": f"Ref: {result.get('reference', 'N/A')}"}
        elif status == "submitted":
            student_status[name] = {"status": "Submitted", "color": "success", "details": "Form submitted"}
        elif status == "stopped":
            student_status[name] = {"status": "Stopped", "color": "danger", "details": "Cancelled by user"}
        elif status == "failed":
            student_status[name] = {"status": "Failed", "color": "danger", "details": "Error occurred"}
        else:
            student_status[name] = {"status": status, "color": "warning", "details": ""}

    for s in students:
        name = s.get("name", "Unknown")
        student_status[name] = {"status": "Starting...", "color": "info", "details": "Launching browser"}
        t = threading.Thread(target=run_one, args=(s,), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    bot_running = False
    master_logger.info("All students finished")
    log_queue.put(None)  # Signal SSE stream to end


# ── CORS (allow frontend from anywhere) ──
@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


# ── Routes ──

@app.route("/")
@app.route("/health")
def health():
    return jsonify({"status": "ok", "running": bot_running})


@app.route("/api/status")
def api_status():
    return jsonify({
        "running": bot_running,
        "students": [
            {
                "name": s.get("name", "?"),
                "level": s.get("exam_level", "?"),
                "city": s.get("city", "?"),
                "booking_time": s.get("booking_datetime", "?"),
                "status": student_status.get(s.get("name", ""), {}).get("status", "Not started"),
                "color": student_status.get(s.get("name", ""), {}).get("color", "secondary"),
                "details": student_status.get(s.get("name", ""), {}).get("details", ""),
            }
            for s in _get_loaded_students()
        ],
        "config_loaded": len(_get_loaded_students()) > 0,
    })


@app.route("/api/config", methods=["GET"])
def api_get_config():
    students = _get_loaded_students()
    return jsonify({
        "path": config_path,
        "count": len(students),
        "students": [
            {k: v for k, v in s.items()}
            for s in students
        ],
    })


@app.route("/api/config/load", methods=["POST"])
def api_load_config():
    global config_path
    data = request.get_json(silent=True) or {}
    path = data.get("path", str(PROJECT_DIR / "config.csv"))
    if not Path(path).exists():
        return jsonify({"ok": False, "error": "File not found"}), 400
    try:
        bot.load_all_students(path)
        config_path = path
        return jsonify({"ok": True, "path": path, "count": len(bot.load_all_students(path))})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/config/upload", methods=["POST"])
def api_config_upload():
    global config_path
    csv_content = request.get_data(as_text=True)
    if not csv_content.strip():
        return jsonify({"ok": False, "error": "Empty CSV data"}), 400
    try:
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".csv"))
        tmp.write_text(csv_content, encoding="utf-8")
        students = bot.load_all_students(str(tmp))
        config_path = str(tmp)
        return jsonify({"ok": True, "count": len(students), "students": [{k: v for k, v in s.items()} for s in students]})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/start", methods=["POST"])
def api_start():
    global bot_thread

    if bot_running:
        return jsonify({"ok": False, "error": "Bot is already running"}), 400

    students = _get_loaded_students()
    if not students:
        return jsonify({"ok": False, "error": "No students loaded. Load a config.csv first"}), 400

    data = request.get_json(silent=True) or {}
    headless = data.get("headless", not os.environ.get("DISPLAY"))
    if not headless and not os.environ.get("DISPLAY"):
        headless = True

    global telegram_token, telegram_chat_id
    telegram_token = data.get("telegram_token", telegram_token)
    telegram_chat_id = data.get("telegram_chat_id", telegram_chat_id)

    bot.TELEGRAM_BOT_TOKEN = telegram_token
    bot.TELEGRAM_CHAT_ID = telegram_chat_id

    global student_status, student_results
    student_status.clear()
    student_results.clear()

    # Clear log queue
    while not log_queue.empty():
        try:
            log_queue.get_nowait()
        except queue.Empty:
            break

    bot_thread = threading.Thread(target=run_students_web, args=(students, headless), daemon=True)
    bot_thread.start()

    return jsonify({"ok": True, "message": f"Started bot for {len(students)} student(s)"})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    if not bot_running:
        return jsonify({"ok": False, "error": "Bot is not running"}), 400
    bot_stop_event.set()
    return jsonify({"ok": True, "message": "Stop signal sent"})


@app.route("/api/logs")
def api_logs():
    def generate():
        while True:
            try:
                record = log_queue.get(timeout=30)
                if record is None:
                    break
                yield f"data: {json.dumps(record)}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/results")
def api_results():
    return jsonify(student_results)


@app.route("/api/schedule")
def api_schedule():
    return jsonify(bot.get_schedule())


def _get_loaded_students() -> List[Dict]:
    global config_path
    if not config_path or not Path(config_path).exists():
        return []
    try:
        return bot.load_all_students(config_path)
    except Exception:
        return []


def main():
    global config_path
    default_cfg = PROJECT_DIR / "config.csv"
    if default_cfg.exists():
        config_path = str(default_cfg)

    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")

    public_url = f"http://localhost:{port}" if host == "0.0.0.0" else f"http://{host}:{port}"

    print("=" * 55)
    print("  Goethe Booking Bot - Web Control Panel")
    print()
    print(f"  Local:   http://localhost:{port}")
    print(f"  Network: http://{host}:{port}")
    print()
    print("  Use ngrok for a public URL:")
    print("    ngrok http http://localhost:{port}")
    print()
    print("  Deploy on Railway / Fly.io / Render:")
    print("    Set PORT env to your port (default 5000)")
    print("=" * 55)
    print("  Press Ctrl+C to stop the server")

    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
