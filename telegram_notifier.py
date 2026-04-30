"""Telegram notification sender for email digests."""
import logging
from typing import Optional

import requests

import config

logger = logging.getLogger("email-agent")

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MSG_LEN = 4000  # Leave buffer below 4096 Telegram limit


def _chunk_message(text: str, max_len: int = MAX_MSG_LEN) -> list:
    """Split long text into chunks at newline boundaries when possible."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    lines = text.split("\n")
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current.strip())
            current = line
        else:
            current = current + "\n" + line if current else line
    if current:
        chunks.append(current.strip())
    return chunks


def send_digest(markdown_text: str, bot_token: Optional[str] = None, chat_id: Optional[str] = None) -> bool:
    """Send a digest to Telegram. Supports long messages via chunking."""
    token = bot_token or config.TELEGRAM_BOT_TOKEN
    chat = chat_id or config.TELEGRAM_CHAT_ID

    if not token or not chat:
        logger.warning("Telegram not configured: missing BOT_TOKEN or CHAT_ID")
        return False

    url = TELEGRAM_API.format(token=token)

    # Convert markdown to simple HTML for Telegram
    html_text = _markdown_to_telegram_html(markdown_text)
    chunks = _chunk_message(html_text, MAX_MSG_LEN)

    success = True
    for i, chunk in enumerate(chunks, 1):
        prefix = f"<b>Digest ({i}/{len(chunks)})</b>\n\n" if len(chunks) > 1 else ""
        payload = {
            "chat_id": chat,
            "text": prefix + chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            logger.info(f"Telegram chunk {i}/{len(chunks)} sent")
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram chunk {i}: {e}")
            success = False

    return success


def send_simple_message(text: str, bot_token: Optional[str] = None, chat_id: Optional[str] = None) -> bool:
    """Send a plain text message to Telegram."""
    token = bot_token or config.TELEGRAM_BOT_TOKEN
    chat = chat_id or config.TELEGRAM_CHAT_ID

    if not token or not chat:
        return False

    url = TELEGRAM_API.format(token=token)
    payload = {
        "chat_id": chat,
        "text": text[:MAX_MSG_LEN],
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def _markdown_to_telegram_html(text: str) -> str:
    """Convert simple markdown to Telegram HTML subset."""
    import re

    # Headers
    text = re.sub(r"^#\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"^###\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)

    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)

    # Italic
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"_(.+?)_", r"<i>\1</i>", text)

    # Code / inline
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)

    # Bullet points
    text = re.sub(r"^\*\s+", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"^-\s+", "• ", text, flags=re.MULTILINE)

    # Clean up excessive whitespace
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    # Escape HTML entities that aren't tags
    # Simple approach: we already used <b>, <i>, <code> — avoid double-escaping
    text = text.replace("&", "&amp;")
    text = text.replace("<b>", "<<B>>").replace("</b>", "<</B>>")
    text = text.replace("<i>", "<<I>>").replace("</i>", "<</I>>")
    text = text.replace("<code>", "<<CODE>>").replace("</code>", "<</CODE>>")
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace("<<B>>", "<b>").replace("<</B>>", "</b>")
    text = text.replace("<<I>>", "<i>").replace("<</I>>", "</i>")
    text = text.replace("<<CODE>>", "<code>").replace("<</CODE>>", "</code>")

    return text.strip()
