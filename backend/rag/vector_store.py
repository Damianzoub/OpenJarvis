from vectorDB.vectorDB_init import start_db
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex,StorageContext
from pathlib import Path
from llama_index.core.storage.docstore import SimpleDocumentStore
import os

STORAGE_LOC = Path(__file__).parent

def _env_suffix():
    return "prod" if os.getenv("ENV") == "Prod" else "dev"

def collection_name():
    return f"my_information_{_env_suffix()}"

def persist_dir():
    return str(STORAGE_LOC / f"my_information_{_env_suffix()}")

def build_index(nodes,docstore:SimpleDocumentStore,name:str|None=None):
    name = name or collection_name()
    vector_client = start_db()
    if vector_client.collection_exists(collection_name=name):
        vector_client.delete_collection(collection_name=name)
    qdrant_client = QdrantVectorStore(client=vector_client,collection_name=name)
    storage_content = StorageContext.from_defaults(vector_store=qdrant_client,docstore=docstore)

    index = VectorStoreIndex(
        nodes = nodes,
        storage_context=storage_content,
        store_nodes_override=True,
        show_progress=True
    )
    storage_content.persist(persist_dir=persist_dir())
    return index