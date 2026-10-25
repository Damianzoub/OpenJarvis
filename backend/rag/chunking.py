from llama_index.core.node_parser import MarkdownNodeParser,SentenceSplitter,HierarchicalNodeParser
from llama_index.core.schema import IndexNode
from llama_index.core.storage.docstore import SimpleDocumentStore

STRUCTURED_DOCS = (".md",".html",".txt")

def is_structured(document)->bool:
    file_name = document.metadata.get("file_path","")
    if file_name.endswith(STRUCTURED_DOCS):
        return True
    return False

MAX_LENGTH=512
def chunk_document(document,docstore:SimpleDocumentStore):
    nodes_index =[ ]
    if is_structured(document):
        parent_parser = MarkdownNodeParser().get_nodes_from_documents([document])
        child_splitter = SentenceSplitter(separator="## ",chunk_size=256,chunk_overlap=30)
        for parent in parent_parser:
            docstore.add_documents([parent])
            if len(parent.get_content().split()) < MAX_LENGTH:
                nodes_index.append(parent)
            else:
                child_section = child_splitter.get_nodes_from_documents([parent])
                for child in child_section:
                    nodes_index.append(IndexNode.from_text_node(node=child,index_id=parent.node_id))
    else:
        nodes_parser = HierarchicalNodeParser.from_defaults(chunk_sizes=[1024,256])
        nodes_index = nodes_parser.get_nodes_from_documents([document])
        docstore.add_documents(nodes_index)

    return nodes_index
