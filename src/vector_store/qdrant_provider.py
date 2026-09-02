"""
Qdrant Vector Database Provider for the KMRL Platform.

This module implements the BaseVectorStore interface, providing a high-performance
connection to a Qdrant instance for managing collections, upserting dense vectors, 
and executing metadata-filtered semantic similarity searches.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

# Safely import Qdrant models and client
try:
    from qdrant_client import QdrantClient  # type: ignore
    from qdrant_client.http import models as qmodels  # type: ignore
except ImportError:
    QdrantClient = None
    qmodels = None

from .base import BaseVectorStore, SearchFilter, SearchResult
from ..embeddings.embedding_schema import VectorizedChunk

# Setup logger mapping to Stage 0 configurations
logger = logging.getLogger("document_intelligence.vector_store.qdrant_provider")


class QdrantProvider(BaseVectorStore):
    """
    Concrete Qdrant implementation for vector storage and retrieval.
    """

    def __init__(self, host: str = "localhost", port: int = 6333, api_key: Optional[str] = None, timeout: int = 15) -> None:
        """
        Initializes the connection to the Qdrant database cluster.

        Args:
            host: Network hostname or IP address of the Qdrant server.
            port: REST API port (default is 6333; gRPC is typically 6334).
            api_key: Optional authentication key for managed cloud deployments.
            timeout: Network timeout threshold in seconds.
        """
        if QdrantClient is None:
            logger.critical("Qdrant client library is not installed in the environment.")
            raise RuntimeError("Missing dependency: 'qdrant-client'. Please install to enable Qdrant storage.")

        self.host = host
        self.port = port
        
        try:
            logger.info(f"Establishing connection to Qdrant cluster at {self.host}:{self.port}...")
            self.client = QdrantClient(
                host=self.host,
                port=self.port,
                api_key=api_key,
                timeout=timeout
            )
            # Verify connection by fetching cluster telemetry/status
            self.client.get_collections()
            logger.info("Successfully authenticated and connected to Qdrant cluster.")
        except Exception as error:
            logger.exception("Failed to connect to the targeted Qdrant database.")
            raise ConnectionError(f"Qdrant connection failure at {self.host}:{self.port}.") from error

    def create_collection(self, collection_name: str, vector_size: int, distance_metric: str = "Cosine") -> bool:
        """
        Provisions a new vector collection index.
        """
        try:
            # Map platform distance string to Qdrant's internal enum constraints
            metric_mapping = {
                "Cosine": qmodels.Distance.COSINE,
                "Euclidean": qmodels.Distance.EUCLID,
                "Dot": qmodels.Distance.DOT
            }
            target_metric = metric_mapping.get(distance_metric, qmodels.Distance.COSINE)

            # Check if collection already exists to prevent overwrite errors
            existing_collections = self.client.get_collections().collections
            if any(col.name == collection_name for col in existing_collections):
                logger.warning(f"Collection '{collection_name}' already exists. Skipping creation.")
                return True

            logger.info(f"Provisioning new Qdrant collection: '{collection_name}' (Size: {vector_size}, Metric: {target_metric}).")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(
                    size=vector_size,
                    distance=target_metric
                )
            )
            return True
        except Exception as error:
            logger.exception(f"Failed to create Qdrant collection '{collection_name}'.")
            return False

    def upsert_chunks(self, collection_name: str, vectorized_chunks: List[VectorizedChunk], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Maps standard VectorizedChunks to Qdrant PointStructs and inserts them in batch.
        """
        if not vectorized_chunks:
            return True

        base_metadata = metadata or {}
        points: List[qmodels.PointStruct] = []

        try:
            for chunk in vectorized_chunks:
                # Merge the top-level document metadata with the chunk-specific parameters
                payload = {
                    **base_metadata,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "chunk_index": chunk.chunk_index
                }
                
                # Qdrant requires UUID or integer formats for point IDs
                # We hash the deterministic chunk_id into a valid UUID string
                point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.chunk_id))

                points.append(
                    qmodels.PointStruct(
                        id=point_uuid,
                        vector=chunk.embedding,
                        payload=payload
                    )
                )

            logger.debug(f"Upserting {len(points)} vectors into Qdrant collection '{collection_name}'...")
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            return True
        except Exception as error:
            logger.exception(f"Batch vector upsertion failed for collection '{collection_name}'.")
            return False

    def search_similarity(
        self, 
        collection_name: str, 
        query_vector: List[float], 
        top_k: int = 5, 
        filters: Optional[List[SearchFilter]] = None
    ) -> List[SearchResult]:
        """
        Executes a dense vector similarity search, optionally pre-filtered by metadata.
        """
        try:
            query_filter = None
            
            # Map our platform's abstract SearchFilters into Qdrant match conditions.
            # A sequence value means "any of these" (e.g. restricting a chat turn to a
            # set of document_ids); a scalar means an exact match.
            if filters:
                must_conditions = []
                for f in filters:
                    if isinstance(f.value, (list, tuple, set)):
                        match = qmodels.MatchAny(any=list(f.value))
                    else:
                        match = qmodels.MatchValue(value=f.value)
                    must_conditions.append(
                        qmodels.FieldCondition(key=f.key, match=match)
                    )
                query_filter = qmodels.Filter(must=must_conditions)

            # `client.search()` was removed in qdrant-client 1.x; `query_points` is the
            # supported universal query entrypoint and returns a QueryResponse envelope.
            query_response = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True  # Ensure we retrieve the stored text back
            )

            parsed_results: List[SearchResult] = []
            for hit in query_response.points:
                payload = hit.payload or {}
                
                # Extract reserved fields, defaulting if payload is unexpectedly malformed
                chunk_id = payload.get("chunk_id", str(hit.id))
                text_content = payload.get("text", "")
                
                # Remove reserved system keys from the metadata dict to keep it clean
                clean_metadata = {k: v for k, v in payload.items() if k not in ["chunk_id", "text"]}

                parsed_results.append(
                    SearchResult(
                        chunk_id=chunk_id,
                        text=text_content,
                        score=hit.score,
                        metadata=clean_metadata
                    )
                )

            return parsed_results
            
        except Exception as error:
            logger.exception(f"Semantic search execution failed on Qdrant collection '{collection_name}'.")
            raise RuntimeError(f"Search failure against vector database.") from error

    def list_documents(
        self,
        collection_name: str,
        max_points: int = 10_000,
        payload_keys: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Returns one entry per distinct document held in the collection.

        Documents are not stored as first-class records anywhere: the collection holds
        chunks, each carrying its parent's ``document_id`` and ``filename`` in the
        payload. This scrolls those payloads and folds them into document-level
        summaries.

        Args:
            collection_name: Collection to enumerate.
            payload_keys: Restrict the scroll to these payload fields. When omitted,
                every field except the chunk ``text`` is fetched — text is by far the
                largest field and listing never needs it, so pulling it would mean
                hauling the entire corpus across the wire on every call.
            max_points: Safety bound on how many chunks to scan.

        Returns:
            ``{"documents": [...], "truncated": bool, "scanned_chunks": int}``.
            ``truncated`` is True when the scan hit ``max_points`` with chunks still
            unread, meaning the document list is incomplete — callers must surface that
            rather than presenting a short list as the whole corpus.
            An absent collection yields an empty, untruncated result.
        """
        reserved = {"chunk_id", "text", "chunk_index", "document_id", "filename", "extension", "upload_date"}
        documents: Dict[str, Dict[str, Any]] = {}
        next_offset = None
        scanned = 0

        payload_selector: Any
        if payload_keys:
            payload_selector = qmodels.PayloadSelectorInclude(include=list(payload_keys))
        else:
            payload_selector = qmodels.PayloadSelectorExclude(exclude=["text"])

        try:
            while scanned < max_points:
                points, next_offset = self.client.scroll(
                    collection_name=collection_name,
                    limit=min(256, max_points - scanned),
                    offset=next_offset,
                    with_payload=payload_selector,
                    with_vectors=False,
                )
                if not points:
                    break

                for point in points:
                    payload = point.payload or {}
                    document_id = payload.get("document_id")
                    if not document_id:
                        continue

                    entry = documents.setdefault(
                        document_id,
                        {
                            "document_id": document_id,
                            "filename": payload.get("filename") or "unknown",
                            "extension": payload.get("extension"),
                            "chunk_count": 0,
                            "upload_date": payload.get("upload_date"),
                            "metadata": {},
                        },
                    )
                    entry["chunk_count"] += 1
                    for key, value in payload.items():
                        if key not in reserved:
                            entry["metadata"].setdefault(key, value)

                scanned += len(points)
                if next_offset is None:
                    break

            return {
                "documents": sorted(documents.values(), key=lambda d: str(d["filename"]).lower()),
                "truncated": next_offset is not None,
                "scanned_chunks": scanned,
            }

        except Exception as error:  # noqa: BLE001
            # Nothing ingested yet means no collection, which is an empty list, not a fault.
            if "not found" in str(error).lower() or "doesn't exist" in str(error).lower():
                logger.info("Collection '%s' does not exist yet; reporting no documents.", collection_name)
                return {"documents": [], "truncated": False, "scanned_chunks": 0}
            logger.exception("Failed to enumerate documents in collection '%s'.", collection_name)
            raise RuntimeError("Could not list documents from the vector database.") from error

    def delete_collection(self, collection_name: str) -> bool:
        """
        Drops the collection and permanently removes all contained vector points.
        """
        try:
            logger.info(f"Issuing delete command for Qdrant collection: '{collection_name}'")
            self.client.delete_collection(collection_name=collection_name)
            return True
        except Exception as error:
            logger.error(f"Failed to delete collection '{collection_name}': {str(error)}")
            return False