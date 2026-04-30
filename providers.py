"""Email provider implementations for Gmail and Outlook."""
import base64
import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dateutil import parser as date_parser
from tenacity import retry, stop_after_attempt, wait_exponential

import config
from models import Attachment, EmailMessage


class EmailProvider:
    """Abstract base for email providers."""

    def fetch_emails(self, since: datetime, unread_only: bool = True, max_results: int = 100) -> List[EmailMessage]:
        raise NotImplementedError

    def close(self):
        pass


class GmailProvider(EmailProvider):
    """Gmail API provider."""

    def __init__(self):
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists(config.GMAIL_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(config.GMAIL_TOKEN_FILE, config.GMAIL_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(config.GMAIL_CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {config.GMAIL_CREDENTIALS_FILE}\n"
                        "Download it from Google Cloud Console -> APIs & Services -> Credentials."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(config.GMAIL_CREDENTIALS_FILE, config.GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)
            with open(config.GMAIL_TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
        return build("gmail", "v1", credentials=creds)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_emails(self, since: datetime, unread_only: bool = True, max_results: int = 100) -> List[EmailMessage]:
        query_parts = [f"after:{int(since.timestamp())}"]
        if unread_only:
            query_parts.append("is:unread")
        query = " ".join(query_parts)

        results = self.service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        messages = results.get("messages", [])

        emails: List[EmailMessage] = []
        for msg_meta in messages:
            try:
                msg = self.service.users().messages().get(userId="me", id=msg_meta["id"], format="full").execute()
                email = self._parse_message(msg)
                if email:
                    emails.append(email)
            except HttpError as e:
                print(f"[WARN] Failed to fetch message {msg_meta['id']}: {e}")
                continue
        return emails

    def _parse_message(self, msg: dict) -> Optional[EmailMessage]:
        payload = msg.get("payload", {})
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}

        sender_raw = headers.get("from", "Unknown <unknown@unknown.com>")
        sender_name, sender_email = self._parse_address(sender_raw)

        # Extract body
        body_text, body_html = self._extract_body(payload)

        # Extract attachments info
        attachments = self._extract_attachments(payload)

        # Parse timestamp
        date_str = headers.get("date", "")
        try:
            timestamp = date_parser.parse(date_str)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
        except Exception:
            timestamp = datetime.now(timezone.utc)

        return EmailMessage(
            id=msg["id"],
            thread_id=msg.get("threadId", msg["id"]),
            sender=sender_name,
            sender_email=sender_email,
            recipient=headers.get("to", ""),
            subject=headers.get("subject", "(No Subject)"),
            timestamp=timestamp,
            body_text=body_text or "",
            body_html=body_html,
            is_unread="UNREAD" in msg.get("labelIds", []),
            labels=msg.get("labelIds", []),
            attachments=attachments,
            in_reply_to=headers.get("in-reply-to"),
            references=self._parse_references(headers.get("references", "")),
        )

    def _parse_address(self, raw: str) -> tuple:
        import re
        match = re.match(r"^(.*)<([^>]+)>$", raw.strip())
        if match:
            return match.group(1).strip().strip('"'), match.group(2).strip()
        return raw, raw

    def _extract_body(self, payload: dict) -> tuple:
        """Recursively extract text/plain and text/html from payload."""
        text, html = "", ""
        mime_type = payload.get("mimeType", "")

        if mime_type == "text/plain":
            data = payload.get("body", {}).get("data", "")
            text = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace") if data else ""
        elif mime_type == "text/html":
            data = payload.get("body", {}).get("data", "")
            html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace") if data else ""
        elif "parts" in payload:
            for part in payload["parts"]:
                t, h = self._extract_body(part)
                text = text or t
                html = html or h
        return text, html

    def _extract_attachments(self, payload: dict) -> List[Attachment]:
        attachments = []
        mime_type = payload.get("mimeType", "")
        if "attachment" in payload.get("body", {}).get("attachmentId", ""):
            filename = payload.get("filename", "unknown")
            size = int(payload.get("body", {}).get("size", 0))
            attachments.append(Attachment(filename=filename, mime_type=mime_type, size=size))
        if "parts" in payload:
            for part in payload["parts"]:
                attachments.extend(self._extract_attachments(part))
        return attachments

    def _parse_references(self, refs: str) -> List[str]:
        return [r.strip() for r in refs.split() if r.strip()]

    def close(self):
        self.service.close()


class OutlookProvider(EmailProvider):
    """Microsoft Graph API provider for Outlook."""

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(self):
        self.access_token = self._authenticate()

    def _authenticate(self) -> str:
        import msal
        app = msal.PublicClientApplication(
            config.OUTLOOK_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{config.OUTLOOK_TENANT_ID}",
            token_cache=msal.SerializableTokenCache(),
        )
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(["Mail.Read"], account=accounts[0])
        else:
            result = app.acquire_token_interactive(["Mail.Read"])
        if "access_token" not in result:
            raise RuntimeError(f"Authentication failed: {result.get('error_description', result)}")
        return result["access_token"]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_emails(self, since: datetime, unread_only: bool = True, max_results: int = 100) -> List[EmailMessage]:
        import requests

        headers = {"Authorization": f"Bearer {self.access_token}", "Prefer": 'outlook.timezone="UTC"'}
        filter_parts = [f"receivedDateTime ge {since.isoformat()}"]
        if unread_only:
            filter_parts.append("isRead eq false")
        filter_query = " and ".join(filter_parts)

        url = f"{self.GRAPH_BASE}/me/messages"
        params = {
            "$filter": filter_query,
            "$top": max_results,
            "$select": "id,conversationId,from,toRecipients,subject,receivedDateTime,body,isRead,hasAttachments,internetMessageHeaders",
        }

        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        messages = data.get("value", [])

        emails = []
        for msg in messages:
            try:
                email = self._parse_message(msg)
                if email:
                    emails.append(email)
            except Exception as e:
                print(f"[WARN] Failed to parse Outlook message {msg.get('id')}: {e}")
                continue
        return emails

    def _parse_message(self, msg: dict) -> Optional[EmailMessage]:
        sender_info = msg.get("from", {}).get("emailAddress", {})
        sender_name = sender_info.get("name", "Unknown")
        sender_email = sender_info.get("address", "unknown@unknown.com")

        to_list = msg.get("toRecipients", [])
        recipient = ", ".join(
            r.get("emailAddress", {}).get("address", "") for r in to_list
        )

        body = msg.get("body", {})
        body_html = body.get("content", "") if body.get("contentType") == "html" else None
        body_text = body.get("content", "") if body.get("contentType") == "text" else ""

        timestamp = date_parser.parse(msg.get("receivedDateTime", datetime.now(timezone.utc).isoformat()))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        return EmailMessage(
            id=msg.get("id", ""),
            thread_id=msg.get("conversationId", msg.get("id", "")),
            sender=sender_name,
            sender_email=sender_email,
            recipient=recipient,
            subject=msg.get("subject", "(No Subject)"),
            timestamp=timestamp,
            body_text=body_text,
            body_html=body_html,
            is_unread=not msg.get("isRead", True),
            labels=[],
            attachments=[],
        )

    def close(self):
        pass


def get_provider() -> EmailProvider:
    if config.EMAIL_PROVIDER == "outlook":
        return OutlookProvider()
    return GmailProvider()
