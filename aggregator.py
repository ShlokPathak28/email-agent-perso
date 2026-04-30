"""Thread aggregation and deduplication logic."""
from collections import defaultdict
from typing import Dict, List

from models import ClassifiedEmail, Priority, ThreadSummary


def aggregate_threads(classified_emails: List[ClassifiedEmail]) -> List[ThreadSummary]:
    """Group classified emails by thread and merge into summaries."""
    threads: Dict[str, List[ClassifiedEmail]] = defaultdict(list)
    for ce in classified_emails:
        threads[ce.email.thread_id].append(ce)

    summaries = []
    for thread_id, emails in threads.items():
        # Sort by timestamp (newest last)
        emails.sort(key=lambda e: e.email.timestamp)

        # Determine highest priority in thread
        priority_order = [Priority.URGENT, Priority.IMPORTANT, Priority.INFORMATIONAL, Priority.IGNORE]
        highest_priority = Priority.IGNORE
        for p in priority_order:
            if any(e.priority == p for e in emails):
                highest_priority = p
                break

        # Collect unique participants
        participants = list({e.email.sender_email for e in emails})

        # Latest email drives summary
        latest = emails[-1]

        # Merge summaries: take latest non-ignore summary, or combine if needed
        non_ignore = [e for e in emails if e.priority != Priority.IGNORE]
        if non_ignore:
            combined = non_ignore[-1].summary
            if len(non_ignore) > 1:
                combined = f"({len(non_ignore)} messages) {combined}"
        else:
            combined = latest.summary

        # Any action required?
        action_required = any(e.action_required for e in emails)

        # Any deadline?
        deadlines = [e.deadline for e in emails if e.deadline]
        deadline = deadlines[0] if deadlines else None

        # Category: most common non-other
        categories = [e.category for e in emails if e.category.value != "other"]
        category = categories[0] if categories else latest.category

        summaries.append(
            ThreadSummary(
                thread_id=thread_id,
                subject=latest.email.subject,
                participants=participants,
                message_count=len(emails),
                latest_timestamp=latest.email.timestamp,
                priority=highest_priority,
                combined_summary=combined,
                action_required=action_required,
                deadline=deadline,
                category=category,
            )
        )

    # Sort: urgent first, then by latest timestamp descending
    def sort_key(s: ThreadSummary):
        prio_val = {Priority.URGENT: 0, Priority.IMPORTANT: 1, Priority.INFORMATIONAL: 2, Priority.IGNORE: 3}[s.priority]
        return (prio_val, -s.latest_timestamp.timestamp())

    summaries.sort(key=sort_key)
    return summaries
