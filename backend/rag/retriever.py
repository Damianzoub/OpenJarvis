from llama_index.core.retrievers import RecursiveRetriever, QueryFusionRetriever
from llama_index.core import VectorStoreIndex
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.storage.docstore import SimpleDocumentStore

import Stemmer

def dense_retriever(index:VectorStoreIndex,node_dict:dict,top_k:int=5):
    base_index = index.as_retriever(similarity_top_k=top_k)

    return RecursiveRetriever(
        "vector",
        retriever_dict={"vector":base_index},
        node_dict=node_dict,
        verbose=False
    )

def bm25_retriever(index:VectorStoreIndex,node_dict:dict,docstore:SimpleDocumentStore,top_K:int=5):
    return BM25Retriever.from_defaults(
        docstore = docstore,
        similarity_top_k=top_K,
        stemmer=Stemmer.Stemmer("english"),
        language="english"
    )


def hybrid_retriever(index:VectorStoreIndex,node_dict:dict,docstore:SimpleDocumentStore,top_k:int=5):
    vector_retriever = dense_retriever(index,node_dict)
    bm25_retriever_retriever = bm25_retriever(index,node_dict,docstore=docstore)
    return QueryFusionRetriever(
        [vector_retriever,bm25_retriever_retriever],
        mode="reciprocal_rerank",
        num_queries=1,
        similarity_top_k=top_k,
        use_async=True,
        verbose=True
    )
