# Deploying KMRL Document Intelligence

The app is two deployables plus two managed services:

```
Vercel                Container host              Managed
┌──────────────┐      ┌──────────────────┐      ┌──────────────┐
│  frontend/   │─────▶│  FastAPI (this   │─────▶│ Qdrant Cloud │
│  TanStack    │ HTTPS│  repo's root)    │      └──────────────┘
│  Start (SSR) │      │  Dockerfile      │─────▶┌──────────────┐
└──────────────┘      └──────────────────┘      │  LLM API     │
                                                └──────────────┘
```

## Why the backend cannot go on Vercel

Vercel's serverless functions cap out well below what this API needs: it imports torch
and sentence-transformers (hundreds of MB before model weights), loads an embedding
model into memory, and holds a long-lived connection to a vector store. It needs a
container host with persistent memory — Railway, Render, Fly.io, Cloud Run, or any box
that runs Docker. The `Dockerfile` at the repo root builds it.

The frontend, being a normal SSR app, is a perfect fit for Vercel.

## 1. Vector store — Qdrant Cloud

Create a free cluster (1 GB, no card required) at <https://cloud.qdrant.io>. Keep the
cluster URL and API key.

The code talks to Qdrant over host/port, so a cloud URL needs the host without the
scheme and port 6333, plus the key:

```
QDRANT_HOST=xyz-abc.eu-central.aws.cloud.qdrant.io
QDRANT_PORT=6333
QDRANT_API_KEY=<your key>
```

## 2. LLM — any OpenAI-compatible endpoint

Local Ollama is not reachable from a deployed backend, so point the API at a hosted
endpoint instead. Anything OpenAI-compatible works without code changes — Groq's free
tier is a good default, and OpenAI or Azure work identically:

```
LLM_ACTIVE_PROVIDER=openai_compatible
LLM_OPENAI_BASE_URL=https://api.groq.com/openai/v1
LLM_OPENAI_API_KEY=<your key>
LLM_OPENAI_MODEL=llama-3.3-70b-versatile
```

Note the provider value is `openai_compatible`, not `openai` — the settings enum
rejects the latter.

## 3. API — any Docker host

Point the host at this repository (root directory, not `frontend/`) and let it build
from the `Dockerfile`. Set the environment variables from steps 1 and 2, plus:

```
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu
PREWARM=1
```

`PREWARM=1` loads the embedding model and opens the Qdrant connection during startup
rather than on the first request, which turns a slow first search into a slow deploy.

**Size the instance for the model.** MiniLM plus torch needs roughly 1 GB of RAM
resident. A 512 MB free tier will OOM partway through the first embedding call, which
looks like a mysterious 502. Give it at least 1 GB, or 2 GB with headroom.

Once it is up, confirm from your own machine:

```bash
curl https://<your-api-host>/health
curl -F "file=@samples/kmrl_signalling_audit_q2.pdf" https://<your-api-host>/v1/documents/upload
```

The upload is what populates the index — a fresh deployment starts empty, and the UI
will correctly report an empty corpus until you feed it something.

## 4. Frontend — Vercel

The build already emits a Vercel Build Output (`frontend/.vercel/output`), because
`vite.config.ts` pins the nitro preset to `vercel`.

Import the repo at <https://vercel.com/new>, then set:

- **Root Directory**: `frontend`
- **Environment variable**: `VITE_API_URL` = your API's public URL (no trailing slash)

`VITE_API_URL` is read at build time, so changing it needs a redeploy, not just a
restart.

To deploy from this machine instead:

```bash
cd frontend && npx vercel login
npx vercel link            # name the project metro-intel-hub
npx vercel deploy --prebuilt --prod
```

The project name is what assigns `<name>.vercel.app`, so link it as `metro-intel-hub`
to land on that URL.

## 5. Verify the whole path

Open the deployed site and check, in order:

1. **Command Center** reports a document count instead of "backend not reachable".
2. **Upload** a PDF and watch it report the chunk count the server stored.
3. **Search** for something in that document and get a hit with a similarity score.
4. **AI Workspace** answers a question about it and cites the filename.

If step 1 fails with a CORS error, the API's `allow_origins` is `["*"]` by default in
`src/api/main.py` — tighten it to your Vercel domain for production, but that is also
the first thing to check if you have already tightened it.

## Cost note

Qdrant Cloud's free tier and Groq's free tier cover a demo comfortably. The API host is
the only part that reliably costs money, because the memory requirement rules out most
free tiers.
