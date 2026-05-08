import asyncio
import json
import os

from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

from memory.store import load_facts, save_fact

load_dotenv()

_client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


async def extract_and_save(user_message: str, assistant_reply: str) -> None:
    existing = load_facts()
    existing_text = ", ".join(existing) if existing else "none"
    extraction_prompt = (
        f'User said: "{user_message}"\n'
        f'Assistant replied: "{assistant_reply}"\n\n'
        f"Already known facts: {existing_text}\n\n"
        "Extract any NEW personal facts about the user revealed in this exchange "
        "(name, job, location, preferences, goals, etc.). "
        "Return ONLY a JSON array of short fact strings. "
        "If nothing new was revealed, return []."
    )
    try:
        resp = await _client.chat.completions.create(
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            messages=[{"role": "user", "content": extraction_prompt}],
        )
        raw = resp.choices[0].message.content or "[]"
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end == -1:
            return
        facts: list[str] = json.loads(raw[start: end + 1])
        for fact in facts:
            if isinstance(fact, str) and fact.strip():
                save_fact(fact.strip())
    except Exception:
        pass


@router.post("/chat")
async def chat(req: ChatRequest):
    from agent import orchestrator

    user_message = req.messages[-1].content if req.messages else ""
    captured: list[str] = []

    async def generate():
        async for chunk in orchestrator.stream(user_message):
            data = json.loads(chunk)
            if data["type"] == "text":
                captured.append(data["content"])
            yield f"data: {chunk}\n\n"
        asyncio.create_task(extract_and_save(user_message, captured[0] if captured else ""))

    return StreamingResponse(generate(), media_type="text/event-stream")
