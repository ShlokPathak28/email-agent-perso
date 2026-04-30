# 📬 Email Summarization Agent

An AI agent that reads, processes, and summarizes emails with structured output, priority detection, and thread aggregation.

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-provider** | Gmail (Google API) + Outlook (Microsoft Graph) |
| **Smart Cleaning** | Strips HTML, signatures, disclaimers, tracking pixels |
| **Priority Classification** | Urgent / Important / Informational / Ignore |
| **Thread Aggregation** | Merges related emails into single summaries |
| **Heuristic Detection** | Keywords, deadlines, high-priority contacts, sentiment |
| **Error Resilience** | Exponential backoff retries, skip-on-failure |
| **Continuous or One-shot** | Run on schedule or ad-hoc |

---

## Quick Start

### 1. Install Dependencies

```bash
cd email-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3a. Gmail Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Gmail API**
3. Create **OAuth 2.0 credentials** (Desktop app)
4. Download `credentials.json` into the `email-agent/` folder
5. Run once — browser will prompt for auth, token saved to `token.json`

### 3b. Outlook Setup

1. Go to [Azure App Registrations](https://portal.azure.com/)
2. New registration → add `Mail.Read` delegated permission
3. Copy **Application (client) ID** and create a **client secret**
4. Add to `.env`:
   ```
   OUTLOOK_CLIENT_ID=your-id
   OUTLOOK_CLIENT_SECRET=your-secret
   ```

---

## Usage

### Run Once
```bash
python agent.py --once
```

### Run Continuously (every 15 min)
```bash
python agent.py
```

### Custom Time Window
```bash
python agent.py --once --hours 48 --unread-only
```

### Disable Thread Aggregation
```bash
python agent.py --once --no-aggregate
```

---

## Output Format

```markdown
# 📬 Email Digest — 2025-01-15 09:00 UTC
**12 emails processed**

---
### 📌 Urgent
* **Boss** (boss@company.com) – Project deadline moved to Friday (Action required: Yes, Deadline: Friday)

### ⚠️ Important
* **HR** – New benefits enrollment period opens next week

### ℹ️ Informational
* **Newsletter** – Weekly engineering digest published

### 🗑️ Ignored
* **Marketing** – Ignored domain: marketing.example.com
```

---

## Architecture

```
agent.py         → Orchestrator (CLI + scheduler)
providers.py     → Gmail / Outlook API wrappers
classifier.py    → Priority + category + sentiment rules
cleaner.py       → HTML strip, sig removal, dedup
aggregator.py    → Thread grouping & merging
formatter.py     → Markdown / Rich output
models.py        → Data classes
config.py        → Settings & env vars
```

---

## Extending

- **Add LLM summaries**: Set `SUMMARIZER_MODEL=openai` and provide `OPENAI_API_KEY`
- **Custom ignore rules**: Edit `IGNORED_DOMAINS` / `IGNORED_SUBJECT_PATTERNS` in `config.py`
- **New provider**: Subclass `EmailProvider` in `providers.py`

---

## Privacy & Safety

- **Read-only** — never sends, deletes, or modifies emails
- Asks before any write action (not currently implemented)
- No sensitive data logged by default
- All auth tokens stored locally
