import asyncio
import base64
import json
import os
import threading
import time
from flask import Flask, render_template, request, session, redirect, url_for, Response
from flask_sock import Sock
from playwright.sync_api import sync_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-123")
sock = Sock(app)

# Password for access
ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD", "nikhil123")

# Global browser state
browser_state = {
    "playwright": None,
    "browser": None,
    "context": None,
    "page": None,
    "running": False,
    "lock": threading.Lock()
}

SESSION_FILE = "browser_session.json"

def start_browser():
    """Start Playwright browser with minimal RAM usage"""
    with browser_state["lock"]:
        if browser_state["running"]:
            return True
        try:
            pw = sync_playwright().start()
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--disable-sync",
                    "--disable-translate",
                    "--mute-audio",
                    "--no-first-run",
                    "--safebrowsing-disable-auto-update",
                    "--single-process",  # Important for low RAM
                    "--memory-pressure-off",
                    "--js-flags=--max-old-space-size=128",
                ]
            )

            # Load saved session if exists
            if os.path.exists(SESSION_FILE):
                context = browser.new_context(
                    storage_state=SESSION_FILE,
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                logger.info("Loaded saved session!")
            else:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )

            page = context.new_page()
            page.goto("https://www.google.com")

            browser_state["playwright"] = pw
            browser_state["browser"] = browser
            browser_state["context"] = context
            browser_state["page"] = page
            browser_state["running"] = True
            logger.info("Browser started successfully!")
            return True
        except Exception as e:
            logger.error(f"Browser start failed: {e}")
            return False

def save_session():
    """Save browser session/cookies"""
    try:
        if browser_state["context"]:
            browser_state["context"].storage_state(path=SESSION_FILE)
            logger.info("Session saved!")
    except Exception as e:
        logger.error(f"Session save failed: {e}")

def get_screenshot():
    """Get current page screenshot as base64 JPEG"""
    try:
        if browser_state["page"]:
            screenshot = browser_state["page"].screenshot(
                type="jpeg",
                quality=60,  # Lower quality = faster + less RAM
                full_page=False
            )
            return base64.b64encode(screenshot).decode()
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
    return None

# ─── Routes ───────────────────────────────────────────────

@app.route("/")
def index():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return render_template("browser.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ACCESS_PASSWORD:
            session["authenticated"] = True
            session.permanent = True
            # Start browser if not running
            if not browser_state["running"]:
                threading.Thread(target=start_browser, daemon=True).start()
            return redirect(url_for("index"))
        else:
            error = "Wrong password!"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/save-session")
def save_session_route():
    if not session.get("authenticated"):
        return {"error": "unauthorized"}, 401
    save_session()
    return {"status": "saved"}

# ─── WebSocket ────────────────────────────────────────────

@sock.route("/ws")
def websocket(ws):
    if not session.get("authenticated"):
        ws.close()
        return

    # Start browser if needed
    if not browser_state["running"]:
        start_browser()

    # Send screenshots in a thread
    stop_event = threading.Event()

    def send_frames():
        while not stop_event.is_set():
            try:
                img = get_screenshot()
                if img:
                    page = browser_state["page"]
                    url = page.url if page else ""
                    title = page.title() if page else ""
                    ws.send(json.dumps({
                        "type": "frame",
                        "data": img,
                        "url": url,
                        "title": title
                    }))
                time.sleep(0.15)  # ~6-7 FPS (light on server)
            except Exception as e:
                logger.error(f"Frame send error: {e}")
                break

    frame_thread = threading.Thread(target=send_frames, daemon=True)
    frame_thread.start()

    # Receive user events
    try:
        while True:
            msg = ws.receive()
            if not msg:
                break
            data = json.loads(msg)
            handle_event(data)
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        stop_event.set()

def handle_event(data):
    """Handle user input events"""
    page = browser_state["page"]
    if not page:
        return

    try:
        event_type = data.get("type")

        if event_type == "click":
            x, y = data["x"], data["y"]
            page.mouse.click(x, y)

        elif event_type == "dblclick":
            x, y = data["x"], data["y"]
            page.mouse.dblclick(x, y)

        elif event_type == "mousemove":
            x, y = data["x"], data["y"]
            page.mouse.move(x, y)

        elif event_type == "keydown":
            key = data.get("key", "")
            if key:
                page.keyboard.press(key)

        elif event_type == "type":
            text = data.get("text", "")
            if text:
                page.keyboard.type(text)

        elif event_type == "scroll":
            x, y = data["x"], data["y"]
            dx, dy = data.get("dx", 0), data.get("dy", 0)
            page.mouse.wheel(dx, dy)

        elif event_type == "navigate":
            url = data.get("url", "")
            if url:
                if not url.startswith("http"):
                    url = "https://" + url
                page.goto(url, wait_until="domcontentloaded", timeout=15000)

        elif event_type == "back":
            page.go_back()

        elif event_type == "forward":
            page.go_forward()

        elif event_type == "refresh":
            page.reload()

        elif event_type == "save_session":
            save_session()

    except Exception as e:
        logger.error(f"Event handle error: {e}")

# ─── Startup ──────────────────────────────────────────────

if __name__ == "__main__":
    # Start browser at launch
    threading.Thread(target=start_browser, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
