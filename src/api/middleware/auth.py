from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.logging import RequestTracingMiddleware
from src.api.middleware.error_handlers import setup_exception_handlers
from src.api.routes import upload, search, chat, graph

def create_app() -> FastAPI:
    app = FastAPI(title="KMRL Platform API")

    # 1. Add standard CORS middleware (Essential for frontend communication)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict this in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Add custom request tracing
    app.add_middleware(RequestTracingMiddleware)

    # 3. Setup global error handling
    setup_exception_handlers(app)

    # 4. Include your routers
    app.include_router(upload.router)
    app.include_router(search.router)
    app.include_router(chat.router)
    app.include_router(graph.router)

    return app

app = create_app()