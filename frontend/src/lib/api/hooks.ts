/**
 * React Query bindings over the API client.
 *
 * Queries are deliberately client-only (no router-loader prefetching): the backend runs
 * outside this app's SSR server and may be unreachable from it, so components render
 * their loading state on the server and fetch once hydrated.
 */

import { useMutation, useQuery, type UseQueryResult } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";

import { api, ApiError } from "./client";
import type {
  ChatResponse,
  CitationSource,
  DocumentListResponse,
  DocumentMetadata,
  RecommendationResponse,
  SubGraphResponse,
  HealthResponse,
  SearchRequest,
  SearchResponse,
  SystemMetrics,
  TokenUsage,
  UploadResponse,
} from "./types";

/** Retry transport hiccups, but never a 503 — that state needs operator action, not spam. */
function retryUnlessUnavailable(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && (error.isServiceUnavailable || error.status === 400)) {
    return false;
  }
  return failureCount < 2;
}

/** Liveness of the backend, polled gently for the connection indicator. */
export function useHealth(): UseQueryResult<HealthResponse, ApiError> {
  return useQuery<HealthResponse, ApiError>({
    queryKey: ["health"],
    queryFn: ({ signal }) => api.health(signal),
    refetchInterval: 30_000,
    retry: retryUnlessUnavailable,
    staleTime: 10_000,
  });
}

/** Semantic search. Disabled until there is a non-empty query to run. */
export function useSearch(
  query: string,
  options: Omit<SearchRequest, "query"> = {},
): UseQueryResult<SearchResponse, ApiError> {
  const { top_k = 10, filters = null, search_type, use_reranker } = options;

  return useQuery<SearchResponse, ApiError>({
    queryKey: ["search", query, top_k, filters, search_type, use_reranker],
    queryFn: ({ signal }) =>
      api.search({ query, top_k, filters, search_type, use_reranker }, signal),
    enabled: query.trim().length > 0,
    retry: retryUnlessUnavailable,
    staleTime: 60_000,
  });
}

/** Everything currently indexed and therefore retrievable. */
export function useDocuments(): UseQueryResult<DocumentListResponse, ApiError> {
  return useQuery<DocumentListResponse, ApiError>({
    queryKey: ["documents"],
    queryFn: ({ signal }) => api.documents(signal),
    retry: retryUnlessUnavailable,
    staleTime: 15_000,
  });
}

/** Stored metadata for one document. 404 means it is not in the index. */
export function useDocumentMetadata(documentId: string): UseQueryResult<DocumentMetadata, ApiError> {
  return useQuery<DocumentMetadata, ApiError>({
    queryKey: ["metadata", documentId],
    queryFn: ({ signal }) => api.metadata(documentId, signal),
    enabled: documentId.length > 0,
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && retryUnlessUnavailable(count, error),
  });
}

/** Documents related to this one. An empty list is a real answer, not a failure. */
export function useRecommendations(documentId: string): UseQueryResult<RecommendationResponse, ApiError> {
  return useQuery<RecommendationResponse, ApiError>({
    queryKey: ["recommendations", documentId],
    queryFn: ({ signal }) => api.recommendations(documentId, signal),
    enabled: documentId.length > 0,
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && retryUnlessUnavailable(count, error),
  });
}

/** Knowledge-graph neighbourhood. 503 when no graph store is wired. */
export function useDocumentGraph(documentId: string): UseQueryResult<SubGraphResponse, ApiError> {
  return useQuery<SubGraphResponse, ApiError>({
    queryKey: ["graph", documentId],
    queryFn: ({ signal }) => api.documentGraph(documentId, signal),
    enabled: documentId.length > 0,
    retry: retryUnlessUnavailable,
  });
}

/** Admin dashboard telemetry. */
export function useAnalytics(): UseQueryResult<SystemMetrics, ApiError> {
  return useQuery<SystemMetrics, ApiError>({
    queryKey: ["analytics"],
    queryFn: ({ signal }) => api.analytics(signal),
    retry: retryUnlessUnavailable,
    staleTime: 30_000,
  });
}

/** One turn in a conversation, as rendered. */
export interface ChatEntry {
  role: "user" | "assistant";
  content: string;
  citations?: CitationSource[];
  usage?: TokenUsage | null;
  /** Set when this turn failed; `content` then holds the user-facing reason. */
  failed?: boolean;
}

export interface ChatSession {
  messages: ChatEntry[];
  send: (message: string) => void;
  reset: () => void;
  isThinking: boolean;
  error: ApiError | null;
  /** Cumulative tokens across the session, or null if the endpoint reported none. */
  totalTokens: number | null;
  /** Citations from the most recent successful answer. */
  lastCitations: CitationSource[];
  sessionId: string;
}

function newSessionId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `session-${Date.now()}`;
}

/**
 * Owns a single RAG conversation: message list, history assembly, and in-flight state.
 *
 * The backend is stateless per turn — it takes the prior messages back on every call —
 * so the transcript lives here rather than on the server.
 */
export function useChatSession(documentIds?: string[]): ChatSession {
  const [sessionId, setSessionId] = useState(newSessionId);
  const [messages, setMessages] = useState<ChatEntry[]>([]);

  const mutation = useMutation<ChatResponse, ApiError, string>({
    mutationFn: (message: string) => {
      // Only completed, successful turns belong in the history sent upstream.
      const history = messages
        .filter((entry) => !entry.failed)
        .map((entry) => ({ role: entry.role, content: entry.content }));

      return api.chat({
        session_id: sessionId,
        message,
        chat_history: history,
        document_ids: documentIds && documentIds.length > 0 ? documentIds : null,
      });
    },
    onSuccess: (response) => {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.answer,
          citations: response.citations,
          usage: response.usage,
        },
      ]);
    },
    onError: (error) => {
      setMessages((current) => [
        ...current,
        { role: "assistant", content: error.userMessage, failed: true },
      ]);
    },
  });

  const { mutate } = mutation;

  const send = useCallback(
    (message: string) => {
      const trimmed = message.trim();
      if (!trimmed) return;
      setMessages((current) => [...current, { role: "user", content: trimmed }]);
      mutate(trimmed);
    },
    [mutate],
  );

  const reset = useCallback(() => {
    setMessages([]);
    setSessionId(newSessionId());
  }, []);

  const totalTokens = useMemo(() => {
    const counted = messages.reduce((sum, entry) => sum + (entry.usage?.total_tokens ?? 0), 0);
    return counted > 0 ? counted : null;
  }, [messages]);

  const lastCitations = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const entry = messages[i];
      if (entry.role === "assistant" && entry.citations?.length) return entry.citations;
    }
    return [];
  }, [messages]);

  return {
    messages,
    send,
    reset,
    isThinking: mutation.isPending,
    error: mutation.error,
    totalTokens,
    lastCitations,
    sessionId,
  };
}

export interface UploadVariables {
  file: File;
  metadata?: Record<string, unknown>;
}

/** Document ingestion, with upload progress surfaced for the drop-zone UI. */
export function useUpload(onProgress?: (percent: number) => void) {
  return useMutation<UploadResponse, ApiError, UploadVariables>({
    mutationFn: ({ file, metadata }) => api.upload(file, metadata, onProgress),
  });
}

export { ApiError } from "./client";
export { API_BASE_URL } from "./client";
