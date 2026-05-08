import json
import os

STORE_PATH = os.path.join(os.path.dirname(__file__), "store.json")


def load_facts() -> list[str]:
    if not os.path.exists(STORE_PATH):
        return []
    with open(STORE_PATH) as f:
        return json.load(f).get("facts", [])


def save_fact(fact: str) -> None:
    facts = load_facts()
    if fact not in facts:
        facts.append(fact)
        with open(STORE_PATH, "w") as f:
            json.dump({"facts": facts}, f, indent=2)
