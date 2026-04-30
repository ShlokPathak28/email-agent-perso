"""Classification engine for emails."""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

from dateutil import parser as date_parser

from config import (
    HIGH_PRIORITY_CONTACTS,
    IGNORED_DOMAINS,
    IGNORED_SUBJECT_PATTERNS,
    URGENCY_KEYWORDS,
)
from models import Category, ClassifiedEmail, EmailMessage, Priority


def _contains_urgency_keywords(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in URGENCY_KEYWORDS)


def _extract_date_near_keyword(text: str) -> Optional[str]:
    """Look for dates mentioned near urgency keywords."""
    # Simple heuristic: find date-like strings
    date_patterns = [
        r"\b(?:by|before|on|due)\s+([A-Za-z]{3,9}(?:day)?\s+\d{1,2}(?:,\s+\d{4})?)\b",
        r"\b(?:by|before|on|due)\s+(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b",
        r"\b(?:tomorrow|today|next\s+\w+|Friday|Monday|Tuesday|Wednesday|Thursday|Saturday|Sunday)\b",
    ]
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[0]
    return None


def _is_high_priority_sender(email: EmailMessage) -> bool:
    sender = email.sender_email.lower()
    domain = email.sender_domain
    return (
        sender in HIGH_PRIORITY_CONTACTS
        or domain in HIGH_PRIORITY_CONTACTS
        or any(contact in sender for contact in HIGH_PRIORITY_CONTACTS)
    )


def _should_ignore(email: EmailMessage) -> Tuple[bool, str]:
    """Determine if an email should be ignored, with reason."""
    domain = email.sender_domain
    if any(ignored in domain for ignored in IGNORED_DOMAINS):
        return True, f"Ignored domain: {domain}"

    subject_lower = email.subject.lower()
    for pattern in IGNORED_SUBJECT_PATTERNS:
        if pattern in subject_lower:
            return True, f"Ignored subject pattern: {pattern}"

    # Heuristic: newsletters often have List-Unsubscribe headers (captured in labels)
    if "newsletter" in subject_lower or "unsubscribe" in email.body_text.lower()[:500]:
        return True, "Newsletter / bulk email"

    return False, ""


def _detect_category(email: EmailMessage) -> Category:
    text = (email.subject + " " + email.body_text).lower()
    if any(w in text for w in ["invoice", "payment", "receipt", "bill", "subscription", "charge"]):
        return Category.FINANCE
    if any(w in text for w in ["meeting", "project", "deadline", "report", "client", "team"]):
        return Category.WORK
    if any(w in text for w in ["newsletter", "digest", "update", "announcement"]):
        return Category.NEWSLETTER
    if any(w in text for w in ["facebook", "twitter", "linkedin", "instagram", "social"]):
        return Category.SOCIAL
    if any(w in text for w in ["family", "friend", "personal", "birthday", "party"]):
        return Category.PERSONAL
    return Category.OTHER


def _detect_sentiment(text: str) -> str:
    """Simple rule-based sentiment detection."""
    negative_words = ["complaint", "issue", "problem", "error", "fail", "dissatisfied", "urgent", "critical"]
    positive_words = ["thank", "great", "excellent", "good", "success", "approved", "completed"]
    text_lower = text.lower()
    neg_count = sum(1 for w in negative_words if w in text_lower)
    pos_count = sum(1 for w in positive_words if w in text_lower)
    if neg_count > pos_count:
        return "negative"
    if pos_count > neg_count:
        return "positive"
    return "neutral"


def classify(email: EmailMessage) -> ClassifiedEmail:
    """Classify a single email message."""
    # 1. Check ignore rules first
    should_ignore, ignore_reason = _should_ignore(email)
    if should_ignore:
        return ClassifiedEmail(
            email=email,
            priority=Priority.IGNORE,
            category=_detect_category(email),
            summary=ignore_reason,
            action_required=False,
            sentiment="neutral",
        )

    # 2. Detect category and sentiment
    category = _detect_category(email)
    sentiment = _detect_sentiment(email.subject + " " + email.body_text)

    # 3. Determine priority
    text_for_analysis = (email.subject + " " + email.body_text).lower()
    has_urgency = _contains_urgency_keywords(text_for_analysis)
    deadline = _extract_date_near_keyword(text_for_analysis)
    is_high_priority = _is_high_priority_sender(email)

    action_required = False
    priority = Priority.INFORMATIONAL

    if has_urgency or is_high_priority or deadline:
        priority = Priority.URGENT
        action_required = True
    elif category in (Category.WORK, Category.FINANCE) or sentiment == "negative":
        priority = Priority.IMPORTANT
        action_required = "action" in text_for_analysis or "please" in text_for_analysis

    # 4. Generate one-line summary
    summary = _generate_summary(email)

    return ClassifiedEmail(
        email=email,
        priority=priority,
        category=category,
        summary=summary,
        action_required=action_required,
        deadline=deadline,
        sentiment=sentiment,
    )


def _generate_summary(email: EmailMessage) -> str:
    """Generate a concise one-line summary from the email body."""
    # Use first sentence or first ~120 chars of body
    body = email.body_text.strip()
    if not body:
        return email.subject

    # Try first sentence
    first_sentence = body.split(".")[0].strip()
    if len(first_sentence) > 15 and len(first_sentence) < 150:
        return first_sentence

    # Fallback to truncated body
    return body[:120].replace("\n", " ") + "..." if len(body) > 120 else body
