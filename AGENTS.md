# AGENTS.md

Instructions for any AI coding tool working in this repository.

**The full developer reference is [`CLAUDE.md`](./CLAUDE.md). Read it first.**
The agent roster and routing details are in [`agent.md`](./agent.md).

This file exists so non-Claude tools (Codex, Cursor, Copilot, Gemini CLI, …) pick
up the same rules. It is deliberately a short pointer — the detail lives in
`CLAUDE.md`, so the two cannot drift apart.

---

## What this project is

OpenJarvis — a local-first personal AI assistant meant to run on laptop, phone and
eventually an ESP32 device; to be spoken to rather than typed at; to be drivable by
camera gestures; and to reach out proactively when something needs attention.

Local by default: Ollama for models, Qdrant for vectors.

---

## Hard rules

1. **All agents use LangGraph / LangChain.** Tools are `@tool`-decorated async
   functions from `langchain.tools`. Agents are built with
   `create_agent(llm, tools=[...], system_prompt=...)`. Models are `ChatOllama`.
2. **Never** write a raw loop calling the LLM inside an agent file.
3. **Never** use `AsyncOpenAI` or `AsyncAnthropic` inside an agent file. (The one
   permitted use is the non-agent fact-extraction call in `routes/chat.py`.)
4. **Python 3.11+ with type hints everywhere.** Async FastAPI handlers. Pydantic
   models for every request/response shape.
5. **No comments** unless the *why* is non-obvious.
6. **Prompts live in `backend/prompts/`**, never inline in agent files, and are
   fetched as `get_prompt(name=...) or LOCAL_PROMPT`.
7. **Never commit secrets** — `.env`, `auth/credentials.json`, `auth/token.json`.
8. **Respect the safety levels** in `CLAUDE.md`. Side-effecting tools (sending
   email, creating events, writing files) need confirmation, not silent execution.

## Before you trust this repo's docs

Parts of the old documentation described files that never existed (`tools/base.py`,
`tools/registry.py`, `agent/planner.py`, a `ToolPlugin` base class, pkgutil
auto-discovery). Those are gone from the docs now, but the lesson stands:
**verify against the code before building on a documented interface.** If a doc and
the code disagree, the code wins — then fix the doc.

## How the maintainer wants to work

- **Explain before editing.** He is building this to learn the agent/graph stack
  hands-on. Walk through a change and let him write it, unless he explicitly asks
  you to make the edit.
- **Plain English first.** Lead with the point in ordinary words; introduce the
  technical term after the plain version.
- **Measure, don't estimate.** Langfuse, DeepEval and `backend/observability/metrics.py`
  are already wired up. Any claim about latency, cost or accuracy should come with a
  real number.
