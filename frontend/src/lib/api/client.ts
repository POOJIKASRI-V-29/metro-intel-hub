/**
 * HTTP client for the KMRL Document Intelligence backend.
 *
 * The backend is a separate FastAPI service (see the repository root), not part of this
 * app's SSR server, so its origin is configured at build time via `VITE_API_URL` and
 * every call is a plain cross-origin fetch. The backend sets permissive CORS.
 */

import type {
  ChatRequest,
  ChatResponse,
  DocumentListResponse,
  DocumentMetadata,
  HealthResponse,
  RecommendationResponse,
  SubGraphResponse,
  SearchRequest,
  SearchResponse,
  SystemMetrics,
  UploadResponse,
} from "./types";

/** Where the API lives. Override per environment with `VITE_API_URL`. */
export const API_BASE_URL: string = (import.meta.env.VITE_API_URL ?? "http://localhost:8000")
  .toString()
  .replace(/\/+$/, "");

/**
 * A failed API call, carrying enough detail for the UI to say something specific.
 *
 * `status === 0` means the request never reached the server (wrong URL, server down,
 * CORS refusal); `status === 503` means the server is up but a backend it depends on
 * (Qdrant, the LLM endpoint) is not — the two need different messages on screen.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string | null;

  constructor(message: string, status: number, detail: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }

  /** The API could not be reached at all. */
  get isUnreachable(): boolean {
    return this.status === 0;
  }

  /** The API is up but an AI backend it needs is unavailable. */
  get isServiceUnavailable(): boolean {
    return this.status === 503;
  }

  /** A short, human-facing explanation suitable for rendering directly. */
  get userMessage(): string {
    if (this.isUnreachable) {
      return `Cannot reach the API at ${API_BASE_URL}. Is the backend running?`;
    }
    if (this.isServiceUnavailable) {
      return this.detail ?? "An AI backend is unavailable. Check Qdrant and the LLM endpoint.";
    }
    return this.detail ?? this.message;
  }
}

/** Pulls FastAPI's `{"detail": ...}` out of an error body, whatever shape it took. */
async function extractDetail(response: Response): Promise<string | null> {
  try {
    const body = await response.json();
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (detail != null) return JSON.stringify(detail);
    return null;
  } catch {
    return null;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch (cause) {
    // fetch() rejects only on transport failure — DNS, refused connection, blocked CORS.
    throw new ApiError(
      `Network request to ${API_BASE_URL}${path} failed`,
      0,
      cause instanceof Error ? cause.message : null,
    );
  }

  if (!response.ok) {
    throw new ApiError(
      `${init.method ?? "GET"} ${path} failed with ${response.status}`,
      response.status,
      await extractDetail(response),
    );
  }

  return (await response.json()) as T;
}

function postJson<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}

export const api = {
  health(signal?: AbortSignal): Promise<HealthResponse> {
    return request<HealthResponse>("/health", { signal });
  },

  documents(signal?: AbortSignal): Promise<DocumentListResponse> {
    return request<DocumentListResponse>("/v1/documents", { signal });
  },

  metadata(documentId: string, signal?: AbortSignal): Promise<DocumentMetadata> {
    return request<DocumentMetadata>(`/metadata/${encodeURIComponent(documentId)}`, { signal });
  },

  recommendations(documentId: string, signal?: AbortSignal): Promise<RecommendationResponse> {
    return request<RecommendationResponse>(`/recommend/${encodeURIComponent(documentId)}`, { signal });
  },

  documentGraph(documentId: string, signal?: AbortSignal): Promise<SubGraphResponse> {
    return request<SubGraphResponse>(`/graph/document/${encodeURIComponent(documentId)}`, { signal });
  },

  search(payload: SearchRequest, signal?: AbortSignal): Promise<SearchResponse> {
    return postJson<SearchResponse>("/v1/search", payload, signal);
  },

  chat(payload: ChatRequest, signal?: AbortSignal): Promise<ChatResponse> {
    return postJson<ChatResponse>("/v1/chat", payload, signal);
  },

  analytics(signal?: AbortSignal): Promise<SystemMetrics> {
    return request<SystemMetrics>("/analytics/dashboard", { signal });
  },

  /**
   * Uploads a document for ingestion.
   *
   * Uses XMLHttpRequest rather than fetch because the upload UI reports progress, and
   * fetch exposes no upload-progress events.
   */
  upload(
    file: File,
    metadata?: Record<string, unknown>,
    onProgress?: (percent: number) => void,
  ): Promise<UploadResponse> {
    return new Promise((resolve, reject) => {
      const form = new FormData();
      form.append("file", file);
      if (metadata && Object.keys(metadata).length > 0) {
        form.append("metadata", JSON.stringify(metadata));
      }

      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE_URL}/v1/documents/upload`);

      xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable && onProgress) {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      });

      xhr.addEventListener("load", () => {
        let parsed: unknown = null;
        try {
          parsed = JSON.parse(xhr.responseText);
        } catch {
          // fall through to the status check below
        }

        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(parsed as UploadResponse);
          return;
        }

        const detail = (parsed as { detail?: unknown } | null)?.detail;
        reject(
          new ApiError(
            `Upload failed with ${xhr.status}`,
            xhr.status,
            typeof detail === "string" ? detail : detail != null ? JSON.stringify(detail) : null,
          ),
        );
      });

      xhr.addEventListener("error", () => {
        reject(new ApiError(`Upload to ${API_BASE_URL} failed`, 0));
      });

      xhr.addEventListener("abort", () => {
        reject(new ApiError("Upload was cancelled", 0));
      });

      xhr.send(form);
    });
  },
};
