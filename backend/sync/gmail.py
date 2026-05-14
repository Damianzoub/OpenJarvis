import json 
import asyncio 
import redis 
from auth.google_auth import get_credentials
from googleapiclient.discovery import build 

r = redis.Redis(host='localhost',port=6379,decode_responses=True)

def _service():
    return build('gmail', 'v1', credentials=get_credentials())


async def sync_recent_emails(max_results:int=10):
    service = await asyncio.to_thread(_service)
    results = await asyncio.to_thread(
        lambda: service.users().messages().list(userId='me',maxResults = max_results).execute()
    )
    messages = results.get('messages', [])
    emails = []
    for msg in messages:
        data = await asyncio.to_thread(
            lambda m=msg: service.users().messages().get(userId='me', id=m['id']).execute()
        )
        headers = {h["name"]: h["value"] for h in data["payload"]["headers"]}
        emails.append({
            'from': headers.get('From', '?'),
            'subject': headers.get('Subject', '?'),
            'snippet': data.get('snippet', '')
        })
    r.set('recent_emails', json.dumps(emails))
    print(f"Synced {len(emails)} recent emails to Redis.")