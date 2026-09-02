# ── KMRL Document Intelligence — API image ──
# CPU-only: the embedding model is small and runs fine without CUDA, and the CPU wheels
# keep the image a few GB smaller than the default ones.

FROM python:3.12-slim

# PIP_RETRIES/PIP_TIMEOUT: the torch wheel is ~155 MB, and a connection dropped partway
# through should retry rather than fail the whole build.
# HF_HOME: keep model weights on a writable path that can be mounted as a volume, so a
# restart does not re-download them.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_RETRIES=10 \
    PIP_TIMEOUT=60 \
    HF_HOME=/models

WORKDIR /app

# Build tools are needed by a few wheels; drop them from the final layer.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Torch first, from the CPU index, so the huge default CUDA build is never pulled.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .

# Excluded from the image:
#  - OCR extras (paddleocr, pytesseract) need native engines and only serve image
#    ingestion; PDF, DOCX and XLSX ingestion never touch them.
#  - chromadb is an alternative vector store reachable only from an orphaned module
#    (src/retrieval/semantic_search.py has no importers), so it is never loaded at
#    runtime — it would add hundreds of MB and a large surface of build failures for
#    code this deployment cannot execute.
#
#    What keeps that safe is that src/embeddings/__init__.py re-exports only the
#    schemas, so nothing eagerly pulls vector_store.py. Adding ChromaVectorStore to
#    that __init__ would break this image at import time rather than at first use —
#    if you do, drop chromadb from the exclusion list below.
#  - torch is installed above from the CPU wheel index.
RUN grep -viE '^\s*(paddleocr|pytesseract|chromadb|torch)\b' requirements.txt > requirements.docker.txt \
    && pip install --no-cache-dir -r requirements.docker.txt

COPY config/ ./config/
COPY src/ ./src/

RUN apt-get purge -y build-essential && apt-get autoremove -y

# Bake the embedding model into the image so the first request is not a cold download.
ARG EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')"

EXPOSE 8000

# Hosts inject the port they want the process to listen on.
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
