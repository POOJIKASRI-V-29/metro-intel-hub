# KMRL Document Intelligence — AI/ML Backend

A FastAPI service that ingests KMRL documents (PDF/DOCX/XLSX/images), runs OCR,
cleaning, chunking and embedding, stores vectors in Qdrant, and answers questions with a
retrieval-augmented-generation (RAG) chat pipeline. It also exposes classification,
metadata, summarization, recommendation, analytics and knowledge-graph endpoints.

## Architecture

```
config/                 # Pydantic settings, logging, prompt templates
src/
  api/                  # FastAPI app, routes, schemas, middleware, DI (dependencies.py)
  ingestion/            # File loaders + parsers (pdf, docx, excel, image), validation
  ocr/                  # PaddleOCR + Tesseract engines, table extraction
  preprocessing/        # Text cleaner, normalizer, token-aware chunker, dup detection
  embeddings/           # SentenceTransformers manager + schemas
  vector_store/         # Abstract store + Qdrant provider
  retrieval/            # BM25, hybrid (RRF), semantic search, reranker, RAG pipeline
  generation/           # LLM manager wrapping the OpenAI-compatible client
  llm/                  # LLM client, prompts, guardrails, response parsing
  agents/               # Per-concern agents + ingestion workflow orchestrator
  analysis/             # Classifier, summarizer, risk, metadata, recommendations
  knowledge_graph/      # Entity/relationship extraction, graph queries, visualizer
  pipeline/             # Upload / search / chat / indexing / analytics / graph pipelines
  evaluation/           # RAGAS, retrieval & classification metrics, benchmarking
  utils/                # Constants, logging decorators, file/text/embedding helpers
```

Package rooting: `config` and `src` are top-level packages; run the app as
`src.api.main:app` from the repository root.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then edit as needed

uvicorn src.api.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the interactive API, or hit the health probe:

```bash
curl localhost:8000/health
```

### Booting without the full ML stack

Heavy dependencies (torch, sentence-transformers, qdrant-client, openai) and their
backing services are loaded **lazily**. The app boots and `/health` works even if they
are absent or unconfigured; the ML-backed routes then return a clean **503** until their
dependencies and services (Qdrant, an LLM endpoint) are available. Set `PREWARM=1` to
eagerly initialize them on startup instead.

External services expected for full functionality:

- **Qdrant** vector DB — `docker run -p 6333:6333 qdrant/qdrant`
- **An LLM endpoint** — local [Ollama](https://ollama.com) (default) or OpenAI (set `LLM_ACTIVE_PROVIDER=openai` and `LLM_OPENAI_API_KEY`)
- **Tesseract** binary if using the Tesseract OCR engine

## API surface

| Area | Route |
| --- | --- |
| Health | `GET /health` |
| Upload / ingest | `POST /v1/documents/upload` |
| Search | `POST /v1/search` |
| Chat (RAG) | `POST /v1/chat` |
| Analytics | `/analytics/*` |
| Knowledge graph | `/graph/*` |
| Classify | `/classify/*` |
| Metadata | `/metadata/*` |
| Recommend | `/recommend/*` |
| Summarize | `/summarize/*` |

## Configuration

All runtime configuration flows through `config/settings.py` (`get_settings()`), which
reads environment variables (grouped by prefix: `SERVER_`, `LLM_`, `EMBEDDING_`,
`VECTOR_DB_`, `OCR_`, `LOG_`, …) and an optional `.env`. See `.env.example`.

## Status

The ingestion → retrieval → chat happy path and all routers are wired and import
cleanly. End-to-end RAG quality depends on the configured embedding model, a populated
Qdrant collection, and a reachable LLM endpoint. The `src/evaluation/` suite provides
RAGAS and retrieval/classification metrics for measuring answer quality.
