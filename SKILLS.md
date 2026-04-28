# OpenJarvis — SKILLS.md

Reusable step-by-step workflows for common development tasks on this project.

---

## Skill: Add a New Tool

**Use when:** You want to give Jarvis a new capability.

1. Create `backend/tools/<tool_name>.py`
2. Import `ToolPlugin` and `ToolResult` from `.base`
3. Subclass `ToolPlugin`, set `name` (snake_case) and `description` (one sentence, user-facing)
4. Implement `schema()` — return the Anthropic tool schema dict with `input_schema`
5. Implement `execute(**kwargs)` — always catch exceptions, return `ToolResult`
6. Restart the server — the registry picks it up automatically

**Check it loaded:**
```bash
curl http://localhost:8000/tools
```

**Gotchas:**
- `execute()` must never raise — catch all exceptions and return `ToolResult(success=False, error=...)`
- Match the `execute()` parameter names exactly to your `input_schema` property names
- Keep tools single-purpose — one tool, one job

---

## Skill: Add Memory to a Tool

**Use when:** A tool needs to persist or retrieve data across conversations.

1. Import `memory` from `memory.store`
2. Call `memory.remember(fact, category)` to store
3. Call `memory.recall(query)` to retrieve
4. The store is a singleton — no session management needed

```python
from memory.store import memory

# inside execute():
memory.remember(f"User prefers {value}", category="preference")
facts = memory.recall("preference")
```

---

## Skill: Change the AI Model

**Use when:** You want to switch between Claude models (e.g., faster Haiku for drafts, Opus for complex reasoning).

1. Open `backend/.env`
2. Change `MODEL=claude-sonnet-4-6` to your target model
3. Available models: `claude-haiku-4-5-20251001`, `claude-sonnet-4-6`, `claude-opus-4-7`
4. Restart the server

No code changes needed — `settings.model` is read at startup.

---

## Skill: Add a New API Endpoint

**Use when:** The frontend or a CLI client needs a new backend capability.

1. Open `backend/main.py`
2. Add a Pydantic request/response model
3. Add a `@app.post("/your-route")` handler
4. Keep business logic in `agent/` or `tools/` — keep `main.py` thin

```python
class SummarizeRequest(BaseModel):
    path: str

@app.post("/summarize")
async def summarize(req: SummarizeRequest):
    tool = registry.get("summarize_file")
    result = tool.execute(path=req.path)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.output
```

---

## Skill: Add an MCP Server Integration

**Use when:** You want to connect an external MCP server (GitHub, calendar, etc.).

> Phase 2 feature — placeholder workflow.

1. Create `mcp-servers/<name>/config.json` with the server URL and capabilities
2. Create `backend/tools/mcp_<name>.py` wrapping the MCP client calls as a `ToolPlugin`
3. The agent will use it like any other tool — no special handling needed

---

## Skill: Debug a Tool Not Being Called

**Use when:** You ask Jarvis to do something and it responds without using the right tool.

1. Check the tool loaded: `curl http://localhost:8000/tools` — confirm it's listed
2. Check the `description` field — Claude uses it to decide when to call the tool. Make it specific and action-oriented.
3. Check `schema()` `input_schema` is valid JSON Schema — a malformed schema silently prevents the tool from being offered
4. Try prompting more explicitly: "Use the search_files tool to find..."
5. Check server logs for any import errors at startup

---

## Skill: Run Tests

> Tests are in `tests/` — not yet written. When you add them:

```bash
cd backend
pytest ../tests/ -v
```

Convention: one test file per tool (`tests/test_search_files.py`). Test `execute()` directly — no need to spin up FastAPI for unit tests.

---

## Skill: Add a Safety Confirmation to a Tool

**Use when:** A tool takes a risky action (delete, send, modify) and should pause for user approval.

> Full confirmation UI requires the desktop frontend (Phase 3). For now:

1. Add a `dry_run: bool = True` parameter to the tool's `input_schema`
2. When `dry_run=True`, describe what *would* happen without doing it
3. The agent will present the plan; the user confirms by saying "yes, do it" or similar
4. Claude will then call the tool again with `dry_run=False`

---

## Skill: Upgrade to SQLite Memory

**Use when:** The JSON memory store becomes slow or you need better querying.

1. Add `aiosqlite` to `requirements.txt`
2. Rewrite `backend/memory/store.py` to use SQLite with the same `remember()` / `recall()` interface
3. No other files need to change — tools import from `memory.store`, not from the implementation

---

## Skill: Add the Desktop Popup (Tauri)

**Use when:** Phase 3 — building the desktop frontend.

1. `cd desktop-app && npx create-tauri-app`
2. Use the Tauri `invoke` API to POST to `http://localhost:8000/chat`
3. Register a global hotkey in `tauri.conf.json` to show/hide the popup window
4. Keep the UI minimal: text input, response area, voice button
