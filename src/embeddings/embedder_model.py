import logging
from typing import List
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class BGEEmbedder:
    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5"):
        logger.info(f"Loading embedding model: {model_name}")
        # BGE models use specific instruction prompts for retrieval tasks
        self.query_instruction = "Represent this sentence for searching relevant passages: "
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds document chunks (no prefix needed for documents in BGE)."""
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """Embeds a search query (BGE requires instruction prefix)."""
        formatted_query = f"{self.query_instruction}{query}"
        embedding = self.model.encode(formatted_query, normalize_embeddings=True)
        return embedding.tolist()