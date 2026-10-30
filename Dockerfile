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
#  - pytesseract needs the native Tesseract engine and only serves image ingestion; PDF,
#    DOCX and XLSX ingestion never touch it.
#  - torch is installed above from the CPU wheel index.
RUN grep -viE '^\s*(pytesseract|torch)\b' requirements.txt > requirements.docker.txt \
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
