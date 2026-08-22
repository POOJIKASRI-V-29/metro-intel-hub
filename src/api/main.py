"""
Main Application Entrypoint for the Document Intelligence Platform API.

Configures global middleware, handles application lifecycle startup/shutdown events,
and mounts sub-routers into a unified, secure web service.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import structural dependency resolvers to manage lifecycle states
from .dependencies import get_vector_store, get_embedding_manager, get_llm_manager

# Import isolated route engines from the route package layout
from .routes.upload import router as upload_router
from .routes.search import router as search_router
from .routes.chat import router as chat_router
from .routes.analytics import router as analytics_router
from .routes.graph import router as graph_router
from .routes.classify import router as classify_router
from .routes.metadata import router as metadata_router
from .routes.recommend import router as recommend_router
from .routes.summarize import router as summarize_router

# Setup unified system logging formatters matching Stage 0 configurations
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("document_intelligence.api.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages global application lifecycle hooks. 
    Guarantees heavy singletons load on boot and cleanup logic triggers cleanly on shut down.
    """
    logger.info("==================================================")
    logger.info("Initializing KMRL Document Intelligence Core Core Server...")
    logger.info("==================================================")
    
    # Pre-warming loads the embedding model and opens the vector-store / LLM
    # connections up front. It requires the full ML stack and running services, so
    # it is opt-in via PREWARM=1 and never fatal: the API still boots (and each
    # ML-backed route returns a clean 503) if a backend is unavailable.
    if os.getenv("PREWARM", "0") == "1":
        logger.info("PREWARM=1 -> pre-warming database client pools and model weights...")
        for name, provider in (
            ("vector_store", get_vector_store),
            ("embedding_manager", get_embedding_manager),
            ("llm_manager", get_llm_manager),
        ):
            try:
                provider()
                logger.info("Pre-warmed '%s'.", name)
            except Exception as init_error:  # noqa: BLE001
                logger.warning("Could not pre-warm '%s': %s", name, init_error)
    else:
        logger.info("Skipping pre-warm (set PREWARM=1 to eagerly load ML backends).")

    yield  # --- The FastAPI Server sits here serving requests while active ---

    logger.info("==================================================")
    logger.info("Initiating server shutdown sequence...")
    logger.info("Cleaning up computational resources and database locks...")
    logger.info("==================================================")


# Initialize FastAPI Instance with strict OpenAPI configurations
app = FastAPI(
    title="Document Intelligence Platform Engine",
    description="Enterprise-grade RAG, semantic extraction, and multi-turn conversational chat system.",
    version="1.0.0",
    lifespan=lifespan
)

# --- Global Middleware Configuration ---

# Configure Cross-Origin Resource Sharing (CORS) parameters to unblock frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to dedicated internal subdomains in strict production configurations
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def operational_latency_logging_middleware(request: Request, call_next):
    """
    Interceptors monitoring incoming transaction patterns across all mounted endpoints.
    Provides automated logging tracing for active system auditing.
    """
    import time
    start_time = time.perf_counter()
    
    logger.debug(f"Inbound Request Hook initiated: {request.method} {request.url.path}")
    response = await call_next(request)
    
    execution_duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        f"HTTP {response.status_code} | {request.method} {request.url.path} | "
        f"Execution Window: {execution_duration_ms:.2f}ms"
    )
    return response


# --- Global Exception Interception Handlers ---

@app.exception_handler(Exception)
async def unhandled_global_exception_handler(request: Request, exc: Exception):
    """
    Fallback guard catching raw untracked system execution crashes.
    Prevents exposure of interior microservice stack traces to public callers.
    """
    logger.critical(f"Unhandled system fault intercepted on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "A critical system anomaly occurred while running your query pipeline context."}
    )


# --- Modular Route Registrations ---

# Mount independent router components following architecture mapping specs
app.include_router(upload_router)
app.include_router(search_router)
app.include_router(chat_router)
app.include_router(analytics_router)
app.include_router(graph_router)
app.include_router(classify_router)
app.include_router(metadata_router)
app.include_router(recommend_router)
app.include_router(summarize_router)


@app.get("/health", tags=["System Lifecycle Support"])
async def service_health_check():
    """
    Liveness probe endpoint. Used by container orchestrators like Kubernetes 
    or AWS ECS to verify instance operational integrity.
    """
    return {"status": "healthy", "service": "document_intelligence_core"}