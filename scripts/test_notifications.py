"""Send a test alert through every configured channel to verify delivery.

Exercises the same path the bot uses (notifications.notify_all): Telegram, email,
and the optional generic webhook. Run it wherever the bot runs (Railway shell,
VPS, or locally) with the relevant env vars set.

Usage:
  # Telegram
  TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python scripts/test_notifications.py
  # Webhook (SMS/call bridge)
  ALERT_WEBHOOK_URL=... python scripts/test_notifications.py
"""
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import notifications

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("notif_test")

configured = []
if notifications.TELEGRAM_BOT_TOKEN and notifications.TELEGRAM_CHAT_ID:
    configured.append("telegram")
if all([notifications.EMAIL_SMTP_HOST, notifications.EMAIL_USER, notifications.EMAIL_PASS, notifications.EMAIL_TO]):
    configured.append("email")
if notifications.ALERT_WEBHOOK_URL:
    configured.append("webhook")

if not configured:
    print("No notification channels configured. Set at least one of:")
    print("  TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID")
    print("  EMAIL_SMTP_HOST + EMAIL_USER + EMAIL_PASS + EMAIL_TO")
    print("  ALERT_WEBHOOK_URL")
    sys.exit(1)

print(f"Configured channels: {', '.join(configured)}")
print("Sending test alert via notify_all()...")
notifications.notify_all(
    "Goethe Bot — Test Alert",
    "If you received this, notifications are working. (test_notifications.py)",
    logger,
)
print("Done. Check the channel(s) above for the message.")
print("Note: per-channel success/failure is logged above (e.g. 'Telegram sent').")
