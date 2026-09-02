/**
 * TypeScript mirrors of the backend's Pydantic schemas.
 *
 * Source of truth: `src/api/schemas/{request,response,upload}_schema.py`. Keep these in
 * sync with that module — a field renamed there is a silent `undefined` here.
 */

/** A single matching text fragment inside a document. */
export interface TextSnippetMatch {
  chunk_id: string;
  text: string;
  score: number;
}

/** A grouped, document-level search result. */
export interface SearchDocumentResult {
  document_id: string;
  filename: string;
  aggregate_score: number;
  matches: TextSnippetMatch[];
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  results_count: number;
  documents: SearchDocumentResult[];
}

export interface SearchRequest {
  query: string;
  /** The backend currently implements `semantic` only; other values fall back to it. */
  search_type?: "semantic" | "bm25" | "hybrid" | "graph";
  top_k?: number;
  /** Scalar values match exactly; arrays match any-of. */
  filters?: Record<string, unknown> | null;
  use_reranker?: boolean;
}

/** A document chunk the assistant used to ground an answer. */
export interface CitationSource {
  document_id: string;
  filename: string;
  page_number: string | number | null;
  text_snippet: string;
  similarity_score: number | null;
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface ChatTurnMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ChatRequest {
  session_id: string;
  message: string;
  chat_history: ChatTurnMessage[];
  /** Scopes retrieval to these documents only. */
  document_ids?: string[] | null;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  citations: CitationSource[];
  usage: TokenUsage | null;
}

export interface UploadResponse {
  filename: string;
  document_id: string;
  status: string;
  chunks_created: number;
  metadata_attached: Record<string, unknown> | null;
}

export interface HealthResponse {
  status: string;
  service: string;
}

/**
 * Dashboard telemetry.
 *
 * Storage counts come straight from the vector store and are always real. Metrics that
 * need a request log or a session store the backend does not have are returned as null
 * and named in `unavailable_metrics` with the reason — never invented.
 */
export interface SystemMetrics {
  total_documents: number | null;
  total_chunks?: number | null;
  total_queries_last_24h: number | null;
  avg_latency_ms: number | null;
  active_users: number | null;
  error_rates: Record<string, number> | null;
  unavailable_metrics?: Record<string, string>;
}

/** One indexed document, folded up from the chunks stored for it. */
export interface DocumentSummary {
  document_id: string;
  filename: string;
  extension: string | null;
  chunk_count: number;
  upload_date: string | null;
  metadata: Record<string, unknown>;
}

export interface DocumentListResponse {
  total: number;
  documents: DocumentSummary[];
  /**
   * True when the backend hit its scan bound with chunks still unread: `total` is then
   * a floor, not the size of the corpus, and must not be presented as a full count.
   */
  truncated?: boolean;
}

/** Metadata held for a document. Fields the backend has not stored come back null. */
export interface DocumentMetadata {
  document_id: string;
  title: string | null;
  author: string | null;
  creation_date: string | null;
  keywords: string[];
  custom_attributes: Record<string, unknown>;
  chunk_count?: number | null;
  /** Present when the backend wants to explain what it could and could not provide. */
  note?: string | null;
}

export interface RecommendationItem {
  document_id: string;
  title: string;
  relevance_score: number;
  recommendation_reason: string;
}

export interface RecommendationResponse {
  source_document_id: string;
  recommendations: RecommendationItem[];
  /** Terms the similarity was driven by, when the backend reports them. */
  keywords_used?: string[];
  keyword_source?: string;
}

export interface GraphNode {
  entity_id: string;
  name: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source_id: string;
  target_id: string;
  relation_type: string;
  weight?: number;
}

export interface SubGraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
