"""Telegram notification sender for email digests."""
import html
import logging
import re
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

    # 1. Headers
    text = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)

    # 2. Bold **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # 3. Italic *text* (but not bullets)
    text = re.sub(r"(?<!\n)\*(.+?)\*(?!\s)", r"<i>\1</i>", text)

    # 4. Code `text`
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)

    # 5. Bullet points
    text = re.sub(r"^\*\s+", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"^-\s+", "• ", text, flags=re.MULTILINE)

    # 6. Clean excessive whitespace
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    # 7. Escape raw HTML characters that aren't our Telegram tags
    text = _escape_html_except_tags(text, {"b", "i", "code"})

    return text.strip()


def _escape_html_except_tags(text: str, allowed_tags: set) -> str:
    """Escape <, >, & but preserve allowed HTML tags."""
    # Find all allowed tags and replace with unique placeholders
    tag_pattern = re.compile(r"<(/?)(b|i|code)(/?)>")

    placeholders = {}
    counter = [0]

    def replace_tag(match):
        counter[0] += 1
        ph = f"\x00{counter[0]}\x00"
        placeholders[ph] = match.group(0)
        return ph

    text = tag_pattern.sub(replace_tag, text)

    # Now escape all remaining HTML characters
    text = html.escape(text)

    # Restore allowed tags
    for ph, tag in placeholders.items():
        text = text.replace(ph, tag)

    return text
