"""Unit tests for the email agent components."""
import unittest
from datetime import datetime, timezone

from classifier import classify
from cleaner import clean_email_body
from models import EmailMessage


class TestCleaner(unittest.TestCase):
    def test_strip_html(self):
        html = "<p>Hello <b>World</b></p><div>Second line</div>"
        result = clean_email_body(html=html)
        self.assertIn("Hello World", result)
        self.assertNotIn("<p>", result)

    def test_remove_signature(self):
        text = "Meeting at 3pm.\n\nBest regards,\nJohn Doe"
        result = clean_email_body(text=text)
        self.assertIn("Meeting at 3pm", result)
        self.assertNotIn("Best regards", result)

    def test_remove_disclaimer(self):
        text = "Please review.\n\nDISCLAIMER: This email is confidential..."
        result = clean_email_body(text=text)
        self.assertIn("Please review", result)
        self.assertNotIn("DISCLAIMER", result)

    def test_empty_input(self):
        self.assertEqual(clean_email_body(), "")


class TestClassifier(unittest.TestCase):
    def _make_email(self, subject, body, sender="test@example.com"):
        return EmailMessage(
            id="1",
            thread_id="t1",
            sender="Test User",
            sender_email=sender,
            recipient="me@example.com",
            subject=subject,
            timestamp=datetime.now(timezone.utc),
            body_text=body,
        )

    def test_urgent_keyword(self):
        email = self._make_email("URGENT: Action required", "Please respond ASAP.")
        result = classify(email)
        self.assertEqual(result.priority.value, "urgent")
        self.assertTrue(result.action_required)

    def test_finance_category(self):
        email = self._make_email("Invoice #123", "Your payment is due.")
        result = classify(email)
        self.assertEqual(result.category.value, "finance")

    def test_ignore_newsletter(self):
        email = self._make_email("Weekly Newsletter", "Unsubscribe here...", sender="newsletter@marketing.com")
        result = classify(email)
        self.assertEqual(result.priority.value, "ignore")

    def test_important_work(self):
        email = self._make_email("Project Update", "The team completed the milestone.")
        result = classify(email)
        self.assertEqual(result.category.value, "work")
        # Should be important or informational
        self.assertIn(result.priority.value, ["important", "informational"])

    def test_negative_sentiment(self):
        email = self._make_email("Issue with server", "Critical failure detected.")
        result = classify(email)
        self.assertEqual(result.sentiment, "negative")


class TestEndToEnd(unittest.TestCase):
    def test_full_pipeline(self):
        email = EmailMessage(
            id="1",
            thread_id="t1",
            sender="Boss",
            sender_email="boss@company.com",
            recipient="me@company.com",
            subject="Deadline update",
            timestamp=datetime.now(timezone.utc),
            body_text="The deadline has been moved to Friday. Please update your tasks.",
        )
        cleaned = clean_email_body(text=email.body_text)
        email.body_text = cleaned
        result = classify(email)

        self.assertEqual(result.priority.value, "urgent")
        self.assertTrue(result.action_required)
        self.assertIn("friday", (result.deadline or "").lower())


if __name__ == "__main__":
    unittest.main()
