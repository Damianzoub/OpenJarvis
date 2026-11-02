"""Ask Jarvis from the terminal. Dev tool, not an interface.

    python scripts/ask.py "am I free friday afternoon"
"""
import json
import os
import sys

import httpx

BASE = os.getenv("JARVIS_URL", "http://localhost:8000")


def main() -> None:
    message = " ".join(sys.argv[1:])
    if not message:
        sys.exit("usage: python scripts/ask.py <message>")

    payload = {"messages": [{"role": "user", "content": message}]}
    agent = "?"

    with httpx.stream("POST", f"{BASE}/chat", json=payload, timeout=120) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            agent = event.get("agent", agent)
            kind = event["type"]
            if kind == "tool":
                print(f"[{agent}] {event['content']}")
            elif kind == "text":
                print(f"[{agent}] {event['content']}")
            elif kind == "done":
                print(f"--- handled by {agent}")


if __name__ == "__main__":
    main()
