# 📬 Email Summarization Agent

An AI agent that reads, processes, and summarizes emails with structured output, priority detection, and Telegram delivery.

> **Why I built it:** Manually triaging an inbox I rarely opened was slow and repetitive — exactly the kind of problem worth automating. Instead of checking Gmail by hand, I built an agent that does the reading, classifying, and summarizing for me.

---

## What It Does

- Monitors your Gmail or Outlook inbox
- Classifies emails: **Urgent** / **Important** / **Informational** / **Ignored**
- Groups related emails into threads
- Sends clean summaries to your **terminal** and **Telegram**
- Runs once or on a schedule

---

## Quick Start (5 Minutes)

### 1. Clone & Install

```bash
git clone https://github.com/ShlokPathak28/email-agent-perso.git
cd email-agent-perso
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Create Your Config File

```bash
cp .env.example .env
```

---

## Gmail Setup

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown (top-left) → **New Project**
3. Name it `email-agent` → click **Create**
4. Make sure your new project is selected

### Step 2: Enable Gmail API

1. Go to [APIs & Services → Library](https://console.cloud.google.com/apis/library)
2. Search **"Gmail API"** → click it → click **Enable**

### Step 3: Create OAuth Credentials

1. Go to [APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials)
2. Click **+ Create Credentials** → **OAuth client ID**
3. If asked to "Configure consent screen":
   - Click **Configure Consent Screen**
   - Choose **External** → click **Create**
   - App name: `email-agent`
   - User support email: pick your Gmail
   - Developer contact: your Gmail
   - Click **Save and Continue** (skip scopes, skip test users for now)
   - Click **Back to Dashboard**
4. Go back to **Credentials** → **+ Create Credentials** → **OAuth client ID**
5. Application type: **Desktop app**
6. Name: `email-agent-desktop`
7. Click **Create**
8. Click **Download JSON**
9. Move that file into your project folder and rename it to **`credentials.json`**

### Step 4: Add Yourself as a Test User

> ⚠️ **This is required.** Without this, Google will block the login with "Access blocked: app is in testing."

1. Go to [APIs & Services → OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)
2. Under **Publishing Status**, make sure it says **Testing**
3. Scroll down to **Test users**
4. Click **+ ADD USERS**
5. Enter your Gmail address
6. Click **Save**

### Step 5: Run the Agent

```bash
python agent.py --once
```

A browser window will open. Sign in with your Gmail, click **Continue** — your auth token is saved locally as `token.json`. You won't need to do this again.

---

## Outlook Setup (Alternative to Gmail)

1. Go to [Azure App Registrations](https://portal.azure.com/)
2. Click **New registration**
3. Name it `email-agent` → click **Register**
4. Click **API Permissions** → **+ Add a permission**
5. Choose **Microsoft Graph** → **Delegated permissions**
6. Search and add **`Mail.Read`**
7. Click **Certificates & secrets** → **+ New client secret**
8. Copy the secret value immediately (it disappears after)
9. Add to your `.env`:
   ```
   EMAIL_PROVIDER=outlook
   OUTLOOK_CLIENT_ID=your-application-id
   OUTLOOK_CLIENT_SECRET=your-secret-value
   ```
10. Run:
    ```bash
    python agent.py --once --provider outlook
    ```

---

## Telegram Setup (Optional)

Get summaries delivered to your phone:

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Type `/newbot`
3. Give it a name and username → **save the token** it gives you
4. Message [@userinfobot](https://t.me/userinfobot) → **save your Chat ID** (just numbers)
5. Add to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234...
   TELEGRAM_CHAT_ID=123456789
   ```
6. **Important:** Open Telegram, find your bot, and tap **Start**
7. Run normally — summaries go to both terminal and Telegram:
   ```bash
   python agent.py --once
   ```

---

## Usage

| Command | What it does |
|---------|-------------|
| `python agent.py --once` | Run once, show summary |
| `python agent.py --once --hours 48` | Check last 48 hours |
| `python agent.py --once --no-aggregate` | Don't group threads |
| `python agent.py` | Run continuously every 15 min |

### Automate It

**Daily digest at 8am:**
```bash
crontab -e
# Add this line:
0 8 * * * cd /path/to/email-agent-perso && venv/bin/python agent.py --once
```

**Run as background service:**
```bash
nohup python agent.py > agent.log 2>&1 &
```

---

## What You'll See

**Terminal:**
```
📬 Email Digest — 2025-04-30 10:15 UTC
12 emails processed

📌 Urgent
• Boss – Project deadline moved to Friday (Action: Yes)

⚠️ Important
• HR – Benefits enrollment opens

ℹ️ Informational
• Newsletter – Weekly digest

🗑️ Ignored
• Marketing – Ignored domain: marketing.example.com
```

**Telegram:** Same clean summary delivered to your phone.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `credentials.json not found` | Make sure you downloaded and renamed the OAuth credentials |
| "Access blocked: app has not completed verification" | Add your Gmail as a **Test user** in the OAuth consent screen (see Step 4 above) |
| Browser auth loops forever | Delete `token.json` and re-run |
| No emails showing | Increase `--hours` or set `PROCESS_UNREAD_ONLY=false` in `.env` |
| Telegram not sending | Make sure you tapped **Start** on your bot, and the Chat ID is numeric |
| 403 errors from Google | Make sure credentials are type **Desktop app**, not Web |

---

## File Structure

```
agent.py              → Main entry point + scheduler
providers.py          → Gmail / Outlook API
classifier.py         → Priority + category detection
cleaner.py            → HTML strip, signature removal
aggregator.py         → Thread grouping
formatter.py          → Markdown output
telegram_notifier.py  → Telegram delivery
models.py             → Data classes
config.py             → Settings
```

---

## Privacy

- **Read-only** — never sends, deletes, or modifies emails
- All tokens stored **locally** (never uploaded)
- No email content logged by default

---

*Built iteratively with AI coding assistants (Kimi K2.6), designed, tested and maintained by me.*
