import os

from llama_index.core.ingestion import IngestionPipeline,DocstoreStrategy
from llama_index.core import StorageContext,VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from vectorDB.vectorDB_init import start_db

from .config import configure_llamaIndex
from .document_loader import path_exists
from .chunking import chunk_document
from llama_index.core.storage.docstore import SimpleDocumentStore
from .vector_store import build_index,collection_name,persist_dir

def main():
    configure_llamaIndex()
    saved = os.path.join(os.path.dirname(__file__), "personal_info", "index.json")
    docstore = SimpleDocumentStore.from_persist_path(saved) if os.path.exists(saved) else SimpleDocumentStore()
    vector_store = QdrantVectorStore(start_db(),collection_name=collection_name(), docstore=docstore)
    pipeline = IngestionPipeline(
        transformations=[],
        docstore=SimpleDocumentStore(),
        vector_store=vector_store,
        docstore_strategy=DocstoreStrategy.UPSERTS_AND_DELETE,
        disable_cache=True
    )
    pipeline_dir = persist_dir() + "/personal_info"
    if os.path.exists(pipeline_dir):
        pipeline.load(pipeline_dir)
    
    documents = path_exists()
    changed = pipeline.run(documents=documents)
    storage = StorageContext.from_defaults(vector_store=vector_store,docstore=docstore)
    index = VectorStoreIndex([],storage_context=storage,store_nodes_override=True)
    for doc in changed:
        docstore.delete_ref_doc(doc.id,raise_error=False)
        index.insert_nodes(chunk_document(doc,docstore=docstore))

    for ref_id in set(docstore.get_all_ref_doc_info() or {}) - {doc.id_ for doc in documents}:
        docstore.delete_ref_doc(ref_id, raise_error=False)

    pipeline.persist(pipeline_dir)
    storage.persist(persist_dir=persist_dir())

if __name__ == "__main__":
    main()
    print("Successfully")