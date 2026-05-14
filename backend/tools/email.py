import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from bu_agent_sdk.tools import tool 
from auth.google_auth import get_credentials

import redis 
import json 

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def _service():
    return build('gmail', 'v1', credentials=get_credentials())

@tool("Read recent emails from the user's Gmail account. Call this when the user asks to check their email.")
async def read_emails(max_results: int = 5) -> str:
    cached = redis_client.get("recent_emails")
    if cached:
        emails = json.loads(cached)[:max_results]
        return "EMAILS:" + json.dumps(emails)
    return "No recent emails cached yet. Try again in a few seconds."

@tool("Create a draft email in the user's Gmail account. Call this when the user asks to compose an email.")
async def create_draft(to:str, subject:str, body:str)->str:
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
    