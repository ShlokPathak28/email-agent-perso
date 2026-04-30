"""Output formatting for digests and summaries."""
from datetime import datetime
from typing import List

from rich.console import Console
from rich.markdown import Markdown

from models import ClassifiedEmail, Digest, Priority, ThreadSummary


def format_digest(digest: Digest, use_rich: bool = True) -> str:
    """Format a Digest into the structured markdown output."""
    lines = []
    lines.append(f"# 📬 Email Digest — {digest.generated_at.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**{digest.total_processed} emails processed**\n")

    # Urgent
    lines.append("---")
    lines.append("### 📌 Urgent\n")
    if digest.urgent:
        for item in digest.urgent:
            action = f" (Action required: {'Yes' if item.action_required else 'No'}"
            if item.deadline:
                action += f", Deadline: {item.deadline}"
            action += ")"
            lines.append(f"* **{item.email.sender}** ({item.email.sender_email}) – {item.summary}{action}")
    else:
        lines.append("_No urgent emails._")
    lines.append("")

    # Important
    lines.append("### ⚠️ Important\n")
    if digest.important:
        for item in digest.important:
            lines.append(f"* **{item.email.sender}** – {item.summary}")
    else:
        lines.append("_No important emails._")
    lines.append("")

    # Informational
    lines.append("### ℹ️ Informational\n")
    if digest.informational:
        for item in digest.informational:
            lines.append(f"* **{item.email.sender}** – {item.summary}")
    else:
        lines.append("_No informational emails._")
    lines.append("")

    # Ignored
    lines.append("### 🗑️ Ignored\n")
    if digest.ignored:
        for item in digest.ignored:
            lines.append(f"* **{item.email.sender}** – {item.summary}")
    else:
        lines.append("_No emails ignored._")
    lines.append("")

    output = "\n".join(lines)

    if use_rich:
        console = Console()
        md = Markdown(output)
        console.print(md)

    return output


def format_digest_aggregated(summaries: List[ThreadSummary], generated_at: datetime, use_rich: bool = True) -> str:
    """Format aggregated thread summaries."""
    lines = []
    lines.append(f"# 📬 Email Digest (Aggregated) — {generated_at.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**{len(summaries)} threads processed**\n")

    urgent = [s for s in summaries if s.priority == Priority.URGENT]
    important = [s for s in summaries if s.priority == Priority.IMPORTANT]
    informational = [s for s in summaries if s.priority == Priority.INFORMATIONAL]
    ignored = [s for s in summaries if s.priority == Priority.IGNORE]

    lines.append("---")
    lines.append("### 📌 Urgent\n")
    if urgent:
        for s in urgent:
            action = f" (Action required: {'Yes' if s.action_required else 'No'}"
            if s.deadline:
                action += f", Deadline: {s.deadline}"
            action += ")"
            participants = ", ".join(s.participants)
            lines.append(f"* **[{s.subject}]** {participants} – {s.combined_summary}{action}")
    else:
        lines.append("_No urgent threads._")
    lines.append("")

    lines.append("### ⚠️ Important\n")
    if important:
        for s in important:
            lines.append(f"* **[{s.subject}]** – {s.combined_summary}")
    else:
        lines.append("_No important threads._")
    lines.append("")

    lines.append("### ℹ️ Informational\n")
    if informational:
        for s in informational:
            lines.append(f"* **[{s.subject}]** – {s.combined_summary}")
    else:
        lines.append("_No informational threads._")
    lines.append("")

    lines.append("### 🗑️ Ignored\n")
    if ignored:
        for s in ignored:
            lines.append(f"* **[{s.subject}]** – {s.combined_summary}")
    else:
        lines.append("_No threads ignored._")
    lines.append("")

    output = "\n".join(lines)

    if use_rich:
        console = Console()
        md = Markdown(output)
        console.print(md)

    return output
