<div align="center">
  <img src="./OpenJarvis.png" alt="OpenJarvis" width="260" />

  # OpenJarvis

  An open-source modular AI desktop assistant framework. Build your own Jarvis — step by step, learning the Anthropic Agent SDK along the way.
</div>

> **Current state: v0** — Basic FastAPI backend with a single `/chat` endpoint. No agent loop or tools yet. That's what we're building next.

---

## Project Goal

Build a personal AI assistant that can actually *do things* — search your files, remember facts, open apps, send emails — not just chat. Built with the [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) agent (tool-use) pattern so every phase teaches you something real.

---

## What Exists Now (v0)

| Component | Status |
|---|---|
| FastAPI backend (`/chat` endpoint) | Working |
| Claude or Ollama chat passthrough | Working |
| Tauri frontend (scaffolded) | Not wired up |
| Agent loop (tool-use) | **Not built yet** |
| Tools (search, memory, etc.) | **Not built yet** |

---

## Setup

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY
uvicorn main:app --reload
```

Test:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

### Frontend (Tauri)

**Prerequisites:**
- [Node.js](https://nodejs.org) (v18+)
- [Rust](https://rustup.rs) (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)


```bash
cd frontend
npm install
npm run tauri dev   # starts both Vite and Tauri
```

---

## Build Phases

| Phase | What You Learn | Status |
|---|---|---|
| 1 | Agent loop, tool-use pattern, tool auto-discovery | **In progress** |
| 2 | SQLite memory, plugin SDK, MCP integration | Planned |
| 3 | Tauri popup + global hotkey | Planned |
| 4 | Voice input (Whisper) | Planned |
| 5 | Email, calendar, browser automation | Planned |

---

## Architecture

See [CLAUDE.md](CLAUDE.md) for the full architecture, coding standards, and agent loop design.

## Adding a Tool (Phase 1+)

Create `backend/tools/your_tool.py`, subclass `ToolPlugin`, restart. See [CLAUDE.md](CLAUDE.md) and [SKILLS.md](SKILLS.md).
