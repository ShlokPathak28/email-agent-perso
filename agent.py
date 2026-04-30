"""Main agent orchestrator."""
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import schedule

from aggregator import aggregate_threads
from classifier import classify
from cleaner import clean_email_body
from config import (
    EMAIL_PROVIDER,
    PROCESS_UNREAD_ONLY,
    SCHEDULE_INTERVAL_MINUTES,
    TIME_WINDOW_HOURS,
)
from formatter import format_digest, format_digest_aggregated
from models import ClassifiedEmail, Digest
from providers import get_provider

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("email-agent")


class EmailAgent:
    """Email summarization agent."""

    def __init__(self, provider_name: Optional[str] = None):
        self.provider_name = provider_name or EMAIL_PROVIDER
        self.provider = None

    def _ensure_provider(self):
        if self.provider is None:
            logger.info(f"Initializing email provider: {self.provider_name}")
            self.provider = get_provider()

    def run_once(self, aggregate: bool = True) -> str:
        """Execute a single fetch-classify-summarize cycle."""
        self._ensure_provider()

        since = datetime.now(timezone.utc) - timedelta(hours=TIME_WINDOW_HOURS)
        logger.info(f"Fetching emails since {since.isoformat()} (unread_only={PROCESS_UNREAD_ONLY})")

        raw_emails = self.provider.fetch_emails(
            since=since,
            unread_only=PROCESS_UNREAD_ONLY,
            max_results=100,
        )
        logger.info(f"Fetched {len(raw_emails)} raw emails")

        if not raw_emails:
            msg = "# 📬 Email Digest\n\n_No new emails in the current window._"
            print(msg)
            return msg

        # Clean + classify
        classified: List[ClassifiedEmail] = []
        for email in raw_emails:
            email.body_text = clean_email_body(html=email.body_html, text=email.body_text)
            if not email.body_text.strip() and not email.subject.strip():
                logger.debug(f"Skipping empty email {email.id}")
                continue
            classified.append(classify(email))

        logger.info(
            f"Classified: {sum(1 for c in classified if c.priority.value == 'urgent')} urgent, "
            f"{sum(1 for c in classified if c.priority.value == 'important')} important, "
            f"{sum(1 for c in classified if c.priority.value == 'informational')} informational, "
            f"{sum(1 for c in classified if c.priority.value == 'ignore')} ignored"
        )

        if aggregate:
            summaries = aggregate_threads(classified)
            output = format_digest_aggregated(summaries, datetime.now(timezone.utc))
        else:
            digest = Digest(
                generated_at=datetime.now(timezone.utc),
                urgent=[c for c in classified if c.priority.value == "urgent"],
                important=[c for c in classified if c.priority.value == "important"],
                informational=[c for c in classified if c.priority.value == "informational"],
                ignored=[c for c in classified if c.priority.value == "ignore"],
            )
            output = format_digest(digest)

        return output

    def run_continuous(self):
        """Run the agent on a schedule."""
        logger.info(f"Starting continuous mode (every {SCHEDULE_INTERVAL_MINUTES} minutes)")

        schedule.every(SCHEDULE_INTERVAL_MINUTES).minutes.do(self.run_once)

        # Run immediately once
        self.run_once()

        while True:
            schedule.run_pending()
            import time
            time.sleep(1)

    def close(self):
        if self.provider:
            self.provider.close()
            self.provider = None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Email Summarization Agent")
    parser.add_argument("--provider", choices=["gmail", "outlook"], default=None, help="Email provider")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--no-aggregate", action="store_true", help="Disable thread aggregation")
    parser.add_argument("--hours", type=int, default=TIME_WINDOW_HOURS, help="Time window in hours")
    parser.add_argument("--unread-only", action="store_true", default=PROCESS_UNREAD_ONLY, help="Only unread emails")
    args = parser.parse_args()

    # Override config with CLI args
    os.environ["EMAIL_PROVIDER"] = args.provider or EMAIL_PROVIDER
    os.environ["TIME_WINDOW_HOURS"] = str(args.hours)
    os.environ["PROCESS_UNREAD_ONLY"] = "true" if args.unread_only else "false"

    agent = EmailAgent(provider_name=args.provider)

    try:
        if args.once:
            agent.run_once(aggregate=not args.no_aggregate)
        else:
            agent.run_continuous()
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Exiting...")
    finally:
        agent.close()


if __name__ == "__main__":
    main()
