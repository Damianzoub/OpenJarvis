# OpenJarvis — CLAUDE.md

Developer reference for building and extending this project.

---

## Project Mission

OpenJarvis is a modular open-source AI desktop assistant built to learn the Anthropic SDK and Browser Use agent SDK hands-on. Built phase by phase — each phase small and understandable — ending up as a genuinely useful personal assistant.

---

## Current State (as of last session)

### What is built and working
- FastAPI backend running, auto-starts on login via LaunchAgent
- `/chat` endpoint — direct Claude/Ollama passthrough (no agent loop yet)
- `/system` endpoint — CPU + RAM stats via psutil (polled by frontend)
- `config/settings.py` — reads all LLM API keys from `.env` via `os.getenv`
- Tauri frontend — Iron Man HUD UI with sidebar (clock, CPU/RAM bars, shortcuts), voice input (Web Speech API), chat

### What is NOT built yet (next up)
```
backend/tools/__init__.py        ← empty package file
backend/tools/base.py            ← ToolPlugin ABC + ToolResult (IN PROGRESS)
backend/tools/registry.py        ← auto-discovers tools via pkgutil
backend/agent/__init__.py        ← empty package file
backend/agent/planner.py         ← THE tool-use loop (core SDK learning)
backend/tools/search_files.py    ← first real tool
backend/tools/browser_tool.py    ← wraps browser-use SDK
backend/memory/store.py          ← JSON-backed fact store
```

---

## Repository Layout

```
OpenJarvis/
├── backend/
│   ├── main.py                  # FastAPI app, CORS, registers routers
│   ├── requirements.txt
│   ├── .env                     # real keys — never commit
│   ├── .env.example             # template with all supported providers
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # os.getenv for all API keys + app config
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── chat.py              # /chat endpoint (passthrough for now)
│   │   └── system.py            # /system endpoint — CPU/RAM stats
│   ├── tools/                   ← NOT BUILT YET
│   ├── agent/                   ← NOT BUILT YET
│   └── memory/                  ← NOT BUILT YET
├── frontend/
│   ├── index.html               # Jarvis HUD layout (sidebar + main)
│   ├── src/
│   │   ├── main.ts              # clock, system polling, chat, voice input
│   │   └── styles.css           # Iron Man theme
│   └── src-tauri/
│       └── tauri.conf.json      # frameless, always-on-top, 860x660
├── ~/Library/LaunchAgents/
│   └── com.openjarvis.backend.plist   # auto-starts backend on login
├── CLAUDE.md
├── SKILLS.md
└── README.md
```

---

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Agent loop | `anthropic` SDK tool-use pattern |
| Browser agent | `browser-use` + `playwright` (Chromium) |
| Settings | plain `os.getenv` + `python-dotenv` |
| Memory | JSON file (Phase 1), SQLite (Phase 2) |
| Frontend | Tauri v2 + Vite + TypeScript |
| Python env | conda `main_env` |
| Auto-start | macOS `launchd` LaunchAgent |
| Model default | `claude-sonnet-4-6`, configurable via `ACTIVE_PROVIDER` + `MODEL` in `.env` |

---

## Agent Loop Build Order (Phase 1 — in progress)

Build these files in this exact order. Each one depends on the previous.

```
Step 1  tools/base.py        ← ToolResult dataclass + ToolPlugin ABC
Step 2  tools/registry.py    ← auto-discovers all ToolPlugin subclasses via pkgutil
Step 3  agent/planner.py     ← Anthropic tool-use loop (THE learning piece)
Step 4  tools/search_files.py ← first real tool (safe, read-only)
Step 5  tools/browser_tool.py ← wraps browser-use Agent
Step 6  routes/chat.py        ← update to call planner instead of direct API
```

---

## How the Agent Loop Works (Anthropic SDK pattern)

The planner runs a **tool-use loop**:

```
1. messages = [{"role": "user", "content": user_message}]
2. response = await client.messages.create(model=..., tools=[schemas], messages=messages)
3. if response.stop_reason == "tool_use":
       → find tool_use blocks in response.content
       → execute each tool via registry
       → append assistant turn + tool_result turn to messages
       → go to step 2
4. if response.stop_reason == "end_turn":
       → extract text block, return as final answer
5. hard cap: max 10 iterations
```

Key SDK things you learn building this:
- `messages.create(tools=[...])` — how to pass tool schemas
- `response.stop_reason` — how to know if Claude wants a tool
- `tool_use` content blocks — how Claude sends back tool name + arguments
- `tool_result` messages — how to feed results back correctly

---

## How to Add a New Tool

1. Create `backend/tools/your_tool.py`
2. Subclass `ToolPlugin`, set `name` and `description`, implement `schema()` and `execute()`
3. Restart the server — registry auto-discovers it via `pkgutil`

```python
from tools.base import ToolPlugin, ToolResult

class OpenAppTool(ToolPlugin):
    name = "open_app"
    description = "Open a macOS application by name."

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Name of the app to open."}
                },
                "required": ["app_name"],
            },
        }

    def execute(self, app_name: str) -> ToolResult:
        import subprocess
        try:
            subprocess.run(["open", "-a", app_name], check=True)
            return ToolResult(success=True, output=f"Opened {app_name}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

---

## Safety Levels

| Level | Examples | Rule |
|---|---|---|
| Safe | `search_files`, `get_memory` | Execute immediately |
| Medium | `remember_fact`, `browse_web` | Execute, log the action |
| High | `send_email`, `delete_file` | `dry_run=True` by default until Phase 3 UI |
| Forbidden | bulk delete, credential access | Refuse entirely in `execute()` |

---

## Coding Standards

- Python 3.11+, type hints everywhere
- Async FastAPI handlers; `AsyncAnthropic` in the planner
- Pydantic models for all API request/response shapes
- No comments unless the WHY is non-obvious
- Tools must never raise — catch everything, return `ToolResult(success=False, error=...)`
- Keep tools single-purpose

---

## Running Locally

```bash
# Backend
conda activate main_env
cd backend
uvicorn main:app --reload

# The LaunchAgent handles this automatically on login:
# /opt/homebrew/Caskroom/miniconda/base/envs/main_env/bin/uvicorn main:app
#   --host 127.0.0.1 --port 8000 --app-dir /Users/damianoszoumpos/OpenJarvis/backend

# Frontend (once Rust is installed)
cd frontend
npm run tauri dev
```

Logs when running via LaunchAgent:
```bash
tail -f /tmp/jarvis-backend.log
tail -f /tmp/jarvis-backend-error.log
```

---

## Build Phases

| Phase | Focus | Status |
|---|---|---|
| 1 | Agent loop + browser-use + search tool | **In progress** |
| 2 | SQLite memory, MCP integration | Planned |
| 3 | Tauri popup wired to backend, global hotkey | Planned |
| 4 | Voice input via Whisper (server-side) | Planned |
| 5 | Email, calendar tools | Planned |

---

## Key Design Decisions

- **`os.getenv` over `pydantic-settings`** — simpler, no magic, easier to understand
- **Tool auto-discovery via `pkgutil`** — add a file, restart, it works. No registration boilerplate.
- **Stateless history per request** — client passes conversation history back each time. Simplifies server.
- **conda `main_env`** — all dependencies in one shared env. Trade-off: version conflicts possible with other projects.
- **LaunchAgent not LaunchDaemon** — runs as the user, not root. Reads `.env` correctly because `WorkingDirectory` is the backend folder.
