"""
Compares OpenAI embedding dimension choices (512 vs 1536) for RAG quality,
scoring faithfulness/relevance on real rag/personal_info/ data, so the
prod embedding dimension in rag/config.py is picked from real numbers
instead of guessed. Needs a real OPENAI_API_KEY in backend/.env to run —
it builds real OpenAI embeddings for each candidate dimension.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

from llama_index.core import Settings, VectorStoreIndex, StorageContext
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore

from rag.document_loader import path_exists
from rag.chunking import chunk_document
from vectorDB.vectorDB_init import start_db

QUERIES = [
    "What is Damianos currently focused on in his AI career transition?",
    "What products or projects has Damianos built?",
    "What AI/ML skills does Damianos have?",
]

CANDIDATE_DIMENSIONS = [512, 1536]


def build_index_for_dimension(dim: int) -> VectorStoreIndex:
    api_key = os.getenv("OPENAI_API_KEY")
    Settings.llm = OpenAI(model="gpt-6-luna", api_key=api_key, temperature=0.1)
    Settings.embed_model = OpenAIEmbedding(
        model="text-embedding-3-small",
        api_key=api_key,
        dimensions=dim,
    )

    docstore = SimpleDocumentStore()
    documents = path_exists()
    nodes = [n for document in documents for n in chunk_document(document=document, docstore=docstore)]

    collection = f"dim_eval_{dim}"
    vector_client = start_db()
    if vector_client.collection_exists(collection_name=collection):
        vector_client.delete_collection(collection_name=collection)
    vector_store = QdrantVectorStore(client=vector_client, collection_name=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store, docstore=docstore)

    return VectorStoreIndex(nodes=nodes, storage_context=storage_context, store_nodes_override=True)


def score_dimension(dim: int) -> list[LLMTestCase]:
    index = build_index_for_dimension(dim)
    query_engine = index.as_query_engine()
    test_cases = []
    for query in QUERIES:
        response = query_engine.query(query)
        test_cases.append(
            LLMTestCase(
                input=query,
                actual_output=str(response),
                retrieval_context=[n.get_content() for n in response.source_nodes],
            )
        )
    return test_cases


def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is empty in backend/.env — set a real key before running this.")
        return

    metrics = [AnswerRelevancyMetric(threshold=0.85), FaithfulnessMetric(threshold=0.85)]
    for dim in CANDIDATE_DIMENSIONS:
        print(f"\n=== dimensions={dim} ===")
        evaluate(test_cases=score_dimension(dim), metrics=metrics)


if __name__ == "__main__":
    main()
