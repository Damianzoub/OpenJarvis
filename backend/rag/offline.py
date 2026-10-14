from .config import configure_llamaIndex
from .document_loader import path_exists
from .chunking import chunk_document
from llama_index.core.storage.docstore import SimpleDocumentStore
from .vector_store import build_index

def main():
    configure_llamaIndex()
    docstore = SimpleDocumentStore()
    documents = path_exists()
    nodes = [n for document in documents for n in chunk_document(document=document,docstore=docstore)]
    index = build_index(nodes,docstore)
    return index

if __name__ == "__main__":
    main()
    print("Successfully")