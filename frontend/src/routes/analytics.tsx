import { createFileRoute } from "@tanstack/react-router";
import { useMemo } from "react";
import { GlassCard, PageShell, Stat } from "@/components/ui-bits";
import { BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { AlertTriangle, Loader2, Info } from "lucide-react";
import { useAnalytics, useDocuments } from "@/lib/api/hooks";
import type { DocumentSummary } from "@/lib/api/types";

export const Route = createFileRoute("/analytics")({
  head: () => ({ meta: [{ title: "AI Analytics Center — KMRL DocIntel" }, { name: "description", content: "Corpus composition and system telemetry." }] }),
  component: Analytics,
});

const pieColors = ["oklch(0.66 0.21 260)", "oklch(0.85 0.16 215)", "oklch(0.66 0.23 295)", "#ffb84d", "#7cffb2", "#ff6b9d"];

function departmentOf(doc: DocumentSummary): string {
  const value = doc.metadata?.department;
  return typeof value === "string" ? value : "Unattributed";
}

/** A metric the backend cannot measure, shown as absent rather than guessed. */
function MissingStat({ label, reason }: { label: string; reason?: string }) {
  return (
    <div className="glass relative overflow-hidden rounded-3xl p-5">
      <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">{label}</div>
      <div className="mt-2 font-display text-3xl font-bold text-muted-foreground/40">—</div>
      <div className="mt-1 text-xs text-muted-foreground">{reason ?? "Not tracked by this deployment"}</div>
    </div>
  );
}

function Analytics() {
  const metrics = useAnalytics();
  const documents = useDocuments();

  const docs = useMemo(() => documents.data?.documents ?? [], [documents.data]);

  const byDepartment = useMemo(() => {
    const counts = new Map<string, number>();
    docs.forEach((d) => counts.set(departmentOf(d), (counts.get(departmentOf(d)) ?? 0) + 1));
    return Array.from(counts, ([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);
  }, [docs]);

  const chunksPerDoc = useMemo(
    () =>
      [...docs]
        .sort((a, b) => b.chunk_count - a.chunk_count)
        .slice(0, 10)
        .map((d) => ({ name: d.filename.replace(/\.[^.]+$/, "").slice(0, 22), chunks: d.chunk_count })),
    [docs],
  );

  const totalChunks = docs.reduce((sum, d) => sum + d.chunk_count, 0);
  const unavailable = metrics.data?.unavailable_metrics ?? {};
  const loading = metrics.isLoading || documents.isLoading;

  return (
    <PageShell title="AI Analytics Center" subtitle="What is actually in the index, and what this deployment can and cannot measure.">
      {loading && (
        <GlassCard>
          <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading telemetry…
          </div>
        </GlassCard>
      )}

      {documents.isError && (
        <GlassCard className="border-amber-400/30">
          <div className="flex items-start gap-2 py-4 text-sm text-amber-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <div className="font-medium">Telemetry unavailable</div>
              <p className="mt-1 text-xs text-amber-200/80">{documents.error.userMessage}</p>
            </div>
          </div>
        </GlassCard>
      )}

      {!loading && !documents.isError && (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Documents indexed" value={(metrics.data?.total_documents ?? docs.length).toLocaleString()} accent="var(--electric)" />
            <Stat label="Retrievable chunks" value={(metrics.data?.total_chunks ?? totalChunks).toLocaleString()} accent="var(--cyan-glow)" />
            {metrics.data?.total_queries_last_24h != null
              ? <Stat label="AI queries (24h)" value={metrics.data.total_queries_last_24h.toLocaleString()} accent="var(--purple-glow)" />
              : <MissingStat label="AI queries (24h)" reason={unavailable.total_queries_last_24h} />}
            {metrics.data?.avg_latency_ms != null
              ? <Stat label="Avg. response" value={`${(metrics.data.avg_latency_ms / 1000).toFixed(2)}s`} accent="#ffb84d" />
              : <MissingStat label="Avg. response" reason={unavailable.avg_latency_ms} />}
          </div>

          {Object.keys(unavailable).length > 0 && (
            <GlassCard className="mb-6 border-white/10">
              <div className="flex items-start gap-2">
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                <div className="text-xs text-muted-foreground">
                  <span className="text-foreground">Some metrics are not collected.</span> Storage counts above come from the vector store and are live. Usage metrics need a request log and a session store this deployment does not run, so they are shown as absent rather than estimated.
                </div>
              </div>
            </GlassCard>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            <GlassCard>
              <h3 className="mb-1 text-lg font-semibold">Corpus by department</h3>
              <p className="mb-4 text-xs text-muted-foreground">Documents grouped by the department attached at upload.</p>
              {byDepartment.length === 0 ? (
                <p className="py-12 text-center text-sm text-muted-foreground">Nothing indexed yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie data={byDepartment} dataKey="value" nameKey="name" innerRadius={60} outerRadius={100} paddingAngle={3}>
                      {byDepartment.map((entry, i) => <Cell key={entry.name} fill={pieColors[i % pieColors.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: "rgba(10,12,24,0.92)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              )}
              <div className="mt-2 flex flex-wrap gap-2">
                {byDepartment.map((d, i) => (
                  <span key={d.name} className="flex items-center gap-1.5 rounded-full bg-white/5 px-2.5 py-1 text-[11px]">
                    <span className="h-2 w-2 rounded-full" style={{ background: pieColors[i % pieColors.length] }} />
                    {d.name} · {d.value}
                  </span>
                ))}
              </div>
            </GlassCard>

            <GlassCard>
              <h3 className="mb-1 text-lg font-semibold">Chunks per document</h3>
              <p className="mb-4 text-xs text-muted-foreground">How much retrievable text each document contributes — longer documents yield more chunks.</p>
              {chunksPerDoc.length === 0 ? (
                <p className="py-12 text-center text-sm text-muted-foreground">Nothing indexed yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={chunksPerDoc} layout="vertical" margin={{ left: 8, right: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis type="number" stroke="rgba(255,255,255,0.4)" fontSize={11} allowDecimals={false} />
                    <YAxis type="category" dataKey="name" stroke="rgba(255,255,255,0.4)" fontSize={10} width={140} />
                    <Tooltip contentStyle={{ background: "rgba(10,12,24,0.92)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12 }} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                    <Bar dataKey="chunks" fill="oklch(0.66 0.21 260)" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </GlassCard>
          </div>
        </>
      )}
    </PageShell>
  );
}
