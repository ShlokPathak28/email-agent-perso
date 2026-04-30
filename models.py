"""Data models for the Email Summarization Agent."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class Priority(Enum):
    URGENT = "urgent"
    IMPORTANT = "important"
    INFORMATIONAL = "informational"
    IGNORE = "ignore"


class Category(Enum):
    WORK = "work"
    FINANCE = "finance"
    PERSONAL = "personal"
    NEWSLETTER = "newsletter"
    SOCIAL = "social"
    OTHER = "other"


@dataclass
class Attachment:
    filename: str
    mime_type: str
    size: int = 0


@dataclass
class EmailMessage:
    id: str
    thread_id: str
    sender: str
    sender_email: str
    recipient: str
    subject: str
    timestamp: datetime
    body_text: str
    body_html: Optional[str] = None
    is_unread: bool = True
    labels: List[str] = field(default_factory=list)
    attachments: List[Attachment] = field(default_factory=list)
    in_reply_to: Optional[str] = None
    references: List[str] = field(default_factory=list)

    @property
    def sender_domain(self) -> str:
        return self.sender_email.split("@")[-1].lower()


@dataclass
class ClassifiedEmail:
    email: EmailMessage
    priority: Priority
    category: Category
    summary: str
    action_required: bool = False
    deadline: Optional[str] = None
    sentiment: str = "neutral"


@dataclass
class ThreadSummary:
    thread_id: str
    subject: str
    participants: List[str]
    message_count: int
    latest_timestamp: datetime
    priority: Priority
    combined_summary: str
    action_required: bool = False
    deadline: Optional[str] = None
    category: Category = Category.OTHER


@dataclass
class Digest:
    generated_at: datetime
    urgent: List[ClassifiedEmail] = field(default_factory=list)
    important: List[ClassifiedEmail] = field(default_factory=list)
    informational: List[ClassifiedEmail] = field(default_factory=list)
    ignored: List[ClassifiedEmail] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return len(self.urgent) + len(self.important) + len(self.informational) + len(self.ignored)
