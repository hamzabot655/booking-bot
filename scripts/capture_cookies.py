"""Capture Goethe session cookies from your laptop and upload to Railway.
Run ONCE from your home laptop (clean IP). After this, the bot on Railway can reuse
these cookies and skip the login page entirely.

Usage:
  1. Open the dashboard, login, copy the auth token from browser devtools
  2. python scripts/capture_cookies.py --email student@gmail.com --password 'student_pw' --token 'auth_token'

Or if already logged into the dashboard:
  python scripts/capture_cookies.py --email student@gmail.com --password 'student_pw'
  (it will ask for the dashboard URL and auth token interactively)
"""
import sys, os, time, json, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import urllib.request
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("capture_cookies")

parser = argparse.ArgumentParser(description="Capture Goethe cookies to use on Railway")
parser.add_argument("--email", help="Goethe student email")
parser.add_argument("--password", help="Goethe student password")
parser.add_argument("--token", help="Dashboard auth token (from browser devtools)")
parser.add_argument("--railway", default="https://goethe-booking-bot-production-21af.up.railway.app",
                    help="Railway backend URL")
args = parser.parse_args()

EMAIL = args.email or os.environ.get("GOETHE_EMAIL", "") or input("Goethe email: ").strip()
PASSWORD = args.password or os.environ.get("GOETHE_PASSWORD", "") or input("Goethe password: ").strip()
RAILWAY_URL = args.railway or input(f"Railway URL [{args.railway}]: ").strip() or args.railway
AUTH_TOKEN = args.token or input("Dashboard auth token: ").strip()

if not EMAIL or not PASSWORD:
    print("\n❌ Email and password required")
    sys.exit(1)

print("\nOpening Chrome browser...")
options = Options()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1280,900")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--lang=en-US,en")

print("✓ Browser opened")
print(f"→ Navigating to Goethe login page...")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
try:
    driver.get("https://login.goethe.de/cas/login")
    time.sleep(2)

    print("→ Logging in...")
    email_el = driver.find_element(By.CSS_SELECTOR, "input[type='email'], input[name='username']")
    email_el.clear()
    email_el.send_keys(EMAIL)
    time.sleep(0.5)

    pwd_el = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pwd_el.clear()
    pwd_el.send_keys(PASSWORD)
    time.sleep(0.3)

    submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit.click()
    time.sleep(5)

    current = driver.current_url.lower()
    if "login" in current:
        print("\n❌ Login failed — still on login page")
        print("   Check your email/password or try manually in the browser window")
        sys.exit(1)

    print(f"\n✓ Login successful! URL: {current[:80]}")
    time.sleep(2)

    cookies = driver.get_cookies()
    print(f"✓ Captured {len(cookies)} cookies")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}",
    }
    data = json.dumps({"cookies": cookies}).encode()
    req = urllib.request.Request(
        f"{RAILWAY_URL}/api/goethe-cookies",
        data=data, headers=headers, method="POST"
    )
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read())

    if result.get("ok"):
        print(f"\n✅ {result['count']} cookies saved to Railway!")
        print("→ Bot on Railway will now reuse these cookies (no login needed)")
        print("→ Cookies expire ~24h — run this script again when they expire")
    else:
        print(f"\n❌ Failed: {result.get('error', 'Unknown')}")

except Exception as e:
    print(f"\n❌ Error: {e}")
finally:
    driver.quit()
