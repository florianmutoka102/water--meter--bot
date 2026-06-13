import threading
import requests
import time
import os

def keep_alive():
    url = os.environ.get("RENDER_EXTERNAL_URL", "https://water-meter-bot-yd3y.onrender.com")
    while True:
        try:
            requests.get(url)
            print(f"✅ Keep alive ping sent to {url}")
        except Exception as e:
            print(f"❌ Keep alive error: {e}")
        time.sleep(840)  # ping every 14 minutes

def start_keep_alive():
    t = threading.Thread(target=keep_alive)
    t.daemon = True
    t.start()
