"""
Retrieval gate: exits 1 if too many golden queries fail to retrieve their expected fact.

Needs Qdrant + Ollama running and the index built (python -m rag.offline).
Run from repo root: python evals/evaluators/retrieval_gate.py
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env")

from backend.rag.config import configure_llamaIndex
from backend.rag.online import load_index
from backend.rag.reranker import rerank_cross_embed
from backend.rag.retriever import hybrid_retriever

# (query, text that must appear in the top 3 chunks) — copied from rag/personal_info/bio.md
GOLDEN = [
    ("When did Damianos start the AI Architect roadmap?", "2026-07-03"),
    ("Which institute co-runs his MSc in AI?", "demokritos"),
    ("What is AIRIA?", "invoice-extraction"),
    ("What is SmartRep?", "voice-agent"),
    ("What does the Inbox Ops Assistant do?", "triages gmail"),
    ("What was dad-videobot built with?", "rasa"),
    ("Which Spanish certification is he studying for?", "dele"),
    ("How does he organize his second brain?", "para method"),
]

MIN_PASS_RATE = 0.9


def main() -> int:
    configure_llamaIndex()
    index = load_index()
    retriever = hybrid_retriever(index, index.docstore.docs, docstore=index.docstore)
    reranker = rerank_cross_embed()

    passed = 0
    for query, expected in GOLDEN:
        nodes = reranker.postprocess_nodes(retriever.retrieve(query), query_str=query)
        ok = any(expected in " ".join(n.get_content().lower().split()) for n in nodes)
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {query}")

    rate = passed / len(GOLDEN)
    print(f"\n{passed}/{len(GOLDEN)} passed ({rate:.0%}, need {MIN_PASS_RATE:.0%})")
    return 0 if rate >= MIN_PASS_RATE else 1


if __name__ == "__main__":
    sys.exit(main())
