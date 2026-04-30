"""Email content cleaning utilities."""
import re
from typing import Optional
from bs4 import BeautifulSoup


def strip_html(html: Optional[str]) -> str:
    """Remove HTML tags and return plain text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    # Replace block elements with newlines for readability
    for tag in soup.find_all(["p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
        tag.append("\n")
    text = soup.get_text(separator=" ")
    # Collapse whitespace
    return re.sub(r"\s+", " ", text).strip()


def remove_signatures(text: str) -> str:
    """Remove common email signature patterns."""
    # Common signature delimiters
    patterns = [
        r"(?im)^--\s*\n.*",           # Standard `--` delimiter
        r"(?im)^Sent from my.*",      # Mobile signature
        r"(?im)^Best regards,.*",
        r"(?im)^Regards,.*",
        r"(?im)^Cheers,.*",
        r"(?im)^Thanks,.*",
        r"(?im)^Thank you,.*",
        r"(?im)^Sincerely,.*",
        r"(?im)^Yours truly,.*",
        r"(?im)^________________________________.*",  # Outlook separator
        r"(?im)^--\s*$.*",            # Another common separator
    ]
    for pattern in patterns:
        text = re.split(pattern, text, maxsplit=1)[0]
    return text.strip()


def remove_disclaimers(text: str) -> str:
    """Remove legal disclaimers and confidentiality notices."""
    disclaimer_patterns = [
        r"(?i)CONFIDENTIALITY NOTICE.*",
        r"(?i)DISCLAIMER.*",
        r"(?i)This email and any files transmitted with it.*",
        r"(?i)The information contained in this email.*",
        r"(?i)If you have received this email in error.*",
        r"(?i)Please notify the sender immediately.*",
        r"(?i)This message is intended only for.*",
    ]
    for pattern in disclaimer_patterns:
        text = re.split(pattern, text, maxsplit=1)[0]
    return text.strip()


def remove_tracking_pixels(text: str) -> str:
    """Remove invisible tracking pixel references (already handled in HTML strip, but extra safety)."""
    # Remove URLs that look like tracking pixels
    text = re.sub(r"https?://[^\s]+pixel[^\s]*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"https?://[^\s]+tracking[^\s]*", "", text, flags=re.IGNORECASE)
    return text.strip()


def remove_extra_whitespace(text: str) -> str:
    """Collapse multiple whitespace characters."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_email_body(html: Optional[str] = None, text: Optional[str] = None) -> str:
    """Full pipeline: HTML -> text -> signatures -> disclaimers -> tracking -> whitespace."""
    if html:
        body = strip_html(html)
    elif text:
        body = text
    else:
        return ""

    body = remove_signatures(body)
    body = remove_disclaimers(body)
    body = remove_tracking_pixels(body)
    body = remove_extra_whitespace(body)
    return body
