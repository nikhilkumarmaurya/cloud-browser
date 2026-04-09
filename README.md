# ☁️ Cloud Browser — Personal Remote Browser

Apna personal cloud browser jo Render pe run hoga.
Ek baar login karo → session save karo → kisi bhi device se same state milega!

---

## 🚀 Render pe Deploy Karo (Step by Step)

### Step 1 — GitHub pe Upload Karo
1. GitHub pe naya repo banao (e.g. `cloud-browser`)
2. Yeh saari files upload karo:
   - `app.py`
   - `requirements.txt`
   - `build.sh`
   - `render.yaml`
   - `templates/login.html`
   - `templates/browser.html`

### Step 2 — Render pe Deploy
1. [render.com](https://render.com) pe jao → New Web Service
2. GitHub repo connect karo
3. Settings:
   - **Build Command:** `pip install -r requirements.txt && playwright install chromium && playwright install-deps chromium`
   - **Start Command:** `gunicorn app:app -k flask_sock.worker.Worker --workers 1 --bind 0.0.0.0:$PORT --timeout 300`
   - **Instance Type:** Free

### Step 3 — Environment Variables Set Karo
Render Dashboard → Environment mein yeh add karo:
```
ACCESS_PASSWORD = apna_password_yahan   ← ZAROOR CHANGE KARO
SECRET_KEY      = koi_bhi_random_string
```

### Step 4 — Done! 🎉
- URL milega: `https://cloud-browser-xxxx.onrender.com`
- Password daalo → Browser open!

---

## 💾 Session Save Kaise Karo

Kisi bhi site pe login karne ke baad:
1. Toolbar mein **💾 Save Session** button click karo
2. Session server pe save ho jayega
3. Ab kisi bhi device se open karo → already logged in!

---

## ⚠️ Important Notes

- **Render Free Tier** = Server 15 min inactivity ke baad sleep ho jata hai
  - Pehli baar load slow lagega (cold start ~30 sec)
  - Paid tier pe always-on rehta hai

- **Session file** (`browser_session.json`) server pe save hoti hai
  - Agar Render redeploy karo → session reset ho sakti hai
  - Isliye important accounts ke liye Render Disk use karo (paid)

- **RAM Usage** ~200-300MB (Render free = 512MB, thoda tight hai)

---

## 🎮 Controls

| Action | Desktop | Mobile |
|--------|---------|--------|
| Click | Mouse click | Tap |
| Double click | Double click | Double tap |
| Scroll | Mouse wheel | - |
| Type | Keyboard | ⌨️ button tap karo |
| Navigate | URL bar mein type karo | Same |
| Back/Forward | ← → buttons | Same |
| Save session | 💾 button | Same |

---

## 🛠️ Tech Stack

- **Backend:** Flask + flask-sock (WebSocket)
- **Browser:** Playwright (Chromium headless)
- **Frontend:** HTML5 Canvas + WebSocket streaming
- **Deploy:** Render.com
