from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams,Distance,PointStruct


def start_db():
    return  QdrantClient(url="http://localhost:6333")
    


