import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "motion/react";
import { useMemo, useState } from "react";
import { GlassCard, PageShell, MetroPill } from "@/components/ui-bits";
import { FileText, Sparkles, ArrowLeft, AlertTriangle, Loader2, Send, MessageSquare } from "lucide-react";
import { useChatSession, useDocumentMetadata, useDocuments, useRecommendations } from "@/lib/api/hooks";

export const Route = createFileRoute("/document/$id")({
  head: () => ({ meta: [{ title: "Document — KMRL DocIntel" }, { name: "description", content: "Document detail, metadata and grounded Q&A." }] }),
  component: DocumentDetail,
});

function DocumentDetail() {
  const { id } = Route.useParams();
  const [input, setInput] = useState("");

  const documents = useDocuments();
  const metadata = useDocumentMetadata(id);
  const related = useRecommendations(id);
  // Every turn here is scoped to this document, so answers can only come from it.
  const chat = useChatSession([id]);

  const summary = useMemo(
    () => documents.data?.documents.find((d) => d.document_id === id) ?? null,
    [documents.data, id],
  );

  const notFound = metadata.error?.status === 404 || (documents.isSuccess && !summary);
  const title = summary?.filename ?? metadata.data?.title ?? "Document";

  const send = (text: string) => {
    if (!text.trim() || chat.isThinking) return;
    chat.send(text);
    setInput("");
  };

  if (notFound) {
    return (
      <PageShell title="Document not found">
        <GlassCard>
          <div className="py-12 text-center">
            <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-amber-300" />
            <div className="text-sm font-medium">Nothing indexed under this id</div>
            <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">
              The document <code className="rounded bg-black/30 px-1">{id}</code> is not in the vector store. It may have been removed, or the index rebuilt.
            </p>
            <Link to="/explorer" className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-aurora px-4 py-1.5 text-xs font-medium text-white">
              <ArrowLeft className="h-3.5 w-3.5" /> Back to explorer
            </Link>
          </div>
        </GlassCard>
      </PageShell>
    );
  }

  return (
    <PageShell
      title={title}
      subtitle={summary ? `${summary.chunk_count} indexed passage${summary.chunk_count === 1 ? "" : "s"} · ${summary.extension?.replace(".", "").toUpperCase() ?? "file"}` : undefined}
      action={
        <Link to="/explorer" className="glass flex items-center gap-2 rounded-full px-3 py-1.5 text-xs">
          <ArrowLeft className="h-3.5 w-3.5" /> Explorer
        </Link>
      }
    >
      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-4">
          <GlassCard>
            <h3 className="mb-1 flex items-center gap-2 text-lg font-semibold"><Sparkles className="h-4 w-4 text-accent" /> Ask this document</h3>
            <p className="mb-4 text-xs text-muted-foreground">Retrieval is scoped to this document, so every answer is grounded in it alone.</p>

            <div className="space-y-4">
              {chat.messages.map((m, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                  className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                    m.role === "user" ? "bg-aurora text-white"
                      : m.failed ? "border border-amber-400/30 bg-amber-400/10 text-amber-100"
                      : "border border-white/10 bg-white/[0.04]"
                  }`}>
                    <div className="whitespace-pre-wrap leading-relaxed">{m.content}</div>
                    {m.usage && <div className="mt-2 text-[10px] uppercase tracking-wider text-muted-foreground">{m.usage.total_tokens.toLocaleString()} tokens</div>}
                  </div>
                </motion.div>
              ))}

              {chat.isThinking && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> Reading this document…
                </div>
              )}

              {chat.messages.length === 0 && !chat.isThinking && (
                <div className="flex flex-wrap gap-2">
                  {["Summarise this document.", "What actions does it require, and who owns them?", "What risks does it identify?"].map((q) => (
                    <button key={q} onClick={() => send(q)}
                      className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-muted-foreground transition hover:border-cyan-300/30 hover:text-foreground">
                      ↳ {q}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="glass-strong mt-4 flex items-end gap-2 rounded-2xl p-2">
              <textarea
                value={input} onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
                rows={1} placeholder="Ask about this document…" disabled={chat.isThinking}
                className="max-h-32 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder:text-muted-foreground disabled:opacity-50"
              />
              <button onClick={() => send(input)} disabled={chat.isThinking || !input.trim()}
                className="grid h-9 w-9 place-items-center rounded-xl bg-aurora disabled:opacity-40">
                {chat.isThinking ? <Loader2 className="h-4 w-4 animate-spin text-white" /> : <Send className="h-4 w-4 text-white" />}
              </button>
            </div>
          </GlassCard>
        </div>

        <div className="space-y-4">
          <GlassCard>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold"><FileText className="h-4 w-4" /> Metadata</h3>
            {metadata.isLoading && <div className="flex items-center gap-2 text-xs text-muted-foreground"><Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading…</div>}
            {metadata.isError && metadata.error.status !== 404 && (
              <p className="text-xs text-amber-200">{metadata.error.userMessage}</p>
            )}
            {metadata.data && (
              <dl className="space-y-2 text-xs">
                {[
                  ["Filename", summary?.filename ?? null],
                  ["Title", metadata.data.title],
                  ["Author", metadata.data.author],
                  ["Created", metadata.data.creation_date],
                  ["Indexed", summary?.upload_date ? new Date(summary.upload_date).toLocaleString() : null],
                  ["Chunks", (metadata.data.chunk_count ?? summary?.chunk_count)?.toString() ?? null],
                ].map(([label, value]) => (
                  <div key={label as string} className="flex items-start justify-between gap-3 rounded-xl bg-white/[0.03] px-3 py-2">
                    <dt className="text-muted-foreground">{label}</dt>
                    <dd className={`text-right ${value ? "" : "text-muted-foreground/40"}`}>{value ?? "not recorded"}</dd>
                  </div>
                ))}
                {Object.entries(metadata.data.custom_attributes ?? {}).map(([key, value]) => (
                  <div key={key} className="flex items-start justify-between gap-3 rounded-xl bg-white/[0.03] px-3 py-2">
                    <dt className="text-muted-foreground">{key}</dt>
                    <dd className="text-right">{String(value)}</dd>
                  </div>
                ))}
                {metadata.data.keywords?.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {metadata.data.keywords.map((k) => <span key={k} className="rounded-full bg-white/5 px-2 py-0.5 text-[10px]">{k}</span>)}
                  </div>
                )}
                {metadata.data.note && <p className="pt-1 text-[11px] text-muted-foreground">{metadata.data.note}</p>}
              </dl>
            )}
          </GlassCard>

          <GlassCard>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold"><MessageSquare className="h-4 w-4" /> Related documents</h3>
            {related.isLoading && <div className="flex items-center gap-2 text-xs text-muted-foreground"><Loader2 className="h-3.5 w-3.5 animate-spin" /> Finding related…</div>}
            {related.isError && <p className="text-xs text-amber-200">{related.error.userMessage}</p>}
            {related.data && related.data.recommendations.length === 0 && (
              <p className="text-xs text-muted-foreground">No related documents found in the index.</p>
            )}
            {related.data && related.data.recommendations.length > 0 && (
              <>
                <ul className="space-y-2">
                  {related.data.recommendations.map((r) => (
                    <li key={r.document_id}>
                      <Link to="/document/$id" params={{ id: r.document_id }} className="block rounded-xl bg-white/[0.03] px-3 py-2 hover:bg-white/[0.06]">
                        <div className="truncate text-sm font-medium">{r.title}</div>
                        <div className="mt-0.5 text-[11px] text-muted-foreground">{r.recommendation_reason}</div>
                        <div className="mt-1"><MetroPill color="var(--cyan-glow)">{r.relevance_score.toFixed(3)}</MetroPill></div>
                      </Link>
                    </li>
                  ))}
                </ul>
                {related.data.keywords_used && related.data.keywords_used.length > 0 && (
                  <p className="mt-3 text-[11px] text-muted-foreground">
                    Matched on {related.data.keywords_used.slice(0, 6).join(", ")}
                    {related.data.keyword_source ? ` (${related.data.keyword_source.replace(/_/g, " ")})` : ""}
                  </p>
                )}
              </>
            )}
          </GlassCard>
        </div>
      </div>
    </PageShell>
  );
}
