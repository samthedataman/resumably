"""
Gmail API service for reading emails and creating drafts.
"""
import base64
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from typing import List, Optional, Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.config import get_settings

settings = get_settings()


class GmailService:
    def __init__(self, token_data: dict):
        """Initialize Gmail service with user's OAuth tokens."""
        self.credentials = Credentials(
            token=token_data.get('token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=token_data.get('scopes', ['https://www.googleapis.com/auth/gmail.modify'])
        )

        # Refresh if expired
        if self.credentials.expired and self.credentials.refresh_token:
            self.credentials.refresh(Request())

        self.service = build('gmail', 'v1', credentials=self.credentials)

    def list_emails(
        self,
        max_results: int = 50,
        query: str = "is:unread category:primary",
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List emails matching the query."""
        results = self.service.users().messages().list(
            userId='me',
            maxResults=max_results,
            q=query,
            pageToken=page_token
        ).execute()

        messages = results.get('messages', [])
        next_page_token = results.get('nextPageToken')

        return {
            'messages': messages,
            'next_page_token': next_page_token
        }

    def get_email(self, email_id: str) -> Dict[str, Any]:
        """Get full email content by ID."""
        message = self.service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()

        # Parse headers
        headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}

        # Parse body
        body = self._get_body(message['payload'])

        # Parse date
        internal_date = int(message.get('internalDate', 0)) / 1000
        date = datetime.fromtimestamp(internal_date)

        return {
            'id': message['id'],
            'thread_id': message['threadId'],
            'subject': headers.get('Subject', ''),
            'from': headers.get('From', ''),
            'to': headers.get('To', ''),
            'date': date,
            'snippet': message.get('snippet', ''),
            'body': body,
            'labels': message.get('labelIds', [])
        }

    def _get_body(self, payload: dict) -> str:
        """Extract body text from email payload."""
        body = ""

        if 'body' in payload and payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        elif 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html' and part['body'].get('data') and not body:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif 'parts' in part:
                    # Nested multipart
                    body = self._get_body(part)
                    if body:
                        break

        return body

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        pdf_attachment: Optional[bytes] = None,
        attachment_name: str = "resume.pdf",
        in_reply_to: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a draft email with optional PDF attachment."""
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject

        if in_reply_to:
            message['In-Reply-To'] = in_reply_to
            message['References'] = in_reply_to

        # Add body
        message.attach(MIMEText(body, 'plain'))

        # Add PDF attachment if provided
        if pdf_attachment:
            pdf_part = MIMEApplication(pdf_attachment, _subtype='pdf')
            pdf_part.add_header(
                'Content-Disposition',
                'attachment',
                filename=attachment_name
            )
            message.attach(pdf_part)

        # Encode message
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        # Create draft
        draft_body = {'message': {'raw': raw}}
        if thread_id:
            draft_body['message']['threadId'] = thread_id

        draft = self.service.users().drafts().create(
            userId='me',
            body=draft_body
        ).execute()

        return draft

    def send_draft(self, draft_id: str) -> Dict[str, Any]:
        """Send a draft email."""
        result = self.service.users().drafts().send(
            userId='me',
            body={'id': draft_id}
        ).execute()
        return result

    def delete_draft(self, draft_id: str) -> None:
        """Delete a draft email."""
        self.service.users().drafts().delete(
            userId='me',
            id=draft_id
        ).execute()

    def mark_as_read(self, email_id: str) -> None:
        """Mark an email as read."""
        self.service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()

    def add_label(self, email_id: str, label_id: str) -> None:
        """Add a label to an email."""
        self.service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': [label_id]}
        ).execute()

    def get_or_create_label(self, label_name: str) -> str:
        """Get or create a Gmail label."""
        # List existing labels
        results = self.service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        for label in labels:
            if label['name'] == label_name:
                return label['id']

        # Create new label
        label_body = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        created = self.service.users().labels().create(
            userId='me',
            body=label_body
        ).execute()

        return created['id']
