import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "motion/react";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { PageShell, GlassCard, MetroPill } from "@/components/ui-bits";
import { Search as SearchIcon, Sparkles, Clock, Command, ArrowUpRight, FileText, MessageSquare, Network, Upload, AlertTriangle, Loader2 } from "lucide-react";
import { useSearch } from "@/lib/api/hooks";
import { api, ApiError, API_BASE_URL } from "@/lib/api/client";
import type { ChatResponse, SearchDocumentResult } from "@/lib/api/types";

export const Route = createFileRoute("/search")({
  head: () => ({ meta: [{ title: "Spotlight Search — KMRL DocIntel" }, { name: "description", content: "Semantic spotlight search for KMRL documents." }] }),
  component: SearchPage,
});

const quick = [
  { icon: FileText, to: "/explorer", label: "Explorer" },
  { icon: MessageSquare, to: "/workspace", label: "Ask AI" },
  { icon: Network, to: "/graph", label: "Graph" },
  { icon: Upload, to: "/upload", label: "Upload" },
];

/** Best snippet for a hit, collapsed to a single readable line. */
function snippetOf(doc: SearchDocumentResult, limit = 220): string {
  const text = doc.matches[0]?.text ?? "";
  const collapsed = text.replace(/\s+/g, " ").trim();
  return collapsed.length > limit ? `${collapsed.slice(0, limit)}…` : collapsed;
}

function departmentOf(doc: SearchDocumentResult): string | null {
  const value = doc.metadata?.department;
  return typeof value === "string" ? value : null;
}

function SearchPage() {
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [history, setHistory] = useState<string[]>([]);

  const results = useSearch(query, { top_k: 10 });

  // Synthesis is a separate, explicit action: it runs a full RAG turn (retrieval plus
  // generation) and takes seconds, so it must not fire on every search.
  const synthesis = useMutation<ChatResponse, ApiError, string>({
    mutationFn: (question: string) =>
      api.chat({
        session_id: `search-${Date.now()}`,
        message: question,
        chat_history: [],
        document_ids: results.data?.documents.map((d) => d.document_id) ?? null,
      }),
  });

  const runSearch = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    setQuery(trimmed);
    synthesis.reset();
    setHistory((prev) => [trimmed, ...prev.filter((q) => q !== trimmed)].slice(0, 6));
  };

  const documents = results.data?.documents ?? [];
  const unreachable = results.error?.isUnreachable;

  return (
    <PageShell title="Spotlight" subtitle="Ask in natural language. We search the meaning, not just the words.">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        className="glass-strong mb-6 flex items-center gap-3 rounded-full px-5 py-4">
        <SearchIcon className="h-5 w-5 text-muted-foreground" />
        <input value={draft} onChange={(e) => setDraft(e.target.value)} autoFocus
          onKeyDown={(e) => { if (e.key === "Enter") runSearch(draft); }}
          className="flex-1 bg-transparent text-lg outline-none placeholder:text-muted-foreground"
          placeholder="What do you want to know?" />
        {results.isFetching && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
        <kbd className="rounded-md border border-white/10 bg-black/30 px-2 py-1 text-[10px] text-muted-foreground flex items-center gap-1"><Command className="h-2.5 w-2.5" />K</kbd>
      </motion.div>

      <div className="mb-6 flex flex-wrap gap-2">
        {quick.map((s) => (
          <Link key={s.label} to={s.to} className="glass flex items-center gap-2 rounded-full px-3 py-1.5 text-xs">
            <s.icon className="h-3.5 w-3.5" /> {s.label}
          </Link>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-3">
          {results.isError && (
            <GlassCard className="border-amber-400/30">
              <div className="flex items-start gap-2 text-sm text-amber-200">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <div className="font-medium">Search unavailable</div>
                  <p className="mt-1 text-xs text-amber-200/80">{results.error.userMessage}</p>
                  {unreachable && (
                    <p className="mt-1 text-xs text-amber-200/60">Tried <code className="rounded bg-black/30 px-1">{API_BASE_URL}</code></p>
                  )}
                </div>
              </div>
            </GlassCard>
          )}

          {!query && !results.isError && (
            <GlassCard className="border-white/10">
              <div className="py-8 text-center">
                <SearchIcon className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
                <div className="text-sm font-medium">Search your indexed documents</div>
                <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
                  Type a question and press Enter. Results are ranked by meaning, not keyword overlap.
                </p>
              </div>
            </GlassCard>
          )}

          {query && !results.isError && documents.length === 0 && !results.isFetching && (
            <GlassCard>
              <div className="py-8 text-center">
                <div className="text-sm font-medium">No matches for “{query}”</div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Nothing in the index is semantically close to that. Try different wording, or upload more documents.
                </p>
                <Link to="/upload" className="mt-4 inline-flex rounded-full bg-aurora px-4 py-1.5 text-xs font-medium text-white">Upload documents</Link>
              </div>
            </GlassCard>
          )}

          {documents.length > 0 && (
            <GlassCard className="border-cyan-300/30">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-sm"><Sparkles className="h-4 w-4 text-accent" /> AI synthesized answer</div>
                {!synthesis.data && (
                  <button onClick={() => synthesis.mutate(query)} disabled={synthesis.isPending}
                    className="rounded-full bg-aurora px-3 py-1 text-[11px] font-medium text-white disabled:opacity-50">
                    {synthesis.isPending ? "Generating…" : "Generate"}
                  </button>
                )}
              </div>

              {synthesis.isPending && (
                <div className="flex items-center gap-2 py-2 text-sm text-muted-foreground">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> Reading the top results and writing an answer…
                </div>
              )}
              {synthesis.isError && (
                <p className="text-xs text-amber-200">{synthesis.error.userMessage}</p>
              )}
              {synthesis.data ? (
                <>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed">{synthesis.data.answer}</p>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {synthesis.data.citations.map((c, i) => (
                      <span key={`${c.document_id}-${i}`} className="rounded-full bg-cyan-300/10 px-2 py-1 text-[10px] text-cyan-200 border border-cyan-300/20">{i + 1}. {c.filename}</span>
                    ))}
                  </div>
                </>
              ) : (
                !synthesis.isPending && !synthesis.isError && (
                  <p className="text-xs text-muted-foreground">
                    Ranked matches are below. Generate an answer to have the AI read the top results and synthesize across them.
                  </p>
                )
              )}
            </GlassCard>
          )}

          <div className="space-y-2">
            {documents.map((doc, i) => (
              <motion.div key={doc.document_id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}>
                <Link to="/document/$id" params={{ id: doc.document_id }} className="glass group block rounded-2xl p-4 transition hover:border-cyan-300/30">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        {departmentOf(doc) && <MetroPill>{departmentOf(doc)}</MetroPill>}
                        <span className="text-[10px] text-muted-foreground">score {doc.aggregate_score.toFixed(3)}</span>
                        <span className="text-[10px] text-muted-foreground">· {doc.matches.length} passage{doc.matches.length === 1 ? "" : "s"}</span>
                      </div>
                      <div className="font-medium">{doc.filename}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{snippetOf(doc)}</div>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-muted-foreground transition group-hover:text-foreground" />
                  </div>
                  <div className="mt-3 h-1 overflow-hidden rounded-full bg-white/5">
                    <div className="h-full bg-aurora" style={{ width: `${Math.min(100, Math.max(4, doc.aggregate_score * 100))}%` }} />
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <GlassCard>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold"><Clock className="h-4 w-4" /> Search history</h3>
            {history.length === 0 ? (
              <p className="text-xs text-muted-foreground">Searches you run in this tab appear here.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {history.map((r) => (
                  <li key={r}><button onClick={() => { setDraft(r); runSearch(r); }} className="w-full rounded-xl bg-white/[0.03] px-3 py-2 text-left text-sm text-muted-foreground hover:text-foreground">{r}</button></li>
                ))}
              </ul>
            )}
          </GlassCard>

          <GlassCard>
            <h3 className="mb-2 text-sm font-semibold">How this search works</h3>
            <p className="text-xs text-muted-foreground">
              Your query is embedded with the same model used to index your documents, then matched by cosine similarity in Qdrant. Scores are similarities, not percentages — 0.4 is a strong match.
            </p>
          </GlassCard>
        </div>
      </div>
    </PageShell>
  );
}
