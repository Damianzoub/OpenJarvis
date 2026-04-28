# OpenJarvis — CLAUDE.md

Developer reference for building and extending this project.

---

## Project Mission

OpenJarvis is a **modular open-source AI desktop assistant framework**. The goal is a platform developers can extend into their own "Jarvis" — not just a personal tool, but a reusable foundation with a plugin ecosystem, MCP support, memory, safety layers, and cross-platform UI.

---

## Architecture Overview

```
User Input (voice / text / hotkey)
        ↓
  Desktop Frontend  (Tauri — not built yet)
        ↓
  FastAPI Backend   backend/main.py
        ↓
  Agent Router      backend/agent/router.py
        ↓
  Agent Planner     backend/agent/planner.py   ← Claude tool-use loop
        ↓
  Tool Registry     backend/tools/registry.py  ← auto-discovers plugins
        ↓
  ToolPlugin impls  backend/tools/*.py
        ↓
  Memory / FS / APIs
```

---

## Repository Layout

```
open-jarvis/
├── backend/
│   ├── main.py              # FastAPI app + lifespan
│   ├── requirements.txt
│   ├── .env.example
│   ├── agent/
│   │   ├── planner.py       # Claude tool-use loop (core agent logic)
│   │   └── router.py        # Dispatches to planner (future: multi-agent)
│   ├── tools/
│   │   ├── base.py          # ToolPlugin ABC + ToolResult model
│   │   ├── registry.py      # Auto-discovers and registers tools
│   │   ├── search_files.py
│   │   ├── summarize_file.py
│   │   └── memory_tools.py
│   ├── memory/
│   │   └── store.py         # JSON-backed fact store
│   └── config/
│       └── settings.py      # Pydantic settings (reads .env)
├── desktop-app/             # Not yet built — Tauri popup UI
├── plugins/                 # Community plugins go here (future)
├── mcp-servers/             # MCP server configs (future)
├── docs/
├── tests/
├── CLAUDE.md                # This file
├── SKILLS.md                # Reusable development workflows
└── README.md
```

---

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Agent | Anthropic Python SDK, Claude tool use |
| Settings | pydantic-settings + .env |
| Memory | JSON file (SQLite in a future phase) |
| Frontend | Tauri (planned) |
| Model | claude-sonnet-4-6 default, configurable |

---

## How the Agent Works

The planner in `backend/agent/planner.py` runs a **tool-use loop**:

1. Send user message + conversation history to Claude with all tool schemas
2. If Claude responds with `stop_reason == "tool_use"` — execute the requested tools, append results, loop again
3. If Claude responds with `stop_reason == "end_turn"` — return the text response
4. Hard cap at 10 iterations to prevent infinite loops

The tool schemas are built from `ToolPlugin.schema()` and loaded automatically at startup via `ToolRegistry.load_all()`.

---

## How to Add a New Tool

1. Create `backend/tools/your_tool.py`
2. Subclass `ToolPlugin`, set `name` and `description`, implement `schema()` and `execute()`
3. Restart the server — the registry auto-discovers it

That's it. No registration boilerplate needed.

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
            return ToolResult(success=False, output=None, error=str(e))
```

---

## Safety Architecture

Tools are categorized by risk. Enforce the appropriate level in each tool's `execute()`:

| Level | Examples | Behavior |
|---|---|---|
| Safe | search_files, get_memory | Execute immediately |
| Medium | remember_fact, create_draft | Execute, log action |
| High | send_email, delete_file | Require explicit user confirmation before executing |
| Forbidden | bulk delete, credential access | Refuse entirely |

The confirmation mechanism (returning a `requires_confirmation` field) is not yet implemented — add it in a future phase when the UI exists.

---

## Coding Standards

- Python 3.11+, type hints everywhere
- Async FastAPI handlers; use `AsyncAnthropic` in the planner
- Pydantic models for all API request/response shapes
- No comments unless the WHY is non-obvious
- Tools must never raise exceptions — catch and return `ToolResult(success=False, ...)`
- Keep tools single-purpose; compose them at the agent layer, not inside a tool

---

## Running Locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in ANTHROPIC_API_KEY and SEARCH_ROOT
uvicorn main:app --reload
```

Test it:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Search for any Python files in my Documents folder"}'
```

---

## Build Phases

| Phase | Focus | Status |
|---|---|---|
| 1 | FastAPI backend + 5 tools + Claude agent loop | **In progress** |
| 2 | Memory upgrade (SQLite), plugin SDK, MCP support | Planned |
| 3 | Tauri desktop popup + hotkey | Planned |
| 4 | Voice (Whisper), notifications | Planned |
| 5 | Browser automation, email/calendar | Planned |
| 6 | Wake word, plugin marketplace | Future |

---

## Key Design Decisions

- **Tool auto-discovery** via `pkgutil` so adding a tool never requires touching the registry
- **Conversation history is stateless per request** for now — the client passes history back if it wants continuity (simplifies the server)
- **Single agent** in Phase 1 — `router.py` exists as the dispatch point for when we add specialized sub-agents later
- **JSON memory** in Phase 1 — simple, inspectable, no deps; migrate to SQLite when search/filtering matters
