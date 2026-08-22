"""
Embedding Generation and Management module for the KMRL Platform.

This module coordinates local bi-encoder models via SentenceTransformers,
applying hardware acceleration auto-detection and execution batching.
"""

import logging
from typing import List, Optional
import torch

# Safely import sentence_transformers to allow execution context flexibility
try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except ImportError:
    SentenceTransformer = None

# Relative schema imports from within the same module folder
from .embedding_schema import EmbeddingConfig, VectorizedChunk
from ..preprocessing.chunker import TextChunk

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.embeddings.manager")


class EmbeddingManager:
    """
    Manages embedding model initialization, optimization pools, and batch execution workflows.
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None) -> None:
        """
        Initializes the embedding management framework, running model loads and hardware mapping.
        """
        if SentenceTransformer is None:
            logger.critical("Sentence-transformers dependency is missing in the execution scope.")
            raise RuntimeError("Missing required dependency package: 'sentence-transformers'.")

        self.config = config or EmbeddingConfig()
        self._device = self.config.device or self._detect_hardware_target()
        
        try:
            logger.info(f"Loading embedding model '{self.config.model_name}' onto targeted device hardware [{self._device}]...")
            self._model = SentenceTransformer(self.config.model_name, device=self._device)
            logger.info(f"Embedding model '{self.config.model_name}' successfully initialized.")
        except Exception as error:
            logger.exception(f"Fatal error occurred while creating embedding transformer for model: {self.config.model_name}")
            raise RuntimeError(f"Failed to compile embedding asset: {str(error)}") from error

    def _detect_hardware_target(self) -> str:
        """
        Heuristically targets the fastest executing available physical compute backend.
        """
        if torch.cuda.is_available():
            logger.info("NVIDIA CUDA hardware accelerator discovered.")
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("Apple Silicon MPS hardware accelerator discovered.")
            return "mps"
        
        logger.warning("No hardware accelerator found. Defaulting system execution target to CPU.")
        return "cpu"

    def generate_embeddings(self, chunks: List[TextChunk]) -> List[VectorizedChunk]:
        """
        Transforms collections of TextChunks into structured VectorizedChunk entities.
        """
        if not chunks:
            return []

        text_batch = [chunk.text for chunk in chunks]
        
        try:
            logger.info(f"Initiating vector generation pass over {len(text_batch)} text slices.")
            
            raw_embeddings = self._model.encode(
                sentences=text_batch,
                batch_size=self.config.batch_size,
                normalize_embeddings=self.config.normalize_embeddings,
                show_progress_bar=False,
                convert_to_numpy=True
            )

            vectorized_outputs: List[VectorizedChunk] = []
            
            for idx, chunk in enumerate(chunks):
                float_vector = raw_embeddings[idx].tolist()
                vectorized_outputs.append(
                    VectorizedChunk(
                        chunk_id=chunk.chunk_id,
                        text=chunk.text,
                        embedding=float_vector,
                        chunk_index=chunk.chunk_index
                    )
                )

            logger.info(f"Vectorization pass completed successfully. Generated {len(vectorized_outputs)} semantic entities.")
            return vectorized_outputs

        except Exception as error:
            logger.exception("An unhandled exception occurred while computing matrix elements during inference loops.")
            raise RuntimeError("Inference processing loop execution failure inside embedding layers.") from error

    def generate_single_query_embedding(self, query: str) -> List[float]:
        """
        Generates a single floating-point vector mapping for runtime user query workflows.
        """
        if not query or not query.strip():
            raise ValueError("Cannot extract semantic vectors from an empty or missing search query string.")
            
        try:
            raw_embedding = self._model.encode(
                sentences=query,
                normalize_embeddings=self.config.normalize_embeddings,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            return raw_embedding.tolist()
        except Exception as error:
            logger.exception(f"Failed to generate search vector for query string: '{query}'")
            raise RuntimeError("Query transformation pipeline block state error.") from error