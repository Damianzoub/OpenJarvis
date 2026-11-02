# OpenJarvis — Agent Reference

The agent roster, how routing picks between them, and how to add a new one.

Audited against the code **2026-10-20**. See `CLAUDE.md` for project-wide rules.

---

## How a request flows

```
POST /chat
   │
   ▼
routes/chat.py ──── loads known facts from memory, prepends them to the message
   │
   ▼
graph/workflow_creation.py   (compiled StateGraph, built once in main.py lifespan)
   │
   ├─ classify  ──── agent/orchestrator.py :: route()
   │                 asks the LLM for an agent name, substring-matches the reply
   │                 Command(goto=<AgentName>)
   ▼
   one agent  ──── create_agent() ReAct loop: LLM ⇄ tools until it answers
   │
   ▼
  END  ──── streamed back as SSE, then a background task extracts new facts
```

**One agent per request. Always.** Every agent has `add_edge(<Agent>, END)`.

### What this means in practice

Multi-step work happens **inside** an agent, never **across** agents:

- ✅ *"Am I free Friday, and if so book 3pm"* — Calendar calls `list_events`, reads
  the result, then calls `create_event`. Works today, because it's one domain.
- ❌ *"Check my calendar then remind me"* — classify picks **either** Calendar
  **or** Reminders, does that half, and returns. The other half is dropped with
  no error and no warning.

So: **multi-step at the tool level, single-shot at the agent level.** ReAct depth
without orchestration breadth. Fixing this is Phase 3 in `CLAUDE.md`.

One more limitation worth knowing: `_classify_node` passes only
`state["messages"][-1].content`. The router never sees conversation history, so it
cannot resolve "do that again" or "the second one".

---

## The roster

11 nodes. Ten real agents plus a `General` fallback.

| Agent | Node name | Factory | Model | Tools |
|---|---|---|---|---|
| **Filesystem** | `Filesystem` | `make_filesystem_agent` | `qwen2.5:7b` | `search_files`, `read_file`, `open_app` |
| **Email** | `Email` | `make_gmail_agent` | `qwen2.5:7b` | `read_emails`, `create_draft` |
| **Calendar** | `Calendar` | `make_agenda_agent` | `qwen2.5:7b` | `list_events`, `create_event` |
| **Weather** | `Weather` | `make_weather_agent` | `qwen2.5:7b` | `get_weather` |
| **News** | `News` | `make_news_agent` | `qwen2.5:7b` | `get_news` |
| **Music** | `Music` | `make_music_agent` | `qwen2.5:7b` | `play_music`, `pause_music`, `previous_track`, `next_track`, `set_volume`, `current_track_info` |
| **Knowledge** | `Knowledge` | `make_knowledge_agent` | **`mistral:latest`** | `search_knowledge`, `ingest_document` |
| **Reminders** | `Reminders` | `make_reminders_agent` | `qwen2.5:7b` | `add_reminder`, `list_reminders`, `complete_reminder` |
| **Growth** | `Growth` | `make_growth_agent` | `qwen2.5:7b` | `log_goal`, `log_progress`, `list_goals` |
| **Finance** | `Finance` | `make_finance_agent` | `qwen2.5:7b` | `log_expense`, `get_budget_summary`, `get_quote`, `summarize_market_news` |
| **General** | `General` | `make_general_agent` | `qwen2.5:7b` | *(none)* — simple FAQ and chitchat |

All agents use `temperature=0.1` against `http://localhost:11434`.

### Knowledge is the odd one out

It's the **only** agent on `mistral:latest`. Everything else is `qwen2.5:7b`.
Because Ollama used to keep one model resident, any hop between Knowledge and
another agent forced a multi-second reload. Mitigated with
`OLLAMA_MAX_LOADED_MODELS=2` (see `CLAUDE.md`), but worth remembering: adding a
third model would reintroduce the problem.

### Agent → prompt mapping

Every prompt lives in `backend/prompts/` and is fetched from Langfuse with a local
constant as fallback: `get_prompt(name=...) or LOCAL_PROMPT`.

| Agent | Prompt file | Langfuse name |
|---|---|---|
| Calendar | `calendar_prompt.py` | `calendar_prompt` |
| Email | `email_prompt.py` | `email_prompt` |
| Weather | `weather_prompt.py` | `weather_prompt` |
| News | `news_prompt.py` | `news_prompt` |
| Music | `music_prompt.py` | `music_prompt` |
| Knowledge | `rag_prompt.py` | `rag_prompt` |
| Reminders | `reminders_prompt.py` | `reminders_prompt` |
| Growth | `growth_prompt.py` | `growth_prompt` |
| Finance | `finance_prompt.py` | `finance_prompt` |
| *router* | `router_prompt.py` | `router_prompt` |

Two exceptions — **Filesystem** and **General** have their prompts written inline
in their agent files rather than in `prompts/`. Inconsistent; worth moving.

Calendar's prompt is the only one that takes runtime arguments — it injects
`today_str` and `tomorrow_str` (Athens time, UTC+3) so the model can resolve
"tomorrow".

---

## Orphaned tools

Defined, decorated, and wired into **nothing**. Either connect them or delete them:

| Tool | File | Note |
|---|---|---|
| `open_site`, `search` | `tools/browser.py` | The whole module is unreachable. No agent imports it. There is no Browser agent. |
| `delete_event` | `tools/calendar.py` | Calendar agent only gets `list_events` and `create_event`. |
| `read_rss_feed` | `tools/finance.py` | Probably intended as an internal helper for `summarize_market_news`, but it carries a `@tool` decorator as if it were callable. |

`tools/browser.py` is the notable one — `browser-use` and `playwright` are both in
`requirements.txt` for it, and nothing uses it.

---

## Adding a new agent

1. **Tools** — `backend/tools/<domain>.py`, `@tool`-decorated async functions.
   See *How to add a new tool* in `CLAUDE.md`.
2. **Prompt** — `backend/prompts/<domain>_prompt.py`, and register the same name in
   Langfuse so it can be tuned without a redeploy.
3. **Agent** — `backend/agent/<domain>_agent.py`:

```python
from langchain.agents import create_agent
from langchain_ollama import ChatOllama

from prompts.<domain>_prompt import <DOMAIN>_PROMPT
from prompts.langfuse_client import get_prompt
from tools.<domain> import tool_a, tool_b


def make_<domain>_agent():
    return create_agent(
        ChatOllama(
            model="qwen2.5:7b",
            base_url="http://localhost:11434",
            temperature=0.1,
        ),
        tools=[tool_a, tool_b],
        system_prompt=get_prompt(name="<domain>_prompt") or <DOMAIN>_PROMPT,
    )
```

4. **Register it** in `graph/workflow_creation.py` — there are **four** places,
   and missing any one of them fails in a different confusing way:
   - import the factory
   - add the node: `builder.add_node("<Name>", make_<domain>_agent())`
   - add the edge: `builder.add_edge("<Name>", END)`
   - add `"<Name>"` to the `Literal[...]` on `_classify_node`'s return type
5. **Teach the router** — add the branch in `orchestrator.py :: route()` **and**
   describe the domain in `prompts/router_prompt.py`. An agent the router was never
   told about is dead code.
6. **Restart** the server. The graph is compiled once in `main.py`'s `lifespan`;
   there is no hot reload of the graph.

### When Laya replaces the router

Steps 5 changes: instead of a prompt plus substring branches, you add one line to
the `criteria` dict — `"<Name>": "<one-line description of what it owns>"`. That
description *is* the routing logic.

Watch the option count. Laya's shipped confidence calibration is invalid at **11 or
more** choices, and the roster is already at 11. Adding a twelfth is fine for
picking correctly, but don't trust the confidence number without refitting. Details
in `CLAUDE.md`.

---

## Observability

- **Langfuse** — a `CallbackHandler` is attached to every `graph.astream` call in
  `routes/chat.py`. Each turn is its own trace. There is no session/conversation id
  yet, so turns in one conversation are not linked.
- **`observability/metrics.py`** — appends per-call token counts, latency and cost
  to `calls.jsonl`. Run `python backend/observability/metrics.py [agent]` for
  count, total tokens, cost and p50/p95/p99 latency.
- **Cost is always `$0.0`** for local models, by design — the table in `metrics.py`
  prices Ollama models at zero. Latency is the metric that matters here.

### ⚠ The router is not instrumented

`routes/chat.py` skips graph updates whose namespace is empty:

```python
if not namespace:
    continue
```

Agents are sub-graphs, so they have a namespace. **Top-level nodes like `classify`
do not** — so `record_call` has never recorded a single routing decision. There is
no `classify` row in `calls.jsonl` and there never has been.

This matters most for the Phase 3 supervisor, which will also be a top-level node
and would be invisible in exactly the same way — precisely the component whose cost
you most need to watch. Fix the namespace handling, or record timings inside the
routing function itself.

---

## Evals

`evals/evaluators/` holds DeepEval suites:

| File | Checks |
|---|---|
| `tool_correctness_eval.py` | did the agent call the right tools |
| `faithfulness.py` | is the answer grounded in retrieved context |
| `relevance.py` | does the answer address the question |
| `personal_info_eval.py` | personal-fact recall |
| `run_evals.py` | runner |

`evals/test/fake_device.py` is an empty stub — intended as a software stand-in for
the ESP32 so `firmware/PROTOCOL.md` can be exercised without hardware.

Routing accuracy has **no eval suite yet**. It's the obvious one to add alongside
the Laya swap: a fixed set of requests with their expected agent, so a routing
regression is caught by a test instead of by noticing a weird answer.
