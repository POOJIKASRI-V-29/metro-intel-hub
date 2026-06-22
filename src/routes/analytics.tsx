import { createFileRoute } from "@tanstack/react-router";
import { GlassCard, PageShell, MetroPill, Stat } from "@/components/ui-bits";
import { LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { Sparkles } from "lucide-react";

export const Route = createFileRoute("/analytics")({
  head: () => ({ meta: [{ title: "AI Analytics Center — KMRL DocIntel" }, { name: "description", content: "Document, search, and AI usage analytics." }] }),
  component: Analytics,
});

const trends = Array.from({ length: 14 }).map((_, i) => ({
  day: `D${i + 1}`,
  docs: 200 + Math.round(Math.sin(i / 2) * 60 + i * 12),
  searches: 120 + Math.round(Math.cos(i / 3) * 40 + i * 8),
}));

const depUsage = [
  { name: "Engineering", value: 3120 },
  { name: "Safety", value: 1890 },
  { name: "Procurement", value: 1432 },
  { name: "Finance", value: 1280 },
  { name: "Operations", value: 3020 },
  { name: "HR", value: 980 },
];

const queries = [
  { name: "Semantic", value: 48 },
  { name: "Keyword", value: 22 },
  { name: "Filter", value: 18 },
  { name: "Voice", value: 12 },
];

const pieColors = ["oklch(0.66 0.21 260)", "oklch(0.85 0.16 215)", "oklch(0.66 0.23 295)", "#ffb84d"];

const top = [
  { name: "Safety Manual v8.2", views: 1840 },
  { name: "Alstom AMC contract", views: 1320 },
  { name: "Track-3 audit report", views: 1098 },
  { name: "Operations daily brief", views: 940 },
  { name: "Tender T-2026/04", views: 712 },
];

function Heat() {
  return (
    <div className="grid gap-1" style={{ gridTemplateColumns: "repeat(24, minmax(0,1fr))" }}>
      {Array.from({ length: 7 * 24 }).map((_, i) => {
        const v = ((i * 53 + 7) % 100) / 100;
        return <div key={i} className="aspect-square rounded-sm" style={{ background: `oklch(0.85 0.16 215 / ${0.08 + v * 0.7})` }} />;
      })}
    </div>
  );
}

function Analytics() {
  return (
    <PageShell title="AI Analytics Center" subtitle="Pulse of the document network — trends, performance and AI quality, in real time.">
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Documents indexed" value="48,392" delta="+2.4% this week" accent="var(--electric)" />
        <Stat label="AI queries" value="18,204" delta="↑ 31%" accent="var(--cyan-glow)" />
        <Stat label="Avg. response" value="1.42s" delta="−18%" accent="var(--purple-glow)" />
        <Stat label="AI performance" value="96.4" delta="A+ grade" accent="#7cffb2" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <GlassCard className="lg:col-span-2">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-lg font-semibold">Document & search trends</h3>
            <MetroPill>Last 14 days</MetroPill>
          </div>
          <div className="h-64">
            <ResponsiveContainer>
              <AreaChart data={trends}>
                <defs>
                  <linearGradient id="g1" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="oklch(0.66 0.21 260)" stopOpacity={0.6} /><stop offset="100%" stopColor="oklch(0.66 0.21 260)" stopOpacity={0} /></linearGradient>
                  <linearGradient id="g2" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="oklch(0.85 0.16 215)" stopOpacity={0.6} /><stop offset="100%" stopColor="oklch(0.85 0.16 215)" stopOpacity={0} /></linearGradient>
                </defs>
                <CartesianGrid stroke="oklch(1 0 0 / 0.05)" />
                <XAxis dataKey="day" stroke="oklch(1 0 0 / 0.3)" fontSize={11} />
                <YAxis stroke="oklch(1 0 0 / 0.3)" fontSize={11} />
                <Tooltip contentStyle={{ background: "oklch(0.18 0.04 265 / 0.95)", border: "1px solid oklch(1 0 0 / 0.1)", borderRadius: 12 }} />
                <Area type="monotone" dataKey="docs" stroke="oklch(0.66 0.21 260)" fill="url(#g1)" strokeWidth={2} />
                <Area type="monotone" dataKey="searches" stroke="oklch(0.85 0.16 215)" fill="url(#g2)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>

        <GlassCard>
          <h3 className="mb-2 text-lg font-semibold">Query types</h3>
          <div className="h-64">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={queries} dataKey="value" innerRadius={50} outerRadius={80} paddingAngle={4}>
                  {queries.map((_, i) => <Cell key={i} fill={pieColors[i]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "oklch(0.18 0.04 265 / 0.95)", border: "1px solid oklch(1 0 0 / 0.1)", borderRadius: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
            {queries.map((q, i) => (
              <div key={q.name} className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: pieColors[i] }} />{q.name} · {q.value}%</div>
            ))}
          </div>
        </GlassCard>

        <GlassCard className="lg:col-span-2">
          <h3 className="mb-2 text-lg font-semibold">Department usage</h3>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={depUsage}>
                <CartesianGrid stroke="oklch(1 0 0 / 0.05)" />
                <XAxis dataKey="name" stroke="oklch(1 0 0 / 0.3)" fontSize={11} />
                <YAxis stroke="oklch(1 0 0 / 0.3)" fontSize={11} />
                <Tooltip contentStyle={{ background: "oklch(0.18 0.04 265 / 0.95)", border: "1px solid oklch(1 0 0 / 0.1)", borderRadius: 12 }} />
                <Bar dataKey="value" radius={[8, 8, 0, 0]} fill="oklch(0.66 0.21 260)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>

        <GlassCard>
          <h3 className="mb-2 text-lg font-semibold flex items-center gap-2"><Sparkles className="h-4 w-4 text-accent" /> AI performance</h3>
          <div className="grid place-items-center py-4">
            <div className="relative h-40 w-40">
              <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
                <circle cx="50" cy="50" r="42" stroke="oklch(1 0 0 / 0.06)" strokeWidth="8" fill="none" />
                <circle cx="50" cy="50" r="42" stroke="url(#perf)" strokeWidth="8" fill="none" strokeDasharray={`${2 * Math.PI * 42 * 0.964} ${2 * Math.PI * 42}`} strokeLinecap="round" />
                <defs>
                  <linearGradient id="perf"><stop offset="0%" stopColor="oklch(0.85 0.16 215)" /><stop offset="100%" stopColor="oklch(0.66 0.23 295)" /></linearGradient>
                </defs>
              </svg>
              <div className="absolute inset-0 grid place-items-center">
                <div className="text-center"><div className="font-display text-3xl font-bold">96.4</div><div className="text-[10px] text-muted-foreground">Confidence</div></div>
              </div>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="lg:col-span-2">
          <h3 className="mb-3 text-lg font-semibold">Activity heatmap · last 7 days</h3>
          <Heat />
          <div className="mt-3 grid grid-cols-7 gap-1 text-center text-[10px] text-muted-foreground">
            {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => <div key={d}>{d}</div>)}
          </div>
        </GlassCard>

        <GlassCard>
          <h3 className="mb-3 text-lg font-semibold">Top accessed documents</h3>
          <ul className="space-y-3">
            {top.map((t, i) => (
              <li key={t.name}>
                <div className="mb-1 flex items-center justify-between text-sm"><span>{i + 1}. {t.name}</span><span className="text-muted-foreground text-xs">{t.views}</span></div>
                <div className="h-1.5 overflow-hidden rounded-full bg-white/5"><div className="h-full bg-aurora" style={{ width: `${(t.views / top[0].views) * 100}%` }} /></div>
              </li>
            ))}
          </ul>
        </GlassCard>

        <GlassCard className="lg:col-span-3">
          <h3 className="mb-2 text-lg font-semibold">Search trends</h3>
          <div className="h-56">
            <ResponsiveContainer>
              <LineChart data={trends}>
                <CartesianGrid stroke="oklch(1 0 0 / 0.05)" />
                <XAxis dataKey="day" stroke="oklch(1 0 0 / 0.3)" fontSize={11} />
                <YAxis stroke="oklch(1 0 0 / 0.3)" fontSize={11} />
                <Tooltip contentStyle={{ background: "oklch(0.18 0.04 265 / 0.95)", border: "1px solid oklch(1 0 0 / 0.1)", borderRadius: 12 }} />
                <Line type="monotone" dataKey="searches" stroke="oklch(0.85 0.16 215)" strokeWidth={2.5} dot={{ r: 3, fill: "oklch(0.85 0.16 215)" }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>
      </div>
    </PageShell>
  );
}
