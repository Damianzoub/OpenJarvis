from fastapi import APIRouter
from pydantic import BaseModel
import os 
import anthropic
from dotenv import load_dotenv

load_dotenv()


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY","")
if ANTHROPIC_API_KEY == "":
    from openai import AsyncOpenAI
    client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
else:
    client = anthropic.AsyncAnthropic()
USE_OLLAMA = not ANTHROPIC_API_KEY

router = APIRouter()

class ChatRequest(BaseModel):
    message:str

@router.post("/chat")
async def chat(req:ChatRequest):
    if USE_OLLAMA:
        response = await client.chat.completions.create(
            model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            messages=[{"role":"user","content":req.message}]
        )
        return {"reply":response.choices[0].message.content}
    else:
        response = await client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1024,
            messages=[{"role":"user","content":req.message}]
        )
        return {"reply": response.content[0].text}


