import json
import os
from datetime import datetime, timezone

LOG_PATH = os.path.join(os.path.dirname(__file__), "calls.jsonl")

# $ per 1M tokens (prompt, completion). Local Ollama models are free.
COST_PER_1M = {
    "qwen2.5:7b": (0.0, 0.0),
    "mistral:latest": (0.0, 0.0),
    "gpt-6-luna": (0.10, 0.50),
}
DEFAULT_COST_PER_1M = (0.0, 0.0)


def record_call(agent: str, model: str, prompt_tokens: int, completion_tokens: int, latency_ms: float) -> None:
    prompt_price, completion_price = COST_PER_1M.get(model, DEFAULT_COST_PER_1M)
    cost = (prompt_tokens / 1_000_000) * prompt_price + (completion_tokens / 1_000_000) * completion_price
    entry = {
        "agent": agent,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cost": cost,
        "latency_ms": latency_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _load_calls(agent: str | None = None) -> list[dict]:
    if not os.path.exists(LOG_PATH):
        return []
    calls = []
    with open(LOG_PATH) as f:
        for line in f:
            if line.strip():
                calls.append(json.loads(line))
    if agent:
        calls = [c for c in calls if c["agent"] == agent]
    return calls


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = min(int(len(values) * p), len(values) - 1)
    return values[index]


def get_stats(agent: str | None = None) -> dict:
    calls = _load_calls(agent)
    if not calls:
        return {"count": 0}
    latencies = [c["latency_ms"] for c in calls]
    return {
        "count": len(calls),
        "total_tokens": sum(c["total_tokens"] for c in calls),
        "total_cost": round(sum(c["cost"] for c in calls), 6),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1),
        "p50_latency_ms": round(_percentile(latencies, 0.50), 1),
        "p95_latency_ms": round(_percentile(latencies, 0.95), 1),
        "p99_latency_ms": round(_percentile(latencies, 0.99), 1),
    }


if __name__ == "__main__":
    import sys
    agent = sys.argv[1] if len(sys.argv) > 1 else None
    print(json.dumps(get_stats(agent), indent=2))
