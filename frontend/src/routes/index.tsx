import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { GlassCard, PageShell, Stat, MetroPill } from "@/components/ui-bits";
import { Sparkles, FileText, Search as SearchIcon, Building2, AlertTriangle, TrendingUp, Plus, Upload, MessageSquare, Network, Calendar, Flame } from "lucide-react";
import { Link } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  head: () => ({ meta: [{ title: "Command Center — KMRL DocIntel" }, { name: "description", content: "AI command center for Kochi Metro document intelligence." }] }),
  component: Dashboard,
});

const departments = [
  { name: "Operations", count: 3120, color: "var(--electric)" },
  { name: "Engineering", count: 2845, color: "var(--cyan-glow)" },
  { name: "Safety", count: 1890, color: "var(--purple-glow)" },
  { name: "Procurement", count: 1432, color: "#ff6b9d" },
  { name: "HR", count: 980, color: "#7cffb2" },
  { name: "Finance", count: 1280, color: "#ffb84d" },
];

const recentUploads = [
  { name: "Aluva–Pettah signalling audit", dept: "Engineering", time: "2m ago", risk: "low" },
  { name: "Q2 vendor compliance — Alstom", dept: "Procurement", time: "18m ago", risk: "medium" },
  { name: "Coach C-08 incident report", dept: "Safety", time: "1h ago", risk: "high" },
  { name: "Tariff revision proposal v3", dept: "Finance", time: "3h ago", risk: "low" },
  { name: "Track-3 metallurgy lab results", dept: "Engineering", time: "5h ago", risk: "low" },
];

const insights = [
  { title: "12 contracts expire within 30 days", body: "Renegotiation window suggested for 4 high-value vendor agreements." },
  { title: "Safety incidents trending up 14%", body: "Cluster detected near Edappally — recommend on-site audit this week." },
  { title: "Duplicate uploads detected", body: "27 near-duplicate engineering drawings consolidated automatically." },
];

const deadlines = [
  { label: "Track-3 inspection sign-off", date: "Jun 24", urgent: true },
  { label: "Alstom signalling AMC renewal", date: "Jun 28", urgent: true },
  { label: "Annual safety audit submission", date: "Jul 02", urgent: false },
  { label: "Vendor compliance report", date: "Jul 10", urgent: false },
];

const keywords = ["track-3", "signalling", "AMC", "incident", "tender-2026", "ridership", "Q2-budget", "Edappally", "OHE", "rolling-stock"];

function Heatmap() {
  return (
    <div className="grid gap-1" style={{ gridTemplateColumns: "repeat(26, minmax(0,1fr))" }}>
      {Array.from({ length: 7 * 26 }).map((_, i) => {
        const v = ((i * 73 + 13) % 100) / 100;
        const op = v < 0.3 ? 0.08 : v < 0.6 ? 0.25 : v < 0.85 ? 0.55 : 0.9;
        return <div key={i} className="aspect-square rounded-[3px]" style={{ background: `oklch(0.66 0.21 260 / ${op})` }} />;
      })}
    </div>
  );
}

function Dashboard() {
  return (
    <PageShell title="Command Center" subtitle="Live intelligence across every document, department and decision at KMRL.">
      {/* Hero AI banner */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        className="glass-strong relative mb-6 overflow-hidden rounded-[2rem] p-8">
        <div className="absolute inset-0 -z-10 opacity-60" style={{ background: "var(--grad-cosmic)" }} />
        <div className="absolute right-6 top-6 flex gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Live · v2.6</span>
        </div>
        <div className="flex items-start gap-4">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-aurora glow-ring">
            <Sparkles className="h-6 w-6 text-white" />
          </div>
          <div className="flex-1">
            <div className="text-[11px] uppercase tracking-[0.25em] text-muted-foreground">Good morning, Commander</div>
            <h2 className="mt-1 text-2xl font-semibold sm:text-3xl">Your network processed <span className="text-gradient">2,847 documents</span> overnight.</h2>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">3 require immediate review · 12 contract renewals queued · AI confidence 96.4%</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to="/workspace" className="rounded-full bg-aurora px-4 py-2 text-sm font-medium text-white">Ask the AI</Link>
              <Link to="/explorer" className="rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm">Explore corpus</Link>
            </div>
          </div>
        </div>
        <div className="metro-line mt-6 h-px w-full" />
      </motion.div>

      {/* Stats */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Total documents" value="48,392" delta="+342 today" accent="var(--electric)" />
        <Stat label="AI searches today" value="1,284" delta="↑ 22% vs yesterday" accent="var(--cyan-glow)" />
        <Stat label="Active departments" value="14" delta="All synced" accent="var(--purple-glow)" />
        <Stat label="Risk alerts" value="7" delta="2 critical" accent="#ff6b6b" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Recent uploads timeline */}
        <GlassCard className="lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold">Recent uploads · Timeline</h3>
            <MetroPill>Auto-classified</MetroPill>
          </div>
          <ol className="relative space-y-4 border-l border-white/10 pl-6">
            {recentUploads.map((u, i) => (
              <motion.li key={u.name} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.06 }}>
                <span className="absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full bg-aurora glow-ring" />
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="font-medium">{u.name}</div>
                    <div className="text-xs text-muted-foreground">{u.dept} · {u.time}</div>
                  </div>
                  <MetroPill color={u.risk === "high" ? "#ff6b6b" : u.risk === "medium" ? "#ffb84d" : "var(--cyan-glow)"}>{u.risk} risk</MetroPill>
                </div>
              </motion.li>
            ))}
          </ol>
        </GlassCard>

        {/* Dept distribution */}
        <GlassCard>
          <h3 className="mb-4 text-lg font-semibold">Department distribution</h3>
          <div className="space-y-3">
            {departments.map((d) => {
              const max = Math.max(...departments.map((x) => x.count));
              const pct = (d.count / max) * 100;
              return (
                <div key={d.name}>
                  <div className="mb-1 flex justify-between text-xs">
                    <span>{d.name}</span>
                    <span className="text-muted-foreground">{d.count.toLocaleString()}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
                    <motion.div initial={{ width: 0 }} whileInView={{ width: `${pct}%` }} viewport={{ once: true }} transition={{ duration: 1, ease: "easeOut" }} className="h-full rounded-full" style={{ background: d.color, boxShadow: `0 0 12px ${d.color}` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </GlassCard>

        {/* AI insights */}
        <GlassCard className="lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold flex items-center gap-2"><Sparkles className="h-4 w-4 text-accent" /> AI Insights</h3>
            <MetroPill color="var(--purple-glow)">Updated 2m ago</MetroPill>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {insights.map((i) => (
              <motion.div key={i.title} whileHover={{ y: -3 }} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <div className="mb-2 text-sm font-semibold text-gradient">{i.title}</div>
                <div className="text-xs text-muted-foreground">{i.body}</div>
              </motion.div>
            ))}
          </div>
        </GlassCard>

        {/* Smart recommendations */}
        <GlassCard>
          <h3 className="mb-4 text-lg font-semibold">Smart recommendations</h3>
          <ul className="space-y-3 text-sm">
            <li className="flex items-start gap-2"><TrendingUp className="mt-0.5 h-4 w-4 text-accent" />Re-index 412 legacy PDFs for semantic search.</li>
            <li className="flex items-start gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 text-amber-400" />Review 3 expiring NDAs before month end.</li>
            <li className="flex items-start gap-2"><Network className="mt-0.5 h-4 w-4 text-cyan-300" />Connect signalling vendor records to incident logs.</li>
          </ul>
        </GlassCard>

        {/* Heatmap */}
        <GlassCard className="lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold flex items-center gap-2"><Flame className="h-4 w-4 text-accent" /> Activity heatmap · 6 months</h3>
            <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
              less <span className="ml-1 h-2 w-2 rounded-sm" style={{ background: "oklch(0.66 0.21 260 / 0.1)" }} />
              <span className="h-2 w-2 rounded-sm" style={{ background: "oklch(0.66 0.21 260 / 0.4)" }} />
              <span className="h-2 w-2 rounded-sm" style={{ background: "oklch(0.66 0.21 260 / 0.7)" }} />
              <span className="h-2 w-2 rounded-sm" style={{ background: "oklch(0.66 0.21 260 / 0.95)" }} /> more
            </div>
          </div>
          <Heatmap />
        </GlassCard>

        {/* Deadlines */}
        <GlassCard>
          <h3 className="mb-4 text-lg font-semibold flex items-center gap-2"><Calendar className="h-4 w-4 text-accent" /> Upcoming deadlines</h3>
          <ul className="space-y-3">
            {deadlines.map((d) => (
              <li key={d.label} className="flex items-center justify-between rounded-xl bg-white/[0.03] p-3">
                <span className="text-sm">{d.label}</span>
                <span className={`text-xs ${d.urgent ? "text-rose-300" : "text-muted-foreground"}`}>{d.date}</span>
              </li>
            ))}
          </ul>
        </GlassCard>

        {/* Trending keywords */}
        <GlassCard className="lg:col-span-3">
          <h3 className="mb-4 text-lg font-semibold">Trending keywords</h3>
          <div className="flex flex-wrap gap-2">
            {keywords.map((k, i) => (
              <motion.span key={k} initial={{ opacity: 0, scale: 0.9 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }} transition={{ delay: i * 0.03 }}
                className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-sm transition hover:border-cyan-300/40 hover:bg-cyan-300/10">
                #{k}
              </motion.span>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* Floating quick actions */}
      <div className="fixed bottom-6 right-6 z-40 flex flex-col gap-3">
        {[
          { icon: Upload, to: "/upload", label: "Upload" },
          { icon: MessageSquare, to: "/workspace", label: "Ask AI" },
          { icon: SearchIcon, to: "/explorer", label: "Explore" },
        ].map((a) => (
          <Link key={a.label} to={a.to} className="group glass-strong flex h-12 w-12 items-center justify-center rounded-full transition hover:w-32 hover:bg-aurora">
            <a.icon className="h-5 w-5" />
            <span className="ml-2 hidden text-xs group-hover:inline">{a.label}</span>
          </Link>
        ))}
        <button className="grid h-14 w-14 place-items-center rounded-full bg-aurora glow-ring">
          <Plus className="h-6 w-6 text-white" />
        </button>
      </div>
    </PageShell>
  );
}
