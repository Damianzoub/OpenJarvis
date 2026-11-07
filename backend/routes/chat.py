import asyncio
import json
import os

from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel
from langchain_core.messages import AIMessage
from langfuse.langchain import CallbackHandler

from memory.store import load_facts, save_fact
from short_memory.main import add_message, get_history
from observability.metrics import record_call
from observability.logger import logger

load_dotenv()

_client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
_langfuse_handler = CallbackHandler()

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    session_id: str | None = None


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
    except Exception as e:
        logger.warning(f"extract_and_save failed: {e}")


@router.post("/chat")
async def chat(req: ChatRequest):
    from main import graph

    user_message = req.messages[-1].content if req.messages else ""
    captured: list[str] = []

    async def generate():
        logger.info(f"chat request: {user_message[:80]!r}")
        yield f"data: {json.dumps({'type': 'status', 'content': 'Thinking...'})}\n\n"

        facts = load_facts()
        state_message = (
            f"[Known facts about the user: {'; '.join(facts)}]\n\n{user_message}"
            if facts else user_message
        )
        history = await get_history(req.session_id) if req.session_id else []
        state = {"messages": history + [{"role": "user", "content": state_message}]}
        agent_name = "General"
        try:
            async for namespace, chunk in graph.astream(state, stream_mode="values", subgraphs=True, config={"callbacks": [_langfuse_handler]}):
                if not namespace:
                    continue
                agent_name = namespace[0].split(":")[0]

                message = chunk["messages"][-1]
                if isinstance(message, AIMessage) and message.tool_calls:
                    for call in message.tool_calls:
                        data = json.dumps({"type": "tool", "content": f"Using {call['name']}...", "agent": agent_name})
                        yield f"data: {data}\n\n"
                elif isinstance(message, AIMessage) and message.content:
                    captured.append(message.content)
                    data = json.dumps({"type": "text", "content": message.content, "agent": agent_name})
                    yield f"data: {data}\n\n"

                    usage = message.usage_metadata
                    total_duration_ns = message.response_metadata.get("total_duration")
                    if usage and total_duration_ns:
                        record_call(
                            agent=agent_name,
                            model=message.response_metadata.get("model", "unknown"),
                            prompt_tokens=usage.get("input_tokens", 0),
                            completion_tokens=usage.get("output_tokens", 0),
                            latency_ms=total_duration_ns / 1e6,
                        )
        except Exception:
            logger.exception(f"chat request failed, agent={agent_name}")
            yield f"data: {json.dumps({'type': 'text', 'content': 'Something went wrong handling that.', 'agent': agent_name})}\n\n"

        logger.info(f"chat done: agent={agent_name}")
        yield f"data: {json.dumps({'type': 'done', 'agent': agent_name})}\n\n"
        if req.session_id and captured:
            await add_message(req.session_id, "user", user_message)
            await add_message(req.session_id, "assistant", captured[-1])
        asyncio.create_task(extract_and_save(user_message, captured[0] if captured else ""))

    return StreamingResponse(generate(), media_type="text/event-stream")
