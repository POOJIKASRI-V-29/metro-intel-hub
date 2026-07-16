"""
Main Application Entrypoint for the Document Intelligence Platform API.

Configures global middleware, handles application lifecycle startup/shutdown events,
and mounts sub-routers into a unified, secure web service.
"""

import logging
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
    
    try:
        # Pre-warm heavy resources immediately on startup to catch configurations flaws early
        logger.info("Pre-warming Database client pools and model weights...")
        v_store = get_vector_store()
        embedder = get_embedding_manager()
        llm = get_llm_manager()
        
        logger.info("All heavy connections and ML models verified successfully.")
    except Exception as init_error:
        logger.critical(f"Critical System Initialization Failure during bootstrap sequence: {str(init_error)}")
        # Raise to halt the server process from running in a zombie state
        raise init_error

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


@app.get("/health", tags=["System Lifecycle Support"])
async def service_health_check():
    """
    Liveness probe endpoint. Used by container orchestrators like Kubernetes 
    or AWS ECS to verify instance operational integrity.
    """
    return {"status": "healthy", "service": "document_intelligence_core"}