import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "motion/react";
import { useState } from "react";
import { PageShell, GlassCard, MetroPill } from "@/components/ui-bits";
import { Search as SearchIcon, Sparkles, Clock, Command, ArrowUpRight, FileText, MessageSquare, Network, Upload } from "lucide-react";

export const Route = createFileRoute("/search")({
  head: () => ({ meta: [{ title: "Spotlight Search — KMRL DocIntel" }, { name: "description", content: "Semantic spotlight search for KMRL documents." }] }),
  component: SearchPage,
});

const semantic = [
  { title: "Aluva–Pettah Signalling Audit Q2", snippet: "…12 intermittent ATP faults traced to firmware mismatch on rev 4.2 OBUs…", score: 0.96, dept: "Engineering", id: 1 },
  { title: "Vendor Contract — Alstom AMC", snippet: "…clause 11.3 governs renewal & continuity obligations…", score: 0.91, dept: "Procurement", id: 2 },
  { title: "Coach C-08 Incident Report", snippet: "…Annex B contains Edappally signalling logs and aspect data…", score: 0.87, dept: "Safety", id: 4 },
  { title: "OHE Maintenance Schedule", snippet: "…Q3 windows for Aluva–Edappally corridor outlined…", score: 0.74, dept: "Engineering", id: 10 },
];

const recent = ["track-3 firmware risk", "AMC renewals next 60 days", "Edappally incidents", "vendor compliance Q2"];
const shortcuts = [
  { k: "⌘ K", v: "Open command palette" },
  { k: "⌘ /", v: "Focus search" },
  { k: "↵", v: "Open result" },
  { k: "⌘ ↵", v: "Open in new tab" },
];

const quick = [
  { icon: FileText, to: "/explorer", label: "Explorer" },
  { icon: MessageSquare, to: "/workspace", label: "Ask AI" },
  { icon: Network, to: "/graph", label: "Graph" },
  { icon: Upload, to: "/upload", label: "Upload" },
];

function SearchPage() {
  const [q, setQ] = useState("signalling firmware risk");
  return (
    <PageShell title="Spotlight" subtitle="Ask in natural language. We search the meaning, not just the words.">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        className="glass-strong mb-6 flex items-center gap-3 rounded-full px-5 py-4">
        <SearchIcon className="h-5 w-5 text-muted-foreground" />
        <input value={q} onChange={(e) => setQ(e.target.value)} autoFocus
          className="flex-1 bg-transparent text-lg outline-none placeholder:text-muted-foreground"
          placeholder="What do you want to know?" />
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
          <GlassCard className="border-cyan-300/30">
            <div className="mb-2 flex items-center gap-2 text-sm"><Sparkles className="h-4 w-4 text-accent" /> AI synthesized answer</div>
            <p className="text-sm leading-relaxed">
              The current signalling firmware risk is concentrated on the <span className="text-gradient font-semibold">Aluva–Pettah corridor</span>, where 12 ATP faults trace to rev 4.2 OBU firmware. A patch (v4.3) is staged but blocked on Alstom's expiring AMC. Recommended path: accelerate the AMC continuity decision, then push firmware over the next maintenance window.
            </p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {semantic.slice(0, 3).map((r, i) => (
                <span key={r.id} className="rounded-full bg-cyan-300/10 px-2 py-1 text-[10px] text-cyan-200 border border-cyan-300/20">{i + 1}. {r.title}</span>
              ))}
            </div>
          </GlassCard>

          <div className="space-y-2">
            {semantic.map((r, i) => (
              <motion.div key={r.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}>
                <Link to="/document/$id" params={{ id: String(r.id) }} className="glass group block rounded-2xl p-4 transition hover:border-cyan-300/30">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        <MetroPill>{r.dept}</MetroPill>
                        <span className="text-[10px] text-muted-foreground">match {Math.round(r.score * 100)}%</span>
                      </div>
                      <div className="font-medium">{r.title}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{r.snippet}</div>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-muted-foreground transition group-hover:text-foreground" />
                  </div>
                  <div className="mt-3 h-1 overflow-hidden rounded-full bg-white/5">
                    <div className="h-full bg-aurora" style={{ width: `${r.score * 100}%` }} />
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <GlassCard>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold"><Clock className="h-4 w-4" /> Search history</h3>
            <ul className="space-y-2 text-sm">
              {recent.map((r) => (
                <li key={r}><button onClick={() => setQ(r)} className="w-full rounded-xl bg-white/[0.03] px-3 py-2 text-left text-sm text-muted-foreground hover:text-foreground">{r}</button></li>
              ))}
            </ul>
          </GlassCard>

          <GlassCard>
            <h3 className="mb-3 text-sm font-semibold">Keyboard shortcuts</h3>
            <ul className="space-y-2 text-sm">
              {shortcuts.map((s) => (
                <li key={s.k} className="flex items-center justify-between rounded-xl bg-white/[0.03] px-3 py-2">
                  <span className="text-muted-foreground">{s.v}</span>
                  <kbd className="rounded-md border border-white/10 bg-black/30 px-2 py-0.5 text-[10px]">{s.k}</kbd>
                </li>
              ))}
            </ul>
          </GlassCard>

          <GlassCard>
            <h3 className="mb-2 text-sm font-semibold">Did you know?</h3>
            <p className="text-xs text-muted-foreground">Spotlight understands natural language — try <em>"contracts expiring this quarter with safety implications"</em>.</p>
          </GlassCard>
        </div>
      </div>
    </PageShell>
  );
}
