import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "motion/react";
import { useMemo } from "react";
import { GlassCard, PageShell, Stat, MetroPill } from "@/components/ui-bits";
import { Sparkles, FileText, Search as SearchIcon, Building2, AlertTriangle, Upload, MessageSquare, Network, Loader2 } from "lucide-react";
import { useDocuments, useHealth } from "@/lib/api/hooks";
import { API_BASE_URL } from "@/lib/api/client";
import type { DocumentSummary } from "@/lib/api/types";

export const Route = createFileRoute("/")({
  head: () => ({ meta: [{ title: "Command Center — KMRL DocIntel" }, { name: "description", content: "AI command center for Kochi Metro document intelligence." }] }),
  component: Dashboard,
});

const palette = ["var(--electric)", "var(--cyan-glow)", "var(--purple-glow)", "#ff6b9d", "#7cffb2", "#ffb84d"];

function departmentOf(doc: DocumentSummary): string {
  const value = doc.metadata?.department;
  return typeof value === "string" ? value : "Unattributed";
}

/** Coarse relative time — enough for "when was this ingested" without a date library. */
function relativeTime(iso: string | null): string {
  if (!iso) return "time unknown";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "time unknown";
  const seconds = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function Dashboard() {
  const documents = useDocuments();
  const health = useHealth();

  const docs = useMemo(() => documents.data?.documents ?? [], [documents.data]);
  const totalChunks = docs.reduce((sum, d) => sum + d.chunk_count, 0);

  const departments = useMemo(() => {
    const counts = new Map<string, number>();
    docs.forEach((d) => counts.set(departmentOf(d), (counts.get(departmentOf(d)) ?? 0) + 1));
    return Array.from(counts, ([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .map((entry, i) => ({ ...entry, color: palette[i % palette.length] }));
  }, [docs]);

  const recent = useMemo(
    () => [...docs].sort((a, b) => (b.upload_date ?? "").localeCompare(a.upload_date ?? "")).slice(0, 5),
    [docs],
  );

  const offline = health.isError || documents.error?.isUnreachable;
  // The query has produced an answer, one way or the other.
  const settled = documents.isSuccess || documents.isError;
  const largest = docs.reduce<DocumentSummary | null>((best, d) => (!best || d.chunk_count > best.chunk_count ? d : best), null);

  return (
    <PageShell title="Command Center" subtitle="Everything indexed across the KMRL document network, and what you can ask of it.">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        className="glass-strong relative mb-6 overflow-hidden rounded-[2rem] p-8">
        <div className="absolute inset-0 -z-10 opacity-60" style={{ background: "var(--grad-cosmic)" }} />
        <div className="absolute right-6 top-6 flex items-center gap-1.5">
          <span className={`h-1.5 w-1.5 rounded-full ${offline ? "bg-amber-400" : "bg-emerald-400 animate-pulse"}`} />
          <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">{offline ? "Backend offline" : "Connected"}</span>
        </div>
        <div className="flex items-start gap-4">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-aurora glow-ring">
            <Sparkles className="h-6 w-6 text-white" />
          </div>
          <div className="flex-1">
            <div className="text-[11px] uppercase tracking-[0.25em] text-muted-foreground">KMRL Document Intelligence</div>
            {documents.isLoading ? (
              <h2 className="mt-1 flex items-center gap-2 text-2xl font-semibold sm:text-3xl">
                <Loader2 className="h-5 w-5 animate-spin" /> Reading the index…
              </h2>
            ) : offline ? (
              <>
                <h2 className="mt-1 text-2xl font-semibold sm:text-3xl">The document backend is <span className="text-gradient">not reachable</span>.</h2>
                <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
                  Tried <code className="rounded bg-black/30 px-1">{API_BASE_URL}</code>. Start the API, or point <code className="rounded bg-black/30 px-1">VITE_API_URL</code> at a running instance.
                </p>
              </>
            ) : docs.length === 0 ? (
              <>
                <h2 className="mt-1 text-2xl font-semibold sm:text-3xl">Your index is <span className="text-gradient">empty</span>.</h2>
                <p className="mt-2 max-w-2xl text-sm text-muted-foreground">Upload a document and it becomes searchable, and the AI can answer questions grounded in it.</p>
              </>
            ) : (
              <>
                <h2 className="mt-1 text-2xl font-semibold sm:text-3xl">
                  <span className="text-gradient">{documents.data?.truncated ? "At least " : ""}{docs.length} document{docs.length === 1 ? "" : "s"}</span> indexed and searchable.
                </h2>
                <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
                  {totalChunks} retrievable passage{totalChunks === 1 ? "" : "s"} across {departments.length} department{departments.length === 1 ? "" : "s"}
                  {recent[0]?.upload_date ? ` · most recent ingest ${relativeTime(recent[0].upload_date)}` : ""}
                </p>
              </>
            )}
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to="/workspace" className="rounded-full bg-aurora px-4 py-2 text-sm font-medium text-white">Ask the AI</Link>
              <Link to="/explorer" className="rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm">Explore corpus</Link>
              <Link to="/upload" className="rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm">Upload</Link>
            </div>
          </div>
        </div>
      </motion.div>

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Until the index has actually been read, these are unknown — not zero. The
            server renders this markup before any fetch, so a literal 0 here would show
            every visitor "0 documents indexed" for as long as the request takes. */}
        <Stat label="Documents indexed" value={settled ? docs.length.toLocaleString() : "—"} accent="var(--electric)" />
        <Stat label="Retrievable chunks" value={settled ? totalChunks.toLocaleString() : "—"} accent="var(--cyan-glow)" />
        <Stat label="Departments" value={settled ? departments.length.toLocaleString() : "—"} accent="var(--purple-glow)" />
        <Stat label="Largest document" value={largest ? `${largest.chunk_count} chunks` : "—"} accent="#ffb84d" />
      </div>

      {documents.isError && !offline && (
        <GlassCard className="mb-6 border-amber-400/30">
          <div className="flex items-start gap-2 py-2 text-sm text-amber-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <div className="font-medium">Could not load the index</div>
              <p className="mt-1 text-xs text-amber-200/80">{documents.error.userMessage}</p>
            </div>
          </div>
        </GlassCard>
      )}

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <GlassCard>
          <h3 className="mb-1 flex items-center gap-2 text-lg font-semibold"><FileText className="h-4 w-4" /> Recent ingests</h3>
          <p className="mb-4 text-xs text-muted-foreground">Newest first, by the time the document entered the index.</p>
          {recent.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/10 p-8 text-center">
              <Upload className="mx-auto mb-2 h-5 w-5 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">No documents yet.</p>
              <Link to="/upload" className="mt-3 inline-flex rounded-full bg-aurora px-4 py-1.5 text-xs font-medium text-white">Upload the first one</Link>
            </div>
          ) : (
            <ul className="space-y-2">
              {recent.map((d) => (
                <li key={d.document_id}>
                  <Link to="/document/$id" params={{ id: d.document_id }} className="flex items-center justify-between gap-3 rounded-xl bg-white/[0.03] px-3 py-2.5 hover:bg-white/[0.06]">
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium">{d.filename}</div>
                      <div className="text-[11px] text-muted-foreground">{d.chunk_count} chunk{d.chunk_count === 1 ? "" : "s"}</div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <MetroPill>{departmentOf(d)}</MetroPill>
                      <span className="text-[11px] text-muted-foreground">{relativeTime(d.upload_date)}</span>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </GlassCard>

        <div className="space-y-4">
          <GlassCard>
            <h3 className="mb-1 flex items-center gap-2 text-lg font-semibold"><Building2 className="h-4 w-4" /> By department</h3>
            <p className="mb-4 text-xs text-muted-foreground">From the metadata attached at upload.</p>
            {departments.length === 0 ? (
              <p className="text-xs text-muted-foreground">Nothing indexed yet.</p>
            ) : (
              <ul className="space-y-2.5">
                {departments.map((d) => (
                  <li key={d.name}>
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span>{d.name}</span>
                      <span className="text-muted-foreground">{d.count}</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
                      <div className="h-full rounded-full" style={{ width: `${(d.count / docs.length) * 100}%`, background: d.color }} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </GlassCard>

          <GlassCard>
            <h3 className="mb-3 text-sm font-semibold">Jump to</h3>
            <div className="grid grid-cols-2 gap-2">
              {[
                { to: "/search", icon: SearchIcon, label: "Search" },
                { to: "/workspace", icon: MessageSquare, label: "Ask AI" },
                { to: "/explorer", icon: FileText, label: "Explorer" },
                { to: "/graph", icon: Network, label: "Graph" },
              ].map((item) => (
                <Link key={item.label} to={item.to} className="flex items-center gap-2 rounded-xl bg-white/[0.03] px-3 py-2.5 text-sm hover:bg-white/[0.06]">
                  <item.icon className="h-4 w-4 text-muted-foreground" /> {item.label}
                </Link>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>
    </PageShell>
  );
}
