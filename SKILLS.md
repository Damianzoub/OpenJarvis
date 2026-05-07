# OpenJarvis — SKILLS.md

Step-by-step workflows for building and extending the project.

---

## Phase 1 Build Order — Agent Loop

Follow this order exactly. Each file depends on the one before it.

| Step | File | What you learn |
|---|---|---|
| 1 | `tools/base.py` | dataclasses, ABCs, defining a contract |
| 2 | `tools/registry.py` | `pkgutil` auto-discovery, singletons |
| 3 | `agent/planner.py` | Anthropic SDK tool-use loop ← main learning |
| 4 | `tools/search_files.py` | writing a real tool end-to-end |
| 5 | `tools/browser_tool.py` | wrapping browser-use as a ToolPlugin |
| 6 | `routes/chat.py` update | wiring routes → planner |

---

## Skill: Build `tools/base.py`

**What it does:** defines the two things every tool must be — a result shape and a behaviour contract.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: str = ""

class ToolPlugin(ABC):
    name: str
    description: str

    @abstractmethod
    def schema(self) -> dict: ...

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult: ...
```

**Why `@dataclass`:** auto-generates `__init__` so you can write `ToolResult(success=True, output="done")` instead of defining `__init__` yourself.

**Why `ABC` + `@abstractmethod`:** Python will raise an error at import time if a subclass forgets to implement `schema()` or `execute()`. Catches mistakes early.

---

## Skill: Build `tools/registry.py`

**What it does:** walks all `.py` files in the `tools/` folder, imports them, finds every class that subclasses `ToolPlugin`, and keeps them in a dict.

Key concepts:
- `pkgutil.iter_modules([tools_path])` — lists all modules in the package without importing them
- `importlib.import_module(f"tools.{name}")` — imports each one dynamically
- `inspect.getmembers(module, inspect.isclass)` — finds all classes in the module
- Check `issubclass(cls, ToolPlugin) and cls is not ToolPlugin` — skip the base class itself

Expose two methods:
- `registry.all() -> list[ToolPlugin]` — returns one instance of each tool
- `registry.schemas() -> list[dict]` — returns the schema dict for each tool (what gets passed to Claude)

---

## Skill: Build `agent/planner.py` (the core loop)

**What it does:** takes a user message, loops with Claude until Claude stops asking for tools, returns the final text answer.

```python
import anthropic
from config.settings import settings
from tools.registry import registry

client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

async def run(message: str) -> str:
    messages = [{"role": "user", "content": message}]

    for _ in range(10):                          # hard cap — prevents infinite loops
        response = await client.messages.create(
            model=settings.MODEL,
            max_tokens=4096,
            tools=registry.schemas(),            # all tool schemas
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return next(b.text for b in response.content if b.type == "text")

        # Claude wants to call tools — find all tool_use blocks
        tool_calls = [b for b in response.content if b.type == "tool_use"]

        # Append Claude's full response (required before tool_result)
        messages.append({"role": "assistant", "content": response.content})

        # Execute each tool and collect results
        results = []
        for call in tool_calls:
            tool = registry.get(call.name)
            result = tool.execute(**call.input)
            results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": result.output if result.success else result.error,
            })

        # Feed results back as a user turn
        messages.append({"role": "user", "content": results})

    return "Reached maximum iterations without a final answer."
```

**Key SDK concepts in this loop:**
- `tools=registry.schemas()` — Claude needs all schemas upfront to know what it can call
- `response.stop_reason` — `"tool_use"` means Claude wants a tool, `"end_turn"` means it's done
- `b.type == "tool_use"` — Claude puts tool call requests inside `response.content` as blocks
- `call.input` — a dict of arguments Claude decided to pass to the tool
- `tool_use_id` — must echo back the same ID so Claude matches result to request
- Order matters: assistant turn must come before `tool_result` turn in the messages list

---

## Skill: Add a New Tool

**Requires:** `tools/base.py` and `tools/registry.py` to be built.

1. Create `backend/tools/<tool_name>.py`
2. Import `ToolPlugin`, `ToolResult` from `tools.base`
3. Set `name` (snake_case) and `description` (one sentence — Claude reads this to decide when to call it)
4. Implement `schema()` — return the Anthropic tool schema dict
5. Implement `execute(**kwargs)` — always catch exceptions, return `ToolResult`
6. Restart — registry auto-discovers it

**Check it loaded:**
```bash
curl http://localhost:8000/tools
```

**Gotchas:**
- `execute()` must never raise — wrap everything in try/except
- Parameter names in `execute()` must match property names in `input_schema` exactly
- One tool, one job — compose at the agent layer, not inside a tool
- The `description` is what Claude uses to decide when to call the tool — be specific

---

## Skill: Use browser-use in a Tool

**What browser-use does:** gives the agent a real Chromium browser it can navigate, click, type, and read. You give it a task in plain English and it figures out the steps.

```python
from browser_use import Agent as BrowserAgent
from langchain_anthropic import ChatAnthropic
from config.settings import settings

async def browse(task: str) -> str:
    llm = ChatAnthropic(
        model=settings.MODEL,
        api_key=settings.ANTHROPIC_API_KEY,
    )
    agent = BrowserAgent(task=task, llm=llm)
    result = await agent.run(max_steps=settings.BROWSER_USE_MAX_STEPS)
    return result.final_result()
```

Wrap this in a `ToolPlugin` (`tools/browser_tool.py`) with:
- `name = "browse_web"`
- `description = "Browse the web to research, find information, or interact with websites."`
- `input_schema` with a single `task: string` parameter

---

## Skill: Change the Active LLM Provider

1. Open `backend/.env`
2. Set `ACTIVE_PROVIDER` to one of: `anthropic` | `openai` | `gemini` | `groq` | `mistral` | `ollama`
3. Set `MODEL` to a model name for that provider
4. Make sure the matching API key is filled in
5. Restart the backend

Examples:
```
ACTIVE_PROVIDER=anthropic  MODEL=claude-sonnet-4-6
ACTIVE_PROVIDER=openai     MODEL=gpt-4o
ACTIVE_PROVIDER=groq       MODEL=llama-3.3-70b-versatile
ACTIVE_PROVIDER=ollama     MODEL=llama3.1:8b
```

---

## Skill: Debug a Tool Not Being Called

1. `curl http://localhost:8000/tools` — confirm the tool is listed
2. Check `description` — Claude uses it to decide when to call the tool. Make it specific.
3. Check `input_schema` is valid JSON Schema — a malformed schema silently breaks things
4. Try prompting explicitly: "Use the search_files tool to find..."
5. Check server logs for import errors at startup

---

## Skill: Add a Safety Dry-Run to a Tool

For tools that do something risky (delete, send, modify):

1. Add `dry_run: bool` to `input_schema` with `default: true`
2. When `dry_run=True`, describe what *would* happen, don't do it
3. Agent presents the plan, user confirms with "yes do it"
4. Claude calls again with `dry_run=False`

---

## Skill: Manage the LaunchAgent

```bash
# Start/stop backend manually
launchctl stop com.openjarvis.backend
launchctl start com.openjarvis.backend

# Reload after editing the plist
launchctl unload ~/Library/LaunchAgents/com.openjarvis.backend.plist
launchctl load ~/Library/LaunchAgents/com.openjarvis.backend.plist

# Check status (PID column = "-" means not running)
launchctl list | grep jarvis

# See logs
tail -f /tmp/jarvis-backend.log
tail -f /tmp/jarvis-backend-error.log
```

Plist location: `~/Library/LaunchAgents/com.openjarvis.backend.plist`
Binary: `/opt/homebrew/Caskroom/miniconda/base/envs/main_env/bin/uvicorn`

---

## Skill: Run Tests

```bash
conda activate main_env
cd backend
pytest ../tests/ -v
```

Convention: one test file per tool (`tests/test_search_files.py`). Test `execute()` directly — no FastAPI needed for unit tests.

---

## Skill: Wire the Tauri Frontend (Phase 3)

1. Install Rust: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
2. `cd frontend && npm install && npm run tauri dev`
3. Backend must be running on `localhost:8000`
4. Build for production: `npm run tauri build` → `.app` in `src-tauri/target/release/bundle/macos/`
5. Add built `.app` to System Settings → General → Login Items
