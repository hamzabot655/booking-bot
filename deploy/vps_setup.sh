#!/usr/bin/env bash
# Goethe Booking Bot — VPS bootstrap (Ubuntu 22.04/24.04).
# Installs Python 3.12, Chrome, the app, and a systemd service.
# Usage:  sudo bash vps_setup.sh
set -euo pipefail

REPO="${REPO:-https://github.com/hamzabot655/booking-bot.git}"
APP_DIR="${APP_DIR:-/opt/goethe-bot}"
SERVICE="goethe-bot"

echo "== apt deps =="
apt-get update
apt-get install -y --no-install-recommends \
  git curl wget gnupg ca-certificates xvfb \
  python3 python3-venv python3-pip

echo "== Google Chrome =="
if ! command -v google-chrome >/dev/null 2>&1; then
  wget -q -O - https://dl.google.com/linux/linux_signing_key.pub \
    | gpg --dearmor > /usr/share/keyrings/chrome-key.gpg
  echo "deb [signed-by=/usr/share/keyrings/chrome-key.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list
  apt-get update
  apt-get install -y --no-install-recommends google-chrome-stable
fi

echo "== clone / update repo =="
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO" "$APP_DIR"
fi

echo "== venv + deps =="
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
"$APP_DIR/.venv/bin/python" -m playwright install chromium || true

echo "== .env scaffold =="
if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo "  -> edit $APP_DIR/.env (AUTH_*, DATABASE_URL, FERNET_KEY, SCRAPINGBEE_API_KEY...)"
fi

echo "== systemd service =="
cat > "/etc/systemd/system/${SERVICE}.service" <<UNIT
[Unit]
Description=Goethe Booking Bot backend
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
Environment=PORT=5000 HOST=0.0.0.0 DISPLAY=:99
ExecStartPre=/usr/bin/bash -c 'Xvfb :99 -screen 0 1280x720x24 &>/dev/null & sleep 1'
ExecStart=${APP_DIR}/.venv/bin/python ${APP_DIR}/webapp.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"

echo "== done =="
echo "Edit ${APP_DIR}/.env then: systemctl restart ${SERVICE}"
echo "Health: curl -s http://localhost:5000/api/health"
echo "Logs:   journalctl -u ${SERVICE} -f"
