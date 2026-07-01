# VPS Setup — Bypass Railway reCAPTCHA for Goethe Login

Railway's datacenter IPs trigger Google reCAPTCHA on Goethe's CAS login, so the bot
can't log in from Railway. Running the backend on a clean-IP VPS (or via a residential
proxy) fixes this. This guide uses **Hetzner CPX11** (~€3.99/mo, 2 vCPU / 4 GB) on
Ubuntu 24.04, but any clean-IP Linux box works.

> The frontend stays on Vercel. Only the backend moves. After setup, point the dashboard's
> "Backend URL" at this VPS (or its domain) and update the backend's `_ALLOWED_ORIGINS`.

## 1. Provision
1. Create a Hetzner CPX11, Ubuntu 24.04, in a region with a residential-ish reputation.
2. Add your SSH key. Note the public IP.

## 2. One-shot install
SSH in as root and run:
```bash
curl -fsSL https://raw.githubusercontent.com/hamzabot655/booking-bot/main/deploy/vps_setup.sh | bash
```
Or copy `deploy/vps_setup.sh` up and run it. It installs Python 3.12, Google Chrome,
clones the repo to `/opt/goethe-bot`, creates a venv, installs deps + Playwright Chromium,
and installs a systemd service.

## 3. Configure env
```bash
sudo nano /opt/goethe-bot/.env     # fill AUTH_*, DATABASE_URL, FERNET_KEY, SCRAPINGBEE_API_KEY, etc.
sudo systemctl restart goethe-bot
```
Use the **same `DATABASE_URL`** (Railway Postgres public URL) and a **stable `FERNET_KEY`**
so existing data/passwords carry over.

## 4. Verify
```bash
systemctl status goethe-bot
curl -s http://localhost:5000/api/health
journalctl -u goethe-bot -f          # live logs
```

## 5. Expose it
- **Quick test:** `ngrok http 5000` → use the ngrok URL as the dashboard Backend URL.
- **Production:** put Nginx + Certbot in front for HTTPS on your domain, then add that
  origin to `_ALLOWED_ORIGINS` and the CSP `connect-src` in `webapp.py` and redeploy/restart.

## Alternatives to a VPS

### Residential proxy (keep running on Railway)
`PROXY_LIST` is comma-separated and applied to Chrome via `--proxy-server` in `create_driver`,
health-checked + rotated per attempt by `proxy_rotator.py`. **Important limitation:** Chrome's
`--proxy-server` **ignores inline `user:pass@` credentials**, so:
- ✅ **Use an IP-whitelisted residential proxy** — whitelist the Railway/VPS egress IP at the
  proxy provider, then set `PROXY_LIST=http://host:port` (no credentials). This works out of the box.
- ⚠️ **User/password proxies won't authenticate** through `--proxy-server` alone. To use one you'd
  need a proxy-auth Chrome extension, `selenium-wire`, or a local upstream (e.g. `gost`/`mitmproxy`)
  that injects the auth and exposes an unauthenticated local port to put in `PROXY_LIST`.
- Format: `PROXY_LIST=http://1.2.3.4:8000,http://5.6.7.8:8000`

### 2Captcha (automatic fallback)
Set `CAPTCHA_API_KEY`. The bot now detects a reCAPTCHA on the CAS login page and solves it via
2Captcha before submitting (`_login_attempt` → `detect_captcha`/`solve_captcha`). No-op without the key.

## Notes
- Chrome needs `--no-sandbox` (already set for non-Windows in `create_driver`).
- Keep the box awake; the bot must be running during the booking window.
- This does not change the TOS situation — automating Goethe registration still violates it.
