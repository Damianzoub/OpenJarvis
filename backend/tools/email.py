import base64
import re
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from langchain.tools import tool
from guardrails import Guard,Validator,register_validator
from guardrails.validator_base import FailResult,PassResult
from guardrails.errors import ValidationError
from auth.google_auth import get_credentials

import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

@register_validator(name="valid-email-address", data_type="string")
class ValidateEmail(Validator):
    def validate(self, value, metadata):
        if not _EMAIL_RE.match(value or ""):
            return FailResult(error_message=f"'{value}' is not a valid email address.")
        return PassResult()

def _service():
    return build('gmail', 'v1', credentials=get_credentials())

_guard = Guard().use(ValidateEmail())

@tool(description="Read recent emails from the inbox.")
async def read_emails(max_results: int = 5) -> str:
    cached = redis_client.get("recent_emails")
    if not cached:
        return "No recent emails cached yet. Try again in a few seconds."
    emails = json.loads(cached)[:max_results]
    lines = ["## Recent Emails\n"]
    for email in emails:
        lines.append(f"**From:** {email['from']}")
        lines.append(f"**Subject:** {email['subject']}")
        if email.get('snippet'):
            lines.append(f"> {email['snippet']}")
        lines.append("---")
    return "\n".join(lines)

@tool(description="Create an email draft with a recipient, subject, and body.")
async def create_draft(to:str, subject:str, body:str)->str:
    try:
        _guard.validate(to)
    except ValidationError as e:
        return str(e)

    service = _service()
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId='me',
        body={'message': {'raw': raw_message}}
    ).execute()

    return f"Draft created with ID: {draft['id']}"
    