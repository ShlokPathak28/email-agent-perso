"""Configuration settings for the Email Summarization Agent."""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# ─── Gmail API ────────────────────────────────────────────────────────────────
GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "token.json")
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# ─── Microsoft Graph API (Outlook) ────────────────────────────────────────────
OUTLOOK_CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID")
OUTLOOK_CLIENT_SECRET = os.getenv("OUTLOOK_CLIENT_SECRET")
OUTLOOK_TENANT_ID = os.getenv("OUTLOOK_TENANT_ID", "common")
OUTLOOK_TOKEN_CACHE = os.getenv("OUTLOOK_TOKEN_CACHE", "msal_token_cache.bin")

# ─── Provider Selection ───────────────────────────────────────────────────────
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "gmail").lower()  # "gmail" or "outlook"

# ─── Processing Window ────────────────────────────────────────────────────────
TIME_WINDOW_HOURS = int(os.getenv("TIME_WINDOW_HOURS", "24"))
PROCESS_UNREAD_ONLY = os.getenv("PROCESS_UNREAD_ONLY", "true").lower() == "true"
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "100"))

# ─── Priority Contacts ────────────────────────────────────────────────────────
# Comma-separated list of email addresses / domains always treated as high priority
HIGH_PRIORITY_CONTACTS = {
    e.strip().lower()
    for e in os.getenv("HIGH_PRIORITY_CONTACTS", "").split(",")
    if e.strip()
}

# ─── Urgency Keywords ──────────────────────────────────────────────────────────
URGENCY_KEYWORDS = [
    "urgent",
    "asap",
    "deadline",
    "payment due",
    "action required",
    "immediate",
    "critical",
    "time-sensitive",
    "expires",
    "overdue",
    "respond by",
    "by eod",
    "by end of day",
    "by tomorrow",
]

# ─── Ignored Senders / Patterns ────────────────────────────────────────────────
IGNORED_DOMAINS = {"no-reply", "noreply", "donotreply", "marketing", "promotions"}
IGNORED_SUBJECT_PATTERNS = ["unsubscribe", "promo", "sale", "discount", "limited time"]

# ─── Scheduling ─────────────────────────────────────────────────────────────────
SCHEDULE_INTERVAL_MINUTES = int(os.getenv("SCHEDULE_INTERVAL_MINUTES", "15"))

# ─── Summarizer ─────────────────────────────────────────────────────────────────
SUMMARIZER_MODEL = os.getenv("SUMMARIZER_MODEL", "local")  # "openai", "local", or "none"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ─── Logging ────────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
