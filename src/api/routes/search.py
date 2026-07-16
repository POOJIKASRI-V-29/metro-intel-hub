"""
Semantic Search API Route Engine for the KMRL Platform.

Exposes RESTful HTTP endpoints that interface directly with the basic search 
pipelines, enabling secure, fast query execution over raw document vector embeddings.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

# Import the Dependency Injection framework
from ..dependencies import get_search_pipeline

# Import the orchestrator and the centralized enterprise validation schemas
from ...pipeline.search_pipeline import SearchPipeline
from ..schemas.request_schema import SearchRequest, SearchType
from ..schemas.response_schema import SearchResponse, SearchDocumentResult, TextSnippetMatch

logger = logging.getLogger("document_intelligence.api.routes.search")

router = APIRouter(prefix="/v1/search", tags=["Document Retrieval Operations"])


@router.post("", response_model=SearchResponse)
async def execute_document_search(
    request: SearchRequest,
    pipeline: SearchPipeline = Depends(get_search_pipeline)
) -> SearchResponse:
    """
    Executes an atomic document search request. 
    
    Verifies incoming structural parameters, routes search queries to the base 
    vector retrieval indices, and returns highly aligned document hits.
    """
    logger.info(f"Received search dispatch request | Query: '{request.query}' | Mode: {request.search_type}")

    # Guardrail: For the current core baseline, enforce semantic search routing exclusively
    if request.search_type != SearchType.SEMANTIC:
        logger.warning(f"Client requested unsupported search strategy: {request.search_type}. Falling back to baseline SEMANTIC execution.")
        # We process it as semantic to maintain the happy path MVP execution flow without throwing errors
    
    try:
        # Under the hood, we fetch extra text segments to make sure grouping calculations have data
        raw_chunks = pipeline.execute_search(
            query=request.query,
            top_k_chunks=request.top_k * 3,
            filters=request.filters
        )

        # Truncate grouped documents to the exact limit defined by user parameters
        bounded_docs = raw_chunks[:request.top_k]

        # Explicitly map the pipeline's internal results to our strict outbound API response schema
        serialized_documents = []
        for doc in bounded_docs:
            snippet_matches = [
                TextSnippetMatch(
                    chunk_id=match.chunk_id,
                    text=match.text,
                    score=match.score
                )
                for match in doc.matches
            ]

            serialized_documents.append(
                SearchDocumentResult(
                    document_id=doc.document_id,
                    filename=doc.filename,
                    aggregate_score=doc.aggregate_score,
                    matches=snippet_matches,
                    metadata=doc.metadata
                )
            )

        return SearchResponse(
            query=request.query,
            results_count=len(serialized_documents),
            documents=serialized_documents
        )

    except ValueError as val_error:
        logger.warning(f"Param validation variance detected on search endpoint: {str(val_error)}")
        raise HTTPException(status_code=400, detail=str(val_error))
        
    except Exception as general_error:
        logger.exception("Catastrophic runtime processing breakdown on global search vector engine.")
        raise HTTPException(
            status_code=500, 
            detail="The retrieval service encountered an unrecoverable system exception parsing this request."
        )