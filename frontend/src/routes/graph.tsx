import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { GlassCard, PageShell, MetroPill } from "@/components/ui-bits";
import { Network, AlertTriangle, Loader2, FileText } from "lucide-react";
import { useDocumentGraph, useDocuments } from "@/lib/api/hooks";

export const Route = createFileRoute("/graph")({
  head: () => ({ meta: [{ title: "Knowledge Graph — KMRL DocIntel" }, { name: "description", content: "Entities and relationships extracted from KMRL documents." }] }),
  component: GraphPage,
});

const typeColors: Record<string, string> = {
  PERSON: "#ff6b9d",
  LOCATION: "var(--cyan-glow)",
  ORGANIZATION: "var(--purple-glow)",
  REGULATION: "#ffb84d",
  EQUIPMENT: "#7cffb2",
};

function colorFor(type: string): string {
  return typeColors[type?.toUpperCase()] ?? "var(--electric)";
}

function GraphPage() {
  const documents = useDocuments();
  const [selected, setSelected] = useState<string>("");

  const docs = useMemo(() => documents.data?.documents ?? [], [documents.data]);
  const activeId = selected || docs[0]?.document_id || "";
  const graph = useDocumentGraph(activeId);

  // Circular layout: enough to read a small neighbourhood without a physics engine.
  const layout = useMemo(() => {
    const nodes = graph.data?.nodes ?? [];
    const radius = 150;
    return nodes.map((node, i) => {
      const angle = (i / Math.max(1, nodes.length)) * Math.PI * 2 - Math.PI / 2;
      return { node, x: 200 + Math.cos(angle) * radius, y: 200 + Math.sin(angle) * radius };
    });
  }, [graph.data]);

  const positionOf = (id: string) => layout.find((entry) => entry.node.entity_id === id);

  return (
    <PageShell
      title="Knowledge Graph"
      subtitle="Entities and relationships extracted from your documents."
    >
      {docs.length > 1 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {docs.map((d) => (
            <button key={d.document_id} onClick={() => setSelected(d.document_id)}
              className={`rounded-full border px-3 py-1.5 text-xs transition ${activeId === d.document_id ? "border-transparent bg-aurora text-white" : "border-white/10 bg-white/5 text-muted-foreground hover:text-foreground"}`}>
              {d.filename}
            </button>
          ))}
        </div>
      )}

      {documents.isSuccess && docs.length === 0 && (
        <GlassCard>
          <div className="py-12 text-center">
            <FileText className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
            <div className="text-sm font-medium">Nothing to graph yet</div>
            <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">Upload documents first — the graph is built from entities extracted out of them.</p>
            <Link to="/upload" className="mt-4 inline-flex rounded-full bg-aurora px-4 py-1.5 text-xs font-medium text-white">Upload documents</Link>
          </div>
        </GlassCard>
      )}

      {activeId && graph.isLoading && (
        <GlassCard>
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Building the graph…
          </div>
        </GlassCard>
      )}

      {graph.isError && (
        <GlassCard className="border-amber-400/30">
          <div className="py-8 text-center">
            <Network className="mx-auto mb-3 h-8 w-8 text-amber-300" />
            <div className="text-sm font-medium text-amber-100">Knowledge graph unavailable</div>
            <p className="mx-auto mt-2 max-w-lg text-xs text-amber-200/80">{graph.error.userMessage}</p>
            <p className="mx-auto mt-3 max-w-lg text-[11px] text-muted-foreground">
              Entity and relationship extraction needs a graph store, which this deployment does not run. Search and the AI workspace are unaffected — they retrieve straight from the vector index.
            </p>
            <div className="mt-4 flex justify-center gap-2">
              <Link to="/search" className="rounded-full bg-aurora px-4 py-1.5 text-xs font-medium text-white">Search instead</Link>
              <Link to="/workspace" className="rounded-full border border-white/15 bg-white/5 px-4 py-1.5 text-xs">Ask the AI</Link>
            </div>
          </div>
        </GlassCard>
      )}

      {graph.data && (
        <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
          <GlassCard className="p-0">
            <div className="border-b border-white/10 px-5 py-3 text-sm font-semibold">
              {graph.data.nodes.length} entit{graph.data.nodes.length === 1 ? "y" : "ies"} · {graph.data.edges.length} relationship{graph.data.edges.length === 1 ? "" : "s"}
            </div>
            {graph.data.nodes.length === 0 ? (
              <p className="px-5 py-16 text-center text-sm text-muted-foreground">No entities were extracted from this document.</p>
            ) : (
              <svg viewBox="0 0 400 400" className="h-[420px] w-full">
                {graph.data.edges.map((edge, i) => {
                  const from = positionOf(edge.source_id);
                  const to = positionOf(edge.target_id);
                  if (!from || !to) return null;
                  return (
                    <g key={i}>
                      <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="rgba(255,255,255,0.15)" strokeWidth={1.5} />
                      <text x={(from.x + to.x) / 2} y={(from.y + to.y) / 2 - 4} fill="rgba(255,255,255,0.45)" fontSize={8} textAnchor="middle">
                        {edge.relation_type?.toLowerCase().replace(/_/g, " ")}
                      </text>
                    </g>
                  );
                })}
                {layout.map(({ node, x, y }) => (
                  <g key={node.entity_id}>
                    <circle cx={x} cy={y} r={9} fill={colorFor(node.type)} opacity={0.9} />
                    <text x={x} y={y + 22} fill="rgba(255,255,255,0.8)" fontSize={9} textAnchor="middle">{node.name}</text>
                  </g>
                ))}
              </svg>
            )}
          </GlassCard>

          <GlassCard>
            <h3 className="mb-3 text-sm font-semibold">Entities</h3>
            {graph.data.nodes.length === 0 ? (
              <p className="text-xs text-muted-foreground">None extracted.</p>
            ) : (
              <ul className="space-y-2">
                {graph.data.nodes.map((node) => (
                  <li key={node.entity_id} className="rounded-xl bg-white/[0.03] px-3 py-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm">{node.name}</span>
                      <MetroPill color={colorFor(node.type)}>{node.type?.toLowerCase()}</MetroPill>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </GlassCard>
        </div>
      )}
    </PageShell>
  );
}
