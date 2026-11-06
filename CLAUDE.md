# OpenJarvis — CLAUDE.md

Developer reference for building and extending this project.

Last audited against the code: **2026-11-06**. If a section here contradicts the
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

Local by default: Ollama for models, Qdrant for vectors, Postgres and Redis on this
machine. Cloud services are allowed only where a tool needs the internet (weather,
news, Gmail, markets), in `ENV=Prod`, and — for now — in the voice pipeline (see
*Key design decisions*).

### Where the five pillars actually stand

Honest audit, not aspiration:

| Pillar | State | Reality on disk |
|---|---|---|
| 1 · Brain | **~85%** | 11 agents in the graph (+ PDF/Excel/PowerPoint agents with prompts but no tools, not in the graph), Laya routing, Qdrant RAG, Langfuse, DeepEval. Long memory in Postgres, short memory in Redis. Works. |
| 2 · Speaks | **~40%** | `backend/voice/` is a working Pipecat bot (Deepgram → `gpt-6-luna` → Cartesia over WebRTC) with all 11 agents as Pipecat Flows nodes. The HUD's MIC button starts a call. A scripted call connected and the bot spoke back; **a real spoken call through the app has not been tested yet.** All three voice services are cloud — no local Whisper/Piper yet. |
| 3 · Everywhere | **~15%** | ESP32: `firmware/PROTOCOL.md` is written and the firmware sources now have code (~8 KB), **never run on hardware**. `/ws/voice` is registered but only echoes audio back. Phone: no mobile target; backend binds `127.0.0.1`. Voice calls do **not** share memory with `/chat` yet. |
| 4 · Hands-free | **0%** | `camera/` contains one empty `__init__.py`. |
| 5 · Calls me | **~20%** | A 30s sync worker and reminders in Postgres exist, but `/reminders/due` is **pull-only**. Nothing initiates contact. |

### What still blocks pillars 3–5

Voice no longer depends on `/ws/voice`: the laptop talks to the Pipecat bot over
WebRTC. `/chat` now has a session id (Redis). What is still missing:

- **One memory for every channel.** The voice bot keeps its conversation inside the
  call and forgets it on hang-up; it does not read facts or save to Redis.
- **`/ws/voice` running the real bot.** The ESP32 needs the same Pipecat agents behind
  a websocket transport instead of WebRTC. Today it echoes.
- **A push path.** Nothing can start a conversation with me.

---

## Current state of the code

### Working
- FastAPI backend, auto-starts on login via LaunchAgent
- `/chat` — SSE streaming, runs the full LangGraph graph; loads and saves the
  conversation in Redis when the client sends a `session_id`
- `/system` — CPU + RAM via psutil
- `/reminders/due` — pull-only reminder list
- **11 agents** wired into a compiled `StateGraph`, routed by **Laya** (see `agent.md`)
- Every agent switches model on `ENV`: Ollama by default, `gpt-6-luna` when `ENV=Prod`
- RAG over Qdrant: ingest, chunking, hybrid retrieval (dense + BM25), reranking
- Long memory (Postgres): facts, expenses, goals, journal entries, reminders
- Short memory (Redis): last 40 messages per session, expires after 1 h idle
- Google OAuth for Gmail + Calendar, with a background sync worker
- Langfuse tracing on every chat request; prompts fetched from Langfuse with local fallback
- DeepEval evaluators and `evals/evaluators/retrieval_gate.py` (8/8 passing)
- Tauri frontend — Iron Man HUD, MIC button = Pipecat voice call, agent-attributed streaming
- Voice bot: `python -m voice.main`, Pipecat Flows with a global `switch_agent`

### Known gaps and traps
- **Routing is single-hop in text.** `START → classify → exactly one agent → END`.
  "Check my calendar then remind me" drops half the request. `classify` only reads
  `messages[-1]`, even though the agents now get the history. (Voice is different:
  `switch_agent` lets the conversation move between agents.)
- **Laya misroutes ~16%** (42/50 on the last labelled run).
- **Metrics blind spot.** `routes/chat.py` skips graph updates with an empty namespace
  (`if not namespace: continue`), so `classify` is **never recorded** by `record_call`
  — `calls.jsonl` has no `classify` row. Any new top-level node (e.g. a supervisor)
  will be invisible the same way. Fix before adding one.
- **Incremental RAG is broken.** `rag/offline.py` uses `IngestionPipeline`, but reads
  the docstore from the wrong path, passes the Qdrant client into `collection_name`,
  uses `doc.id` instead of `doc.id_`, and sets `store_nodes_override=True`.
- **Fact extraction saves near-duplicates** ("favourite colour is teal" and "Your
  favorite color is teal"). The uniqueness check only catches identical text.
- **No confirmation gate** for High-risk tools (`create_draft`, `create_event`), even
  though the Safety Levels table requires one. Voice makes mishearing a real risk.
- **Google token expires** → sync fails with `invalid_grant` until I sign in again.
- `.gitignore` ignores all of `backend/prompts/`, so a fresh clone cannot start, and
  lists `calls.json` instead of `calls.jsonl`.
- `backend/mcp/` (one empty file) and `camera/` are placeholders.

---

## Repository layout

```
OpenJarvis/
├── backend/
│   ├── main.py                  # FastAPI app; lifespan: init_db, Laya, RAG index, graph
│   ├── agent/                   # one file per agent + laya_router.py (see agent.md)
│   ├── graph/workflow_creation.py  # the StateGraph: classify -> agent -> END
│   ├── tools/                   # @tool functions, grouped by domain
│   ├── prompts/                 # system prompts + Langfuse prompt client
│   ├── rag/                     # chunking, retrieval, reranking, vector store
│   ├── memory/                  # store functions the tools call (now backed by Postgres)
│   ├── long_memory/             # SQLAlchemy engine + schema, Alembic (alembic.ini, migrations/)
│   ├── short_memory/            # Redis conversation history per session
│   ├── voice/                   # Pipecat bot: main.py, agents.py (Flows nodes), tools.py
│   ├── observability/           # logger.py, metrics.py -> calls.jsonl
│   ├── routes/                  # chat, system, reminders, roadmap, voice_chat (/ws/voice, echo)
│   ├── auth/ + sync/            # Google OAuth, Gmail/Calendar background sync
│   └── vectorDB/                # Qdrant init + docker-compose
├── frontend/                    # Tauri v2 + Vite + TypeScript HUD
├── firmware/                    # ESP32 — PROTOCOL.md + sources, untested on hardware
├── camera/                      # empty — pillar 4 lives here
├── evals/                       # DeepEval evaluators, retrieval gate, fake_device, browser_trial
├── docs/schema.md               # the Postgres tables
├── CLAUDE.md                    # this file
├── AGENTS.md                    # pointer for non-Claude coding tools
└── agent.md                     # the agent roster + how routing works
```

> Never name a folder after a library you import. `backend/voice/` used to be
> `backend/pipecat/`, which hid the real Pipecat package from everything run in `backend/`.

---

## Tech stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Agent framework | **`langgraph` + `langchain` — mandatory for text agents, see the rule below** |
| Models | Dev: Ollama `qwen2.5:7b` (most agents), `mistral:latest` (Knowledge). `ENV=Prod`: OpenAI `gpt-6-luna` |
| Routing | **Laya** — local 421M non-autoregressive decision model (see *Routing*) |
| Voice | Pipecat 1.15 + Pipecat Flows; Deepgram STT, `gpt-6-luna`, Cartesia TTS; SmallWebRTC transport |
| Vectors | Qdrant (Docker via **Colima**, not Docker Desktop), `nomic-embed-text` embeddings |
| Long memory | Postgres 17 (`jarvis-postgres` container locally; Neon planned for Prod), SQLAlchemy 2, Alembic |
| Short memory | Redis (Homebrew service), `redis.asyncio` |
| Observability | Langfuse (traces + hosted prompts), `observability/metrics.py` → `calls.jsonl` |
| Evals | DeepEval, `retrieval_gate.py`; GitHub Actions in `.github/workflows/ci.yml` |
| Frontend | Tauri v2 + Vite + TypeScript, `@pipecat-ai/client-js` + `small-webrtc-transport` |
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

### `gpt-6-luna` constraints

- No custom `temperature` or `frequency_penalty` — it rejects them.
- Tool calling on chat completions needs `reasoning_effort="none"`.
- In browser-use, list it in `reasoning_models=["gpt-6-luna"]`.

---

## Agent rule — ALWAYS use LangGraph

Non-negotiable for every **text** agent in `backend/agent/`:

- Tools → `@tool(description="...")` from `langchain.tools`, on `async` functions
- Agents → `create_agent(llm, tools=[...], system_prompt=...)` from `langchain.agents`
- Models → `ChatOllama` from `langchain_ollama`, or `ChatOpenAI(model="gpt-6-luna",
  reasoning_effort="none")` when `ENV=Prod` — every agent file has the same `if` block
- Graph → `StateGraph` in `graph/workflow_creation.py`, routed with `Command(goto=...)`

**Never** write a raw `for` loop that calls the LLM directly inside an agent.
**Never** use `AsyncOpenAI` or `AsyncAnthropic` inside an agent file.

> `routes/chat.py` does use `AsyncOpenAI` against Ollama's compat endpoint — but only
> for the background fact-extraction call, which is not an agent. Keep it that way.

### The one exception — voice

`backend/voice/` uses **Pipecat Flows**, not LangGraph, because the pipeline has to
stream audio. Keep it thin:

- One `NodeConfig` per agent (`agent_node(name)`), same names as the graph.
- Voice tools in `voice/tools.py` take `flow_manager` first, have a docstring (Flows
  turns it into the tool description), and return `(result, None)`. They call the
  real LangChain tool with `.ainvoke({...})` — logic stays in `backend/tools/`.
- Agents connect through one global `switch_agent(flow_manager, agent)`.

---

## How routing works (and where it's going)

### Today — Laya
```
START → classify → exactly ONE of 11 agents → END
```
`_classify_node` reads `state["messages"][-1].content` and calls `route()` in
`agent/laya_router.py`. Laya is loaded **once** in `lifespan` (`load_router`) and
picks with `laya.predict_tournament(..., group_size=4)`: the 11 labels compete in
groups of 4, so no single decision ever sees 11+ options. Last labelled run:
**42/50**, vs 32/50 for a plain `decide` over all 11.

Multi-step work *does* happen — but only **inside** one agent, because
`create_agent` is a ReAct loop. So Calendar can call `list_events`, read the result,
then call `create_event`. What cannot happen is crossing from Calendar to Reminders.

```python
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
```

Gotchas, learned by running it:
- The schema key is **`criteria`**, not `options`, and `type` is required.
- **Load once** in `lifespan`. First call is ~4.6 s (MPS warmup); after that
  120–300 ms. Per-request loading would pay the 4.6 s every time.
- The shipped checkpoint has an **invalid calibration temperature for choice
  questions with 11+ options**. The tournament keeps each decision at ≤4; if you
  ever call `decide` over all agents, the confidence numbers are not trustworthy.
- Keep the criteria sharp and non-overlapping. The 42/50 run came with the tournament
  **and** rewritten Knowledge/Finance criteria; the two changes were not measured apart.
- `decide_batch` is **slower** than sequential calls on Apple Silicon
  (~627 ms/state vs ~200 ms). Do not design around batching here.
- A stale `~/.cache/huggingface/token` makes this public repo 401. Work around with
  `HF_HUB_DISABLE_IMPLICIT_TOKEN=1` or re-login to HF.

### Next — multi-hop
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

## Memory

| | Short memory | Long memory |
|---|---|---|
| Where | Redis, `short_memory/main.py` | Postgres, `long_memory/` + `memory/*_store.py` |
| Holds | The current conversation, last 40 messages | Facts, expenses, goals, journal entries, reminders |
| Key | `session:<session_id>` | One table each — see `docs/schema.md` |
| Lifetime | 1 h after the last message | Forever |

- Tools never touch SQLAlchemy directly. They call `memory/*_store.py`, which keeps
  the old JSON-store function names and return shapes.
- Ids are short 8-character strings (`uuid4().hex[:8]`) so the model can repeat them
  back (`complete_reminder`). Money is `Numeric(12, 2)`, never `Float`.
- Tables are created by `init_db()` at startup. Use Alembic (`cd backend/long_memory &&
  alembic ...`) once a change has to keep existing rows; `migrations/env.py` should read
  `DATABASE_URL` from `.env` rather than `alembic.ini`.
- Facts are extracted after each `/chat` turn and injected as
  `[Known facts about the user: ...]` in front of the next message.

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

Then add it to an agent's `tools=[...]` list. Restart the server. For voice, add a
matching function to `voice/tools.py` and its agent's list in `AGENT_TOOLS`.

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

**Not enforced in code yet.** Build the confirmation step before adding automations,
the supervisor, or any new side-effecting tool. The supervisor's side-effect
threshold should read from this table rather than inventing a second risk model.

---

## Coding standards

- Python 3.11+, type hints everywhere
- Async FastAPI handlers
- Pydantic models for every request/response shape
- No comments unless the *why* is non-obvious
- Prompts live in `backend/prompts/`, not inline in agent files — fetched from
  Langfuse with a local constant as fallback (`get_prompt(name=...) or LOCAL_PROMPT`).
  `get_prompt` takes the Langfuse **name** (`"weather_prompt"`), never the prompt text.
- Secrets via `os.getenv` + `python-dotenv`. Never commit `.env`, `firmware/.env`,
  `firmware/include/secrets.h`, `auth/credentials.json` or `auth/token.json`.
  Real keys go in `backend/.env` only, never in `.env.example`.

---

## Running locally

```bash
# Containers (Qdrant + Postgres) — Colima must be up first
colima start
cd backend/vectorDB && docker compose up -d
docker start jarvis-postgres          # created once; restarts with Docker

# Redis
brew services start redis

# Backend
conda activate main_env
cd backend
uvicorn main:app --reload

# Voice bot (second process, port 7860)
cd backend && python -m voice.main

# Frontend
cd frontend && npm run tauri dev
```

`backend/.env` needs `DATABASE_URL` (local:
`postgresql+psycopg://jarvis:jarvis@localhost:5432/jarvis`) and, for voice,
`OPENAI_API_KEY`, `DEEPGRAM_API_KEY`, `CARTESIA_API_KEY`.

If the backend won't start: Colima/Qdrant/Postgres down → start them; no RAG index →
`cd backend && python -m rag.offline`; port 8000 taken → the LaunchAgent already runs
it (`launchctl bootout` / `kickstart`).

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
redis-cli ping                      # PONG
docker exec jarvis-postgres pg_isready -U jarvis
python backend/observability/metrics.py      # latency percentiles per agent
python evals/evaluators/retrieval_gate.py    # exits 1 if retrieval regressed
```

---

## Build phases

| Phase | Focus | Status |
|---|---|---|
| 1 | Multi-agent graph, tools, RAG, memory, observability | **Done** |
| 2 | Laya replaces `classify`; fix the metrics blind spot | **Laya done** — blind spot still open |
| 2b | Postgres long memory + Redis short memory + session id for `/chat` | **Done** |
| 3 | Confirmation gate for High tools, then multi-hop supervisor with proven termination | **Next** |
| 4 | Voice: server-side STT/TTS, agents as Flows nodes, MIC button | **Mostly done** — real call untested; voice not on shared memory; no local STT/TTS |
| 5 | Proactive push: scheduled briefings and due reminders that reach me (pillar 5) | Planned |
| 6 | ESP32 firmware against `firmware/PROTOCOL.md`; `/ws/voice` running the real bot (pillar 3) | Sources written, untested |
| 7 | Phone — PWA over LAN first, native later (pillar 3) | Planned |
| 8 | Camera gesture control (pillar 4) | Planned |

Ordering rationale: the confirmation gate comes before the supervisor and before
proactive automations, because both multiply the number of side effects that can
fire without me watching. Shared voice memory before phone/ESP32, because pillar 3
means *the same* assistant on every device.

---

## Key design decisions

- **Local-first, with named exceptions.** Ollama + Qdrant + Postgres + Redis on this
  machine; no cloud model on the text hot path in dev. Exceptions: `ENV=Prod` uses
  `gpt-6-luna`, and the voice pipeline currently uses Deepgram, OpenAI and Cartesia —
  my voice leaves the machine. Local Whisper/Piper behind the same `ENV` switch is the
  way back. Neon for Prod Postgres is planned and would put long memory in the cloud.
- **`os.getenv` over `pydantic-settings`.** Simpler, no magic.
- **Prompts in Langfuse with local fallback.** Tune a prompt without redeploying;
  still runs if Langfuse is unreachable.
- **A non-generative model for routing.** A classifier that returns a typed choice
  cannot hand back an unparseable sentence. Generation is for agents, not decisions.
- **Conversation history lives on the server.** Redis keyed by `session_id`, not
  re-sent by the client; the client still sends `messages`, but only the last one is
  used.
- **Store functions as the seam.** Swapping JSON for Postgres changed only
  `memory/*_store.py`; no tool or route changed. Keep that boundary.
- **Full RAG rebuild is fine at this size.** Incremental indexing only pays off once
  rebuilds are slow or embeddings cost money.
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
- **Keep it simple.** Change only what the task needs. No extra abstractions,
  helpers or comments I didn't ask for.
- **Measure, don't estimate.** This repo has Langfuse, DeepEval and `metrics.py`
  wired up. If a claim is about latency, cost or accuracy, go get the real number.
