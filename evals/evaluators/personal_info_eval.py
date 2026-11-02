import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, ToolCorrectnessMetric
from deepeval.models.llms.ollama_model import OllamaModel
from deepeval.test_case import LLMTestCase, ToolCall
from langchain_core.messages import AIMessage

from backend.rag.config import configure_llamaIndex
from backend.rag.online import load_index
from backend.rag.retriever import hybrid_retriever
from backend.rag.reranker import rerank_cross_embed
from backend.agent.knowledge_agent import make_knowledge_agent

QUERIES = [
    "What is Damianos currently focused on in his AI career transition?",
    "What products or projects has Damianos built?",
    "What AI/ML skills does Damianos have?",
]


def get_context(index, query: str) -> list[str]:
    retriever = hybrid_retriever(index, index.docstore.docs, docstore=index.docstore)
    nodes = retriever.retrieve(query)
    nodes = rerank_cross_embed().postprocess_nodes(nodes, query_str=query)
    return [n.get_content() for n in nodes]


def get_tools_called(messages: list) -> list[str]:
    names = []
    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            names.extend(call["name"] for call in message.tool_calls)
    return names


async def main():
    configure_llamaIndex()
    index = load_index()
    agent = make_knowledge_agent()

    test_cases = []
    for query in QUERIES:
        result = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})
        test_cases.append(
            LLMTestCase(
                input=query,
                actual_output=result["messages"][-1].content,
                retrieval_context=get_context(index, query),
                tools_called=[ToolCall(name=n) for n in get_tools_called(result["messages"])],
                expected_tools=[ToolCall(name="search_knowledge")],
            )
        )

    judge = OllamaModel(model="qwen2.5:7b", base_url="http://localhost:11434")
    metrics = [
        AnswerRelevancyMetric(threshold=0.85),
        FaithfulnessMetric(threshold=0.85),
        ToolCorrectnessMetric(include_reason=False, model=judge),
    ]
    evaluate(test_cases=test_cases, metrics=metrics)


if __name__ == "__main__":
    asyncio.run(main())
