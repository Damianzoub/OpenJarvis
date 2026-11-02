# OpenJarvis — CLAUDE.md

Developer reference for building and extending this project.

Last audited against the code: **2026-10-20**. If a section here contradicts the
code, the code wins — fix this file.

---

## What this project is meant to become

OpenJarvis is a **local-first personal AI assistant that follows me everywhere.**
Not a chat window. An assistant that is present on whatever device I happen to be
near, that I talk to rather than type at, and that reaches out to me when something
needs my attention instead of waiting to be asked.

Five pillars. All five have to exist for this to be the thing I actually want:

| # | Pillar | What "done" means |
|---|---|---|
| 1 | **The brain** | One agent system that can genuinely do things — files, email, calendar, notes, money, reminders, music, news — not just answer questions |
| 2 | **It speaks** | Voice in and voice out. Talking is the primary interface; typing is the fallback |
| 3 | **Everywhere** | Same assistant, same memory, on laptop **and** phone **and** eventually an ESP32 device I can carry or leave in a room |
| 4 | **Hands-free control** | Drive the laptop with camera gestures alone — no keyboard, no mouse |
| 5 | **It calls me** | When something happens that needs a decision or a change, *it* initiates contact. I don't poll it |

Everything is local by default: Ollama for models, Qdrant for vectors, nothing
leaving the machine unless a tool explicitly needs the internet (weather, news,
Gmail, markets).

### Where the five pillars actually stand

Honest audit, not aspiration:

| Pillar | State | Reality on disk |
|---|---|---|
| 1 · Brain | **~85%** | 11 agents, 12 tool modules, Qdrant RAG (offline + online + reranker), Langfuse tracing, DeepEval, JSON memory with auto fact extraction. This part works. |
| 2 · Speaks | **~10%** | Browser Web Speech API only (`frontend/src/main.ts`). `routes/voice_chat.py` is a stub and is **not registered** in `main.py`. `backend/pipecat/` is empty. No Whisper/Piper anywhere. |
| 3 · Everywhere | **~5%** | ESP32: `firmware/PROTOCOL.md` is complete and good, but all 7 firmware `.cpp` files are **0 bytes** and there is no `/ws/voice` endpoint. Phone: no mobile target, and the backend binds `127.0.0.1` so a phone cannot reach it. |
| 4 · Hands-free | **0%** | `camera/` contains one empty `__init__.py`. |
| 5 · Calls me | **~20%** | A 30s sync worker and a reminders store exist, but `/reminders/due` is **pull-only**. Nothing initiates contact. |

### The one thing that unblocks four pillars

Everything built so far assumes *a human typing into a window*. Voice, phone,
ESP32 and gestures all need the same missing primitive:

> **A persistent bidirectional transport (`/ws/voice`) plus a session identity.**

There is currently no conversation or session ID anywhere — every `/chat` POST is
an independent Langfuse trace with no link to the turn before it. Build the socket
and the session id, and pillars 2, 3, 4 and 5 all become reachable. Build them
separately and each one re-invents it.

**So: build the socket before building any of them.**

---

## Current state of the code

### Working
- FastAPI backend, auto-starts on login via LaunchAgent
- `/chat` — SSE streaming, runs the full LangGraph multi-agent graph
- `/system` — CPU + RAM via psutil
- `/reminders/due` — pull-only reminder list
- **11 agents** wired into a compiled `StateGraph` (see `agent.md` for the roster)
- RAG over Qdrant: ingest, chunking, retrieval, reranking, query optimisation
- Google OAuth for Gmail + Calendar, with a background sync worker
- Langfuse tracing on every chat request; prompts fetched from Langfuse with local fallback
- DeepEval evaluators under `evals/`
- Tauri frontend — Iron Man HUD, voice input via Web Speech, agent-attributed streaming

### Known gaps and traps
- **Routing is single-hop.** `START → classify → exactly one agent → END`. "Check my
  calendar then remind me" silently drops half the request. The classifier also only
  ever sees `messages[-1]`, never history.
- **The router parses free text by substring match** (`orchestrator.py`). A reply like
  "Sure, let's check the calendar!" can match nothing and fall through to `General`
  with no error. Being replaced — see *Routing* below.
- **Metrics blind spot.** `routes/chat.py` skips graph updates with an empty namespace
  (`if not namespace: continue`). Top-level nodes like `classify` are therefore
  **never recorded** by `record_call`. Check `backend/observability/calls.jsonl` —
  there is no `classify` row, and there never has been. Any new top-level node
  (e.g. a supervisor) will be invisible the same way. Fix before adding one.
- `backend/mcp/`, `backend/pipecat/`, `camera/` are empty placeholders.
- `routes/voice_chat.py` exists but is a stub and is not registered in `main.py`.

---

## Repository layout

```
OpenJarvis/
├── backend/
│   ├── main.py                  # FastAPI app, lifespan builds the graph + loads RAG index
│   ├── agent/                   # one file per agent (see agent.md)
│   ├── graph/workflow_creation.py  # the StateGraph: classify -> agent -> END
│   ├── tools/                   # @tool functions, grouped by domain
│   ├── prompts/                 # system prompts + Langfuse prompt client
│   ├── rag/                     # chunking, retrieval, reranking, vector store
│   ├── memory/                  # JSON fact store + per-domain stores
│   ├── observability/           # logger.py, metrics.py -> calls.jsonl
│   ├── routes/                  # chat, system, reminders, voice_chat (stub)
│   ├── auth/ + sync/            # Google OAuth, Gmail/Calendar background sync
│   └── vectorDB/                # Qdrant init + docker-compose
├── frontend/                    # Tauri v2 + Vite + TypeScript HUD
├── firmware/                    # ESP32 — PROTOCOL.md is written, sources are empty
├── camera/                      # empty — pillar 4 lives here
├── evals/                       # DeepEval evaluators
├── CLAUDE.md                    # this file
├── AGENTS.md                    # pointer for non-Claude coding tools
└── agent.md                     # the agent roster + how routing works
```

---

## Tech stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Agent framework | **`langgraph` + `langchain` — mandatory, see the rule below** |
| Models | Local Ollama: `qwen2.5:7b` (most agents), `mistral:latest` (Knowledge) |
| Routing | **Laya** — local 421M non-autoregressive decision model (see *Routing*) |
| Vectors | Qdrant (Docker), `nomic-embed-text` embeddings |
| Memory | JSON fact store (Phase 1) → SQLite (Phase 2) |
| Observability | Langfuse (traces + hosted prompts), `observability/metrics.py` → `calls.jsonl` |
| Evals | DeepEval |
| Frontend | Tauri v2 + Vite + TypeScript |
| Firmware | PlatformIO / ESP32 |
| Python env | conda `main_env` |
| Auto-start | macOS `launchd` LaunchAgents |

### Ollama configuration that matters

Agents do **not** all share a model — Knowledge runs `mistral:latest`, everything
else runs `qwen2.5:7b`. Ollama holds one model resident by default, so alternating
between them forced a multi-second reload from disk.

Fixed by setting `OLLAMA_MAX_LOADED_MODELS=2` in
`~/Library/LaunchAgents/com.openjarvis.ollama.plist`. Verify with `ollama ps` —
both models should appear, ~10 GB total, `100% GPU`. There is plenty of headroom
on 24 GB.

> Note: there are two Ollama launch agents on this machine. `com.openjarvis.ollama`
> is the live one. The Homebrew one (`homebrew.mxcl.ollama`) errors out on load and
> its settings do **not** apply.

---

## Agent rule — ALWAYS use LangGraph

Non-negotiable. Every agent must use `langgraph` / `langchain`:

- Tools → `@tool(description="...")` from `langchain.tools`, on `async` functions
- Agents → `create_agent(llm, tools=[...], system_prompt=...)` from `langchain.agents`
- Models → `ChatOllama` from `langchain_ollama`
- Graph → `StateGraph` in `graph/workflow_creation.py`, routed with `Command(goto=...)`

**Never** write a raw `for` loop that calls the LLM directly inside an agent.
**Never** use `AsyncOpenAI` or `AsyncAnthropic` inside an agent file.

> `routes/chat.py` does use `AsyncOpenAI` against Ollama's compat endpoint — but only
> for the background fact-extraction call, which is not an agent. Keep it that way.

---

## How routing works (and where it's going)

### Today
```
START → classify → exactly ONE of 11 agents → END
```
`_classify_node` reads `state["messages"][-1].content`, calls `route()`, which asks
`qwen2.5:7b` for an agent name and substring-matches the reply.

Multi-step work *does* happen — but only **inside** one agent, because
`create_agent` is a ReAct loop. So Calendar can call `list_events`, read the result,
then call `create_event`. What cannot happen is crossing from Calendar to Reminders.

### Where it's going — Laya replaces `classify`

`pip install laya`, model `convaiinnovations/laya`, Apache 2.0. A 421M
non-autoregressive decision model: one forward pass, no token generation, returns a
typed choice from a closed list plus probabilities. Runs in-process on torch/MPS, so
it never takes an Ollama model slot.

Verified on this machine: **7/7 correct routing, zero-shot, no fine-tuning**, at
120–300 ms warm vs 300–900 ms for the current classify call.

```python
import laya

agent = laya.load("convaiinnovations/laya")   # ONCE, in main.py lifespan

questions = {
    "agent": {
        "type": "choice",                      # required
        "instructions": "Which assistant domain should handle `request`?",
        "criteria": {                          # NOT "options"
            "Weather": "weather forecast or current conditions",
            "Calendar": "check availability, list or create calendar events",
            # ... one line per agent
        },
    }
}

result = laya.decide(agent, user_message, questions=questions)
chosen = result["agent"]["choice"]             # guaranteed to be one of the labels
```

Gotchas, learned by running it:
- The schema key is **`criteria`**, not `options`, and `type` is required.
- **Load once** in `lifespan`, beside `load_index()`. First call is ~4.6 s (MPS
  warmup); after that 120–300 ms. Per-request loading would pay the 4.6 s every time.
- The shipped checkpoint has an **invalid calibration temperature for choice
  questions with 11+ options** — and there are exactly 11 agents. It warns at load.
  The *choices* are still correct; the *confidence numbers* are not trustworthy at
  11 options. Either keep the option set ≤10, or refit with
  `laya.fit_temperature_map` on labeled data before thresholding on confidence.
- `decide_batch` is **slower** than sequential calls on Apple Silicon
  (~627 ms/state vs ~200 ms). The model card's throughput figures assume CUDA.
  Do not design around batching here.
- A stale `~/.cache/huggingface/token` makes this public repo 401. Work around with
  `HF_HUB_DISABLE_IMPLICIT_TOKEN=1` or re-login to HF.

### After that — multi-hop
Add a supervisor node so agents route to it instead of `END`, and it decides
"done, or who's next". Two hard requirements:
1. **Termination must be proven, not asserted.** Carry an enumerated sub-goal list in
   state; a `DONE` that can't point at a satisfied sub-goal is an error, not a success.
2. **Side effects need a higher bar than routing.** Routing wrong costs a hop; sending
   the wrong email costs trust. Gate side-effecting tools on a separate, stricter
   threshold, tied to the Safety Levels table below.

Plus a hop counter, and a visited-agents set so an agent can't be re-selected after
it has already run.

---

## How to add a new tool

Tools are plain `@tool`-decorated async functions. There is **no** plugin base class,
no registry, and no auto-discovery — you import the tool into an agent explicitly.

```python
# backend/tools/open_app.py
from langchain.tools import tool

@tool(description="Open a macOS application by name.")
async def open_app(app_name: str) -> str:
    import asyncio
    proc = await asyncio.create_subprocess_exec("open", "-a", app_name)
    await proc.wait()
    if proc.returncode != 0:
        return f"Could not open {app_name}."
    return f"Opened {app_name}."
```

Then add it to an agent's `tools=[...]` list. Restart the server.

Conventions:
- Return a **string the model can read**, not a dict. The ReAct loop feeds it straight back.
- Prefer returning a clear error string over raising. If you do raise, LangGraph
  catches it and feeds it back as an error — acceptable, but noisier in traces.
- Keep tools single-purpose.
- `async` unless there's a reason not to.

---

## Safety levels

| Level | Examples | Rule |
|---|---|---|
| Safe | `search_files`, `get_weather`, `search_knowledge` | Execute immediately |
| Medium | `add_reminder`, `log_expense`, `play_music` | Execute, log the action |
| High | `create_draft`, `create_event`, writing files | Draft/dry-run by default; needs confirmation before it fires for real |
| Forbidden | bulk delete, credential access, sending money | Refuse inside the tool |

When the supervisor lands, its side-effect threshold should read from this table
rather than inventing a second risk model.

---

## Coding standards

- Python 3.11+, type hints everywhere
- Async FastAPI handlers
- Pydantic models for every request/response shape
- No comments unless the *why* is non-obvious
- Prompts live in `backend/prompts/`, not inline in agent files — fetched from
  Langfuse with a local constant as fallback (`get_prompt(name=...) or LOCAL_PROMPT`)
- Secrets via `os.getenv` + `python-dotenv`. Never commit `.env`,
  `auth/credentials.json`, or `auth/token.json`

---

## Running locally

```bash
# Backend
conda activate main_env
cd backend
uvicorn main:app --reload

# Qdrant
cd backend/vectorDB && docker compose up -d

# Frontend
cd frontend && npm run tauri dev
```

The LaunchAgents start the backend and Ollama on login. Logs:

```bash
tail -f /tmp/jarvis-backend.log
tail -f /tmp/jarvis-backend-error.log
tail -f /tmp/jarvis-ollama.log
```

Sanity checks:
```bash
curl -s localhost:8000/ | jq        # {"ok": true}
ollama ps                           # both models resident?
python backend/observability/metrics.py   # latency percentiles per agent
```

---

## Build phases

| Phase | Focus | Status |
|---|---|---|
| 1 | Multi-agent graph, tools, RAG, memory, observability | **Done** |
| 2 | Laya replaces `classify`; fix the metrics blind spot | **Next** |
| 3 | Multi-hop supervisor with proven termination | Planned |
| 4 | `/ws/voice` + session id + server-side STT/TTS — **unblocks pillars 2–5** | Planned |
| 5 | Proactive push over that socket (pillar 5) | Planned |
| 6 | ESP32 firmware against `firmware/PROTOCOL.md` (pillar 3) | Planned |
| 7 | Phone — PWA over LAN first, native later (pillar 3) | Planned |
| 8 | Camera gesture control (pillar 4) | Planned |

Ordering rationale: Laya first because it's small, self-contained, fixes a real
silent-failure bug, and produces the labeled routing data that Phase 3 needs to
calibrate against. The socket before voice/phone/ESP32/gestures because all four
need it.

---

## Key design decisions

- **Local-first.** Ollama + Qdrant, no cloud model on the hot path. Privacy, and it
  works on a plane.
- **`os.getenv` over `pydantic-settings`.** Simpler, no magic.
- **Prompts in Langfuse with local fallback.** Tune a prompt without redeploying;
  still runs if Langfuse is unreachable.
- **A non-generative model for routing.** A classifier that returns a typed choice
  cannot hand back an unparseable sentence. Generation is for agents, not decisions.
- **Stateless history per request.** The client passes conversation history back each
  time. Simple — but this is exactly what Phase 4's session id has to replace.
- **conda `main_env`.** One shared env. Trade-off: version conflicts with other
  projects are possible, so test risky installs in a throwaway venv first.
- **LaunchAgent not LaunchDaemon.** Runs as the user, so `.env` and the Google token
  resolve correctly.

---

## Working with me on this project

- **Explain before editing.** I am building this to learn the agent/graph stack
  hands-on. Walk me through the change and let me write it, unless I explicitly ask
  you to do it for me.
- **Plain English first.** Lead with the point in ordinary words. Introduce the
  technical term after the plain version.
- **Measure, don't estimate.** This repo has Langfuse, DeepEval and `metrics.py`
  wired up. If a claim is about latency, cost or accuracy, go get the real number.
