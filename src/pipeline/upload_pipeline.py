"""
Document Upload and Processing Pipeline for the KMRL Platform.

This module provides the master orchestration workflow, chaining together 
parsing, cleaning, chunking, embedding, and vector storage into a single transactional process.
"""

import logging
from typing import BinaryIO, Dict, Any

# Import orchestrators from all previous stages
from ..ingestion.document_loader import DocumentLoader
from ..preprocessing.cleaner import TextCleaner
from ..preprocessing.chunker import TokenAwareChunker, TextChunk
from ..embeddings.manager import EmbeddingManager
from ..vector_store.base import BaseVectorStore

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.pipeline.upload_pipeline")


class UploadResult:
    """Data envelope for reporting the final status of a document upload."""
    def __init__(self, document_id: str, filename: str, chunks_processed: int, status: str):
        self.document_id = document_id
        self.filename = filename
        self.chunks_processed = chunks_processed
        self.status = status


class DocumentUploadPipeline:
    """
    Master pipeline orchestrating the complete document-to-vector lifecycle.
    """

    def __init__(
        self,
        loader: DocumentLoader,
        cleaner: TextCleaner,
        chunker: TokenAwareChunker,
        embedder: EmbeddingManager,
        vector_store: BaseVectorStore,
        target_collection: str = "kmrl_enterprise_docs"
    ) -> None:
        """
        Initializes the pipeline with required engine dependencies.

        Args:
            loader: Configured DocumentLoader instance.
            cleaner: Configured TextCleaner instance.
            chunker: Configured TokenAwareChunker instance.
            embedder: Configured EmbeddingManager instance.
            vector_store: Active Vector DB connection instance.
            target_collection: The database collection name to store vectors in.
        """
        self.loader = loader
        self.cleaner = cleaner
        self.chunker = chunker
        self.embedder = embedder
        self.vector_store = vector_store
        self.target_collection = target_collection
        
        # Ensure the destination collection exists in the vector store before processing begins
        # We assume an embedding size of 1024 (matching BAAI/bge-large-en-v1.5 defaults)
        self.vector_store.create_collection(
            collection_name=self.target_collection,
            vector_size=1024,
            distance_metric="Cosine"
        )

    def process_document(self, file_stream: BinaryIO, filename: str, file_size: int, user_metadata: Dict[str, Any] = None) -> UploadResult:
        """
        Executes the end-to-end processing chain on a raw document stream.

        Args:
            file_stream: Seekable binary stream of the uploaded file.
            filename: Original name of the file.
            file_size: Size of the file in bytes.
            user_metadata: Optional dictionary of additional tags (e.g., author, department) to attach to vectors.

        Returns:
            UploadResult containing the generated UUID and processing metrics.
        """
        logger.info(f"--- Starting upload pipeline for file: {filename} ({file_size} bytes) ---")
        
        try:
            # Step 1: Parsing and Extraction
            logger.debug("Step 1: Extracting content blocks...")
            unified_doc = self.loader.load_from_stream(file_stream, filename, file_size)
            
            # Step 2: Cleaning and Normalization
            logger.debug("Step 2: Cleaning extracted text...")
            cleaned_texts = [self.cleaner.clean(block.text) for block in unified_doc.content_blocks]
            
            # Step 3: Semantic Chunking
            logger.debug("Step 3: Chunking document text...")
            all_chunks: list[TextChunk] = []
            
            # We stitch the cleaned text blocks together to preserve cross-page context, 
            # then pass the massive unified string to the token-aware chunker.
            unified_text = "\n\n".join(t for t in cleaned_texts if t)
            all_chunks = self.chunker.chunk_document(text=unified_text, document_id=unified_doc.document_id)
            
            if not all_chunks:
                logger.warning(f"Pipeline finished early. No valid text could be extracted from {filename}.")
                return UploadResult(unified_doc.document_id, filename, 0, "completed_empty")

            # Step 4: Vector Embedding Generation
            logger.debug("Step 4: Generating dense embeddings...")
            vectorized_chunks = self.embedder.generate_embeddings(all_chunks)

            # Step 5: Vector Database Upsertion
            logger.debug("Step 5: Upserting vectors to storage...")
            
            # Compile global metadata applying to all chunks in this document
            base_metadata = user_metadata or {}
            base_metadata.update({
                "document_id": unified_doc.document_id,
                "filename": unified_doc.filename,
                "extension": unified_doc.extension
            })
            
            success = self.vector_store.upsert_chunks(
                collection_name=self.target_collection,
                vectorized_chunks=vectorized_chunks,
                metadata=base_metadata
            )

            if not success:
                raise RuntimeError("Vector database failed to acknowledge upsert command.")

            logger.info(f"--- Pipeline completed successfully for {filename}. Stored {len(vectorized_chunks)} chunks. ---")
            
            return UploadResult(
                document_id=unified_doc.document_id,
                filename=unified_doc.filename,
                chunks_processed=len(vectorized_chunks),
                status="success"
            )

        except Exception as error:
            logger.exception(f"Pipeline encountered a fatal error while processing {filename}.")
            raise RuntimeError(f"Document processing pipeline failed: {str(error)}") from error