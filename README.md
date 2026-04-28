# OpenJarvis

An open-source modular AI desktop assistant framework. Build your own Jarvis.

## Quickstart

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
uvicorn main:app --reload
```

Then try it:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Search for Python files in my documents"}'
```

## Features (Phase 1)

- Text chat via REST API
- Claude-powered agent with tool use
- 5 built-in tools: `search_files`, `summarize_file`, `remember_fact`, `get_memory`
- Auto-discovers new tools — drop a file in `backend/tools/` and restart
- Persistent JSON memory

## Adding a Tool

Create `backend/tools/your_tool.py`, subclass `ToolPlugin`, restart. That's it. See [SKILLS.md](SKILLS.md).

## Architecture

See [CLAUDE.md](CLAUDE.md) for full architecture, coding standards, and build phases.

## Roadmap

- [ ] Phase 1 — Backend + tools + agent loop ← *here*
- [ ] Phase 2 — SQLite memory, plugin SDK, MCP support
- [ ] Phase 3 — Tauri desktop popup + hotkey
- [ ] Phase 4 — Voice (Whisper), notifications
- [ ] Phase 5 — Browser automation, email/calendar
