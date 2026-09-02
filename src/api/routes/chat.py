"""
Conversational RAG Chat API Route Engine for the KMRL Platform.

Exposes endpoints for multi-turn chat interactions over ingested enterprise data,
integrating context retrieval, conversational memory parsing, and LLM text generation.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import TYPE_CHECKING

# Import dependency framework
from ..dependencies import get_chat_pipeline

# Import strict validation schemas. The concrete chat pipeline pulls the heavy ML stack,
# so its type is imported only for type-checking and its runtime message type is imported
# lazily inside the handler.
from ..schemas.request_schema import ChatRequest
from ..schemas.response_schema import ChatResponse, CitationSource, TokenUsage

if TYPE_CHECKING:
    from ...pipeline.chat_pipeline import ChatPipeline

logger = logging.getLogger("document_intelligence.api.routes.chat")

router = APIRouter(prefix="/v1/chat", tags=["Conversational RAG Operations"])


@router.post("", response_model=ChatResponse)
async def execute_rag_chat_turn(
    request: ChatRequest,
    pipeline: "ChatPipeline" = Depends(get_chat_pipeline)
) -> ChatResponse:
    """
    Processes a conversation turn by fetching contextual document snippets, 
    injecting chat histories, and synthesizing answers with clear references.
    """
    logger.info(
        f"Processing RAG chat interaction | Session ID: {request.session_id} | "
        f"History Depth: {len(request.chat_history)} messages"
    )

    try:
        # Imported lazily so this module stays importable without the heavy ML stack.
        from ...pipeline.chat_pipeline import ChatMessage as PipelineChatMessage

        # Step 1: Map the inbound schema chat history objects to internal pipeline message items
        mapped_history = [
            PipelineChatMessage(role=msg.role, content=msg.content)
            for msg in request.chat_history
        ]

        # Step 2: Configure scoping filter overrides if explicit document restrictions are declared
        execution_filters = request.document_ids or None
        filters_dict = None
        if execution_filters:
            # Scope the search to the requested documents. A list value is an any-of match
            # in the vector-store filter contract; a Mongo-style {"$in": [...]} operator
            # dict is not something the store's exact-match mapping can consume.
            filters_dict = {"document_id": execution_filters}

        # Step 3: Trigger the conversational pipeline processing turn
        pipeline_output = pipeline.execute_chat_turn(
            current_query=request.message,
            chat_history=mapped_history,
            filters=filters_dict
        )

        # Step 4: Serialize the internal generated text and reference structures into response schemas
        serialized_citations = [
            CitationSource(
                document_id=chunk.metadata.get("document_id", "unknown_id"),
                filename=chunk.metadata.get("filename", "unknown_source"),
                page_number=chunk.metadata.get("page_label"),
                text_snippet=chunk.text,
                similarity_score=getattr(chunk, "score", None)
            )
            for chunk in pipeline_output.context_chunks
        ]

        # Step 5: Format token telemetry parameters if returned by the generation engine
        usage_telemetry = None
        if pipeline_output.metadata and "token_usage" in pipeline_output.metadata:
            usage_data = pipeline_output.metadata["token_usage"]
            usage_telemetry = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0)
            )

        return ChatResponse(
            session_id=request.session_id,
            answer=pipeline_output.answer,
            citations=serialized_citations,
            usage=usage_telemetry
        )

    except ValueError as format_err:
        logger.warning(f"Validation failure intercepted on chat channel execution: {str(format_err)}")
        raise HTTPException(status_code=400, detail=str(format_err))

    except Exception as runtime_err:
        logger.exception(f"Internal generation loop crash during active chat session processing: {request.session_id}")
        raise HTTPException(
            status_code=500,
            detail="The chat controller experienced an internal generation anomaly while synthesizing the response."
        )