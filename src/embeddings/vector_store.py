import chromadb
import logging
from typing import List, Dict, Any
from src.ingestion.internal_schema import Chunk
from .embedder_model import BGEEmbedder

logger = logging.getLogger(__name__)

class ChromaVectorStore:
    def __init__(self, persist_directory: str = "./database/chroma_db", collection_name: str = "kmrl_docs"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.embedder = BGEEmbedder()
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_chunks(self, chunks: List[Chunk]):
        """Embeds and inserts chunks into ChromaDB."""
        logger.info(f"Adding {len(chunks)} chunks to Vector Store.")
        texts = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        ids = [f"{meta['source']}_chunk_{meta['chunk_index']}" for meta in metadatas]
        
        embeddings = self.embedder.embed_documents(texts)
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Performs vector similarity search."""
        query_embedding = self.embedder.embed_query(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        formatted_results = []
        if results['documents']:
            for doc, meta, distance in zip(results['documents'][0], results['metadatas'][0], results['distances'][0]):
                formatted_results.append({
                    "content": doc,
                    "metadata": meta,
                    "score": distance # Note: Chroma returns distance, lower is better
                })
        return formatted_results