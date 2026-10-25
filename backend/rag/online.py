from .optimise_query import optimise_query
from .reranker import rerank_llm, rerank_cross_embed
from .retriever import dense_retriever , bm25_retriever , hybrid_retriever
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core import VectorStoreIndex
from llama_index.core import Settings
from .config import configure_llamaIndex
from functools import lru_cache
from vectorDB.vectorDB_init import start_db
from .vector_store import persist_dir, collection_name
from llama_index.core.storage.storage_context import StorageContext
from llama_index.core import load_index_from_storage
from llama_index.core.response_synthesizers import get_response_synthesizer

@lru_cache()
def load_index():
    configure_llamaIndex()
    vectorStore = QdrantVectorStore(client=start_db(),collection_name=collection_name())
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir(),vector_store=vectorStore)
    return load_index_from_storage(storage_context=storage_context)


def run_online(query:str,index:VectorStoreIndex| None=None,reranker_type:str="cross-encoder",retriever_type="hybrid",optimise=True,streaming=True):
    index = index or load_index()
    nodes_dict = index.docstore.docs
    optimised_query = optimise_query(llm = Settings.llm , query=query) if optimise else query
    if retriever_type == "dense":
        retriever = dense_retriever(index=index,node_dict=nodes_dict,top_k=5)
    elif retriever_type == "bm25" or retriever_type == "BM25":
        retriever = bm25_retriever(index,node_dict=nodes_dict,docstore=index.docstore)
    else:
        if retriever_type == "hybrid":
            retriever = hybrid_retriever(index,node_dict=nodes_dict,docstore=index.docstore)
        else:
            raise ValueError(f"Retriever {retriever_type} does not exist")
    if reranker_type == "cross-encoder":
        reranker = rerank_cross_embed()
    else:
        if reranker_type == "llm":
            reranker = rerank_llm()
        else:
            raise ValueError(f"not supported {reranker_type}")

    node = retriever.retrieve(optimised_query)
    if reranker is None:
        nodes = nodes[:3]
    else:
        nodes = reranker.postprocess_nodes(node,query_str=query)

    response = get_response_synthesizer(streaming=True)
    return response.synthesize(query,nodes=nodes)
