import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { useMemo, useState } from "react";
import { PageShell, GlassCard, MetroPill } from "@/components/ui-bits";
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

export const Route = createFileRoute("/graph")({
  head: () => ({ meta: [{ title: "Knowledge Graph Universe — KMRL DocIntel" }, { name: "description", content: "Interactive knowledge graph of contracts, departments, projects, engineers, vendors and safety." }] }),
  component: GraphPage,
});

type Node = { id: string; label: string; type: "contract" | "dept" | "project" | "engineer" | "vendor" | "safety"; x: number; y: number };
type Edge = [string, string];

const typeColor: Record<Node["type"], string> = {
  contract: "var(--purple-glow)",
  dept: "var(--electric)",
  project: "var(--cyan-glow)",
  engineer: "#7cffb2",
  vendor: "#ffb84d",
  safety: "#ff6b6b",
};

const nodes: Node[] = [
  { id: "d1", label: "Engineering", type: "dept", x: 500, y: 280 },
  { id: "d2", label: "Procurement", type: "dept", x: 220, y: 180 },
  { id: "d3", label: "Safety", type: "dept", x: 760, y: 180 },
  { id: "p1", label: "Track-3 Upgrade", type: "project", x: 380, y: 420 },
  { id: "p2", label: "Phase-II Civil", type: "project", x: 620, y: 420 },
  { id: "p3", label: "OHE Modernization", type: "project", x: 500, y: 540 },
  { id: "c1", label: "AMC #A-2024-31", type: "contract", x: 180, y: 320 },
  { id: "c2", label: "Tender T-2026/04", type: "contract", x: 80, y: 130 },
  { id: "v1", label: "Alstom", type: "vendor", x: 60, y: 240 },
  { id: "v2", label: "Siemens", type: "vendor", x: 880, y: 380 },
  { id: "v3", label: "L&T", type: "vendor", x: 920, y: 240 },
  { id: "e1", label: "R. Menon", type: "engineer", x: 320, y: 100 },
  { id: "e2", label: "S. Pillai", type: "engineer", x: 680, y: 100 },
  { id: "e3", label: "A. Nair", type: "engineer", x: 700, y: 540 },
  { id: "s1", label: "Safety Manual v8.2", type: "safety", x: 860, y: 110 },
  { id: "s2", label: "Incident C-08", type: "safety", x: 920, y: 480 },
];

const edges: Edge[] = [
  ["d1", "p1"], ["d1", "p2"], ["d1", "p3"], ["d1", "e1"], ["d1", "e2"], ["d1", "e3"],
  ["d2", "c1"], ["d2", "c2"], ["d2", "v1"], ["d2", "v3"],
  ["d3", "s1"], ["d3", "s2"],
  ["c1", "v1"], ["c2", "v1"],
  ["p1", "e1"], ["p2", "v3"], ["p3", "v2"],
  ["s2", "p1"], ["s1", "d1"],
];

function GraphPage() {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [hover, setHover] = useState<Node | null>(null);
  const [drag, setDrag] = useState<{ x: number; y: number } | null>(null);

  const nodeMap = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n])), []);

  return (
    <PageShell title="Knowledge Graph Universe" subtitle="Every entity, every relationship — visualized as a living network.">
      <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
        <GlassCard className="relative overflow-hidden p-0">
          <div className="absolute right-3 top-3 z-10 flex gap-1">
            <button onClick={() => setZoom((z) => Math.min(2, z + 0.15))} className="glass grid h-9 w-9 place-items-center rounded-xl"><ZoomIn className="h-4 w-4" /></button>
            <button onClick={() => setZoom((z) => Math.max(0.5, z - 0.15))} className="glass grid h-9 w-9 place-items-center rounded-xl"><ZoomOut className="h-4 w-4" /></button>
            <button onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }} className="glass grid h-9 w-9 place-items-center rounded-xl"><Maximize2 className="h-4 w-4" /></button>
          </div>
          <div
            className="relative h-[640px] cursor-grab active:cursor-grabbing"
            onMouseDown={(e) => setDrag({ x: e.clientX - pan.x, y: e.clientY - pan.y })}
            onMouseUp={() => setDrag(null)}
            onMouseLeave={() => setDrag(null)}
            onMouseMove={(e) => { if (drag) setPan({ x: e.clientX - drag.x, y: e.clientY - drag.y }); }}
          >
            <div className="absolute inset-0 grid-bg opacity-40" />
            <svg viewBox="0 0 1000 640" className="absolute inset-0 h-full w-full" style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: "center" }}>
              <defs>
                <linearGradient id="edge" x1="0" x2="1">
                  <stop offset="0%" stopColor="oklch(0.85 0.16 215)" stopOpacity="0.5" />
                  <stop offset="100%" stopColor="oklch(0.66 0.21 260)" stopOpacity="0.5" />
                </linearGradient>
              </defs>
              {edges.map(([a, b], i) => {
                const A = nodeMap[a], B = nodeMap[b];
                return <motion.line key={i} x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke="url(#edge)" strokeWidth={1.4}
                  initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 1 }} transition={{ duration: 1.2, delay: i * 0.03 }} />;
              })}
              {nodes.map((n, i) => (
                <motion.g key={n.id} initial={{ opacity: 0, scale: 0 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 + i * 0.04, type: "spring", stiffness: 200 }}
                  onMouseEnter={() => setHover(n)} onMouseLeave={() => setHover(null)} style={{ cursor: "pointer" }}>
                  <circle cx={n.x} cy={n.y} r={n.type === "dept" ? 26 : 18} fill={typeColor[n.type]} opacity={0.15} />
                  <circle cx={n.x} cy={n.y} r={n.type === "dept" ? 14 : 9} fill={typeColor[n.type]} style={{ filter: `drop-shadow(0 0 10px ${typeColor[n.type]})` }} />
                  <text x={n.x} y={n.y + (n.type === "dept" ? 38 : 30)} textAnchor="middle" className="fill-foreground" style={{ fontSize: 11, fontWeight: 500 }}>{n.label}</text>
                </motion.g>
              ))}
            </svg>

            {hover && (
              <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                className="glass-strong absolute left-4 bottom-4 max-w-xs rounded-2xl p-4">
                <MetroPill color={typeColor[hover.type]}>{hover.type}</MetroPill>
                <div className="mt-2 text-lg font-semibold">{hover.label}</div>
                <div className="mt-1 text-xs text-muted-foreground">Connected to {edges.filter(([a, b]) => a === hover.id || b === hover.id).length} entities across the network.</div>
              </motion.div>
            )}
          </div>
        </GlassCard>

        <div className="space-y-4">
          <GlassCard>
            <h3 className="mb-3 text-sm font-semibold">Legend</h3>
            <ul className="space-y-2 text-sm">
              {Object.entries(typeColor).map(([k, c]) => (
                <li key={k} className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full" style={{ background: c, boxShadow: `0 0 10px ${c}` }} />
                  <span className="capitalize">{k}</span>
                </li>
              ))}
            </ul>
          </GlassCard>
          <GlassCard>
            <h3 className="mb-3 text-sm font-semibold">Network stats</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-muted-foreground">Nodes</span><span>{nodes.length}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Edges</span><span>{edges.length}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Clusters</span><span>3</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Density</span><span>0.42</span></div>
            </div>
          </GlassCard>
          <GlassCard>
            <h3 className="mb-2 text-sm font-semibold">AI observations</h3>
            <p className="text-xs text-muted-foreground">Alstom is a critical-path vendor — central to 4 active contracts. Loss of this node would impact Engineering and Safety simultaneously.</p>
          </GlassCard>
        </div>
      </div>
    </PageShell>
  );
}
