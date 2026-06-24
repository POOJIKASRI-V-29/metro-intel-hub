import { createFileRoute, Link } from "@tanstack/react-router";
import { PageShell, GlassCard, MetroPill } from "@/components/ui-bits";
import { motion } from "motion/react";
import { FileText, Download, Share2, Star, Sparkles, ListChecks, ShieldAlert } from "lucide-react";

export const Route = createFileRoute("/document/$id")({
  head: ({ params }) => ({ meta: [{ title: `Document #${params.id} — KMRL DocIntel` }, { name: "description", content: "Document detail with AI summary and intelligence." }] }),
  component: DocumentPage,
});

function DocumentPage() {
  const { id } = Route.useParams();
  return (
    <PageShell title="Aluva–Pettah Signalling Audit Q2" subtitle={`Document #${id} · Engineering · 4.2 MB · Updated Jun 18, 2026`}
      action={
        <div className="flex gap-2">
          <button className="glass flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs"><Star className="h-3.5 w-3.5" /> Favorite</button>
          <button className="glass flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs"><Share2 className="h-3.5 w-3.5" /> Share</button>
          <button className="flex items-center gap-1.5 rounded-full bg-aurora px-3 py-1.5 text-xs text-white"><Download className="h-3.5 w-3.5" /> Download</button>
        </div>
      }
    >
      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        {/* Preview */}
        <GlassCard className="p-0">
          <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
            <div className="flex items-center gap-2 text-sm"><FileText className="h-4 w-4" /> Preview</div>
            <div className="flex gap-1.5">
              <MetroPill color="var(--cyan-glow)">PDF</MetroPill>
              <MetroPill color="var(--purple-glow)">v3.1</MetroPill>
            </div>
          </div>
          <div className="relative grid h-[640px] place-items-center overflow-hidden">
            <div className="absolute inset-0 grid-bg opacity-30" />
            <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
              className="relative aspect-[1/1.3] w-[70%] max-w-[460px] rounded-2xl bg-white p-8 text-black shadow-2xl">
              <div className="mb-4 text-[10px] uppercase tracking-widest text-gray-500">KMRL · Engineering Division</div>
              <h2 className="text-xl font-bold leading-tight">Aluva–Pettah Signalling System Audit Report</h2>
              <div className="mt-1 text-xs text-gray-500">Quarter 2 · 2026</div>
              <div className="mt-6 space-y-2">
                {Array.from({ length: 14 }).map((_, i) => <div key={i} className="h-1.5 rounded bg-gray-200" style={{ width: `${60 + (i % 5) * 8}%` }} />)}
              </div>
              <div className="mt-6 grid grid-cols-3 gap-2">
                <div className="h-16 rounded bg-blue-50" />
                <div className="h-16 rounded bg-amber-50" />
                <div className="h-16 rounded bg-emerald-50" />
              </div>
            </motion.div>
          </div>
        </GlassCard>

        <div className="space-y-4">
          <GlassCard>
            <h3 className="mb-2 flex items-center gap-2 text-lg font-semibold"><Sparkles className="h-4 w-4 text-accent" /> AI Summary</h3>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Q2 audit of the Aluva–Pettah signalling corridor identified <span className="text-foreground">12 intermittent ATP faults</span> traced to firmware mismatches on rev 4.2 OBUs, plus <span className="text-foreground">4 monsoon-related aspect anomalies</span> at Edappally. Vendor AMC continuity is the top risk vector. Overall corridor reliability stands at <span className="text-gradient font-semibold">98.7%</span>.
            </p>
          </GlassCard>

          <GlassCard>
            <h3 className="mb-3 flex items-center gap-2 text-lg font-semibold"><ShieldAlert className="h-4 w-4 text-amber-300" /> Risk Score</h3>
            <div className="flex items-center gap-4">
              <div className="relative h-20 w-20">
                <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
                  <circle cx="50" cy="50" r="42" stroke="oklch(1 0 0 / 0.06)" strokeWidth="10" fill="none" />
                  <circle cx="50" cy="50" r="42" stroke="oklch(0.75 0.18 50)" strokeWidth="10" fill="none" strokeDasharray={`${2 * Math.PI * 42 * 0.62} ${2 * Math.PI * 42}`} strokeLinecap="round" />
                </svg>
                <div className="absolute inset-0 grid place-items-center"><span className="font-display text-xl font-bold">62</span></div>
              </div>
              <div>
                <div className="text-sm font-medium">Moderate</div>
                <div className="text-xs text-muted-foreground">Requires review within 7 days</div>
              </div>
            </div>
          </GlassCard>

          <GlassCard>
            <h3 className="mb-3 flex items-center gap-2 text-lg font-semibold"><ListChecks className="h-4 w-4 text-accent" /> AI Action Items</h3>
            <ul className="space-y-2 text-sm">
              {[
                "Schedule joint review with Engineering + Procurement before Jun 25",
                "Initiate AMC continuity dialogue with Alstom (contract A-2024-31)",
                "Deploy firmware patch v4.3 to 38 affected OBUs",
                "Add monsoon-mode telemetry probes at Edappally junction",
              ].map((a, i) => (
                <li key={i} className="flex items-start gap-2 rounded-xl bg-white/[0.03] p-3"><span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-aurora" />{a}</li>
              ))}
            </ul>
          </GlassCard>

          <GlassCard>
            <h3 className="mb-3 text-sm font-semibold">Metadata</h3>
            <dl className="grid grid-cols-2 gap-2 text-xs">
              {[
                ["Author", "R. Menon"], ["Reviewer", "S. Pillai"], ["Department", "Engineering"],
                ["Classification", "Internal"], ["Pages", "42"], ["Language", "English"],
              ].map(([k, v]) => (
                <div key={k} className="rounded-xl bg-white/[0.03] p-3"><dt className="text-[10px] uppercase tracking-wider text-muted-foreground">{k}</dt><dd className="mt-0.5">{v}</dd></div>
              ))}
            </dl>
          </GlassCard>

          <GlassCard>
            <h3 className="mb-2 text-sm font-semibold">Keywords</h3>
            <div className="flex flex-wrap gap-1.5">
              {["signalling", "ATP", "Aluva", "Pettah", "OBU", "firmware", "monsoon", "Edappally", "AMC", "Alstom", "Q2-2026"].map((k) => (
                <span key={k} className="rounded-full bg-white/5 px-2.5 py-1 text-[11px] text-muted-foreground">#{k}</span>
              ))}
            </div>
          </GlassCard>

          <GlassCard>
            <h3 className="mb-3 text-sm font-semibold">Related documents</h3>
            <ul className="space-y-2">
              {[2, 3, 4].map((rid) => (
                <li key={rid}>
                  <Link to="/document/$id" params={{ id: String(rid) }} className="flex items-center justify-between rounded-xl bg-white/[0.03] p-2.5 text-sm hover:bg-white/10">
                    <span>Related document #{rid}</span><span className="text-[11px] text-muted-foreground">96% similar</span>
                  </Link>
                </li>
              ))}
            </ul>
          </GlassCard>

          <GlassCard>
            <h3 className="mb-3 text-sm font-semibold">Timeline</h3>
            <ol className="relative space-y-3 border-l border-white/10 pl-5 text-sm">
              {[
                ["Jun 18", "Audit signed off by S. Pillai"],
                ["Jun 12", "Draft submitted for review"],
                ["Jun 02", "Field inspection completed"],
                ["May 24", "Audit initiated"],
              ].map(([d, t]) => (
                <li key={d} className="relative">
                  <span className="absolute -left-[22px] mt-1.5 h-2.5 w-2.5 rounded-full bg-aurora" />
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{d}</div>
                  <div>{t}</div>
                </li>
              ))}
            </ol>
          </GlassCard>
        </div>
      </div>
    </PageShell>
  );
}
