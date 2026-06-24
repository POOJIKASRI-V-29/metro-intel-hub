import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { useState } from "react";
import { GlassCard, PageShell, MetroPill } from "@/components/ui-bits";
import { LayoutGrid, List, GitBranch, Filter, Star, FileText, FileSpreadsheet, FileImage, FileCog, Sparkles } from "lucide-react";
import { Link } from "@tanstack/react-router";

export const Route = createFileRoute("/explorer")({
  head: () => ({ meta: [{ title: "Document Explorer — KMRL DocIntel" }, { name: "description", content: "Pinterest-style explorer for KMRL documents." }] }),
  component: Explorer,
});

const tags = ["All", "Engineering", "Safety", "Procurement", "Finance", "HR", "Operations", "Legal"];
const smartTags = ["#urgent", "#vendor", "#audit-2026", "#track-3", "#OHE", "#tender", "#incident", "#renewal"];

type Doc = { id: number; title: string; dept: string; type: "pdf" | "xls" | "img" | "cad"; date: string; size: string; risk: "low" | "med" | "high"; tall?: boolean; preview: string };

const icons = { pdf: FileText, xls: FileSpreadsheet, img: FileImage, cad: FileCog };
const colors: Record<string, string> = { Engineering: "var(--cyan-glow)", Safety: "var(--purple-glow)", Procurement: "#ffb84d", Finance: "#7cffb2", Operations: "var(--electric)", HR: "#ff6b9d", Legal: "#a78bfa" };

const docs: Doc[] = [
  { id: 1, title: "Aluva-Pettah Signalling Audit Q2", dept: "Engineering", type: "pdf", date: "Jun 18", size: "4.2MB", risk: "med", tall: true, preview: "Comprehensive audit of the signalling system covering 23 stations…" },
  { id: 2, title: "Vendor Contract — Alstom AMC", dept: "Procurement", type: "pdf", date: "Jun 15", size: "1.8MB", risk: "high", preview: "Annual maintenance contract renewal terms and clauses…" },
  { id: 3, title: "Track-3 Metallurgy Lab Results", dept: "Engineering", type: "xls", date: "Jun 14", size: "640KB", risk: "low", preview: "Spectrometer analysis of rail samples from 14 locations." },
  { id: 4, title: "Coach C-08 Incident Report", dept: "Safety", type: "pdf", date: "Jun 12", size: "2.1MB", risk: "high", tall: true, preview: "Detailed incident timeline, root cause analysis, mitigation steps…" },
  { id: 5, title: "Q2 Tariff Revision Proposal", dept: "Finance", type: "xls", date: "Jun 10", size: "320KB", risk: "low", preview: "Fare modelling with demand elasticity considerations." },
  { id: 6, title: "Edappally Depot CAD Schematics", dept: "Engineering", type: "cad", date: "Jun 09", size: "12.4MB", risk: "low", preview: "Updated electrical layout drawings for the depot." },
  { id: 7, title: "Safety Manual v8.2", dept: "Safety", type: "pdf", date: "Jun 08", size: "8.9MB", risk: "low", tall: true, preview: "Full safety protocol manual covering all metro operations." },
  { id: 8, title: "HR Bulk Recruitment Plan FY26", dept: "HR", type: "pdf", date: "Jun 05", size: "1.1MB", risk: "low", preview: "Hiring forecast across departments for fiscal 2026." },
  { id: 9, title: "Tender — Phase II Civil Works", dept: "Procurement", type: "pdf", date: "Jun 02", size: "5.6MB", risk: "med", preview: "Pre-qualification document for civil contractors." },
  { id: 10, title: "OHE Maintenance Schedule", dept: "Engineering", type: "xls", date: "May 30", size: "420KB", risk: "low", preview: "Overhead equipment quarterly maintenance windows." },
  { id: 11, title: "Legal Opinion — Right of Way", dept: "Legal", type: "pdf", date: "May 28", size: "780KB", risk: "med", tall: true, preview: "Counsel opinion on land acquisition disputes near Kalamassery." },
  { id: 12, title: "Operations Daily Brief", dept: "Operations", type: "pdf", date: "Today", size: "200KB", risk: "low", preview: "Ridership, on-time performance, station-wise footfall." },
];

type View = "grid" | "list" | "timeline";

function Explorer() {
  const [view, setView] = useState<View>("grid");
  const [tag, setTag] = useState("All");
  const filtered = tag === "All" ? docs : docs.filter((d) => d.dept === tag);

  return (
    <PageShell
      title="Document Explorer"
      subtitle="Browse 48,000+ documents intelligently. Search semantically, filter by intent, jump through time."
      action={
        <div className="glass flex items-center gap-1 rounded-full p-1">
          {([["grid", LayoutGrid], ["list", List], ["timeline", GitBranch]] as const).map(([v, Ic]) => (
            <button key={v} onClick={() => setView(v)} className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs capitalize ${view === v ? "bg-aurora text-white" : "text-muted-foreground hover:bg-white/5"}`}>
              <Ic className="h-3.5 w-3.5" />{v}
            </button>
          ))}
        </div>
      }
    >
      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {tags.map((t) => (
          <button key={t} onClick={() => setTag(t)} className={`rounded-full border px-3 py-1.5 text-xs transition ${tag === t ? "border-transparent bg-aurora text-white" : "border-white/10 bg-white/5 text-muted-foreground hover:text-foreground"}`}>{t}</button>
        ))}
        <span className="mx-2 h-4 w-px bg-white/10" />
        <button className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs"><Filter className="h-3 w-3" /> Advanced</button>
        <div className="ml-auto flex flex-wrap gap-1.5">
          {smartTags.map((s) => <span key={s} className="rounded-full bg-white/5 px-2.5 py-1 text-[11px] text-muted-foreground hover:bg-white/10">{s}</span>)}
        </div>
      </div>

      {/* AI suggested + favorites strip */}
      <div className="mb-6 grid gap-4 lg:grid-cols-[2fr_1fr]">
        <GlassCard>
          <div className="mb-3 flex items-center gap-2 text-sm"><Sparkles className="h-4 w-4 text-accent" /> AI suggested for you</div>
          <div className="flex gap-3 overflow-x-auto scroll-thin pb-2">
            {docs.slice(0, 5).map((d) => (
              <Link to="/document/$id" params={{ id: String(d.id) }} key={d.id} className="group min-w-[220px] rounded-2xl border border-white/10 bg-white/[0.03] p-3 transition hover:border-cyan-300/30">
                <MetroPill color={colors[d.dept]}>{d.dept}</MetroPill>
                <div className="mt-2 line-clamp-2 text-sm font-medium">{d.title}</div>
                <div className="mt-1 text-[11px] text-muted-foreground">{d.date} · {d.size}</div>
              </Link>
            ))}
          </div>
        </GlassCard>
        <GlassCard>
          <div className="mb-3 flex items-center gap-2 text-sm"><Star className="h-4 w-4 text-amber-300" /> Favorites & Recent</div>
          <ul className="space-y-2 text-sm">
            {docs.slice(5, 9).map((d) => (
              <li key={d.id} className="flex items-center justify-between rounded-xl bg-white/[0.03] px-3 py-2">
                <span className="truncate">{d.title}</span>
                <span className="text-[11px] text-muted-foreground">{d.date}</span>
              </li>
            ))}
          </ul>
        </GlassCard>
      </div>

      {/* Views */}
      {view === "grid" && (
        <div className="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4">
          {filtered.map((d, i) => {
            const Ic = icons[d.type];
            return (
              <motion.div key={d.id} initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.03 }}
                className="mb-4 break-inside-avoid">
                <Link to="/document/$id" params={{ id: String(d.id) }}>
                  <motion.div whileHover={{ y: -4 }} className="group glass overflow-hidden rounded-2xl">
                    <div className={`relative ${d.tall ? "h-56" : "h-36"} overflow-hidden`} style={{ background: `linear-gradient(135deg, ${colors[d.dept]}33, transparent)` }}>
                      <div className="absolute inset-0 grid-bg opacity-40" />
                      <Ic className="absolute right-4 top-4 h-6 w-6 opacity-60" />
                      <div className="absolute bottom-3 left-3 right-3">
                        <MetroPill color={colors[d.dept]}>{d.dept}</MetroPill>
                      </div>
                    </div>
                    <div className="p-4">
                      <div className="font-medium leading-tight">{d.title}</div>
                      <div className="mt-2 line-clamp-2 text-xs text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">{d.preview}</div>
                      <div className="mt-3 flex flex-wrap gap-1.5 text-[10px] text-muted-foreground">
                        <span className="rounded-full bg-white/5 px-2 py-0.5">{d.type.toUpperCase()}</span>
                        <span className="rounded-full bg-white/5 px-2 py-0.5">{d.size}</span>
                        <span className="rounded-full bg-white/5 px-2 py-0.5">{d.date}</span>
                      </div>
                    </div>
                  </motion.div>
                </Link>
              </motion.div>
            );
          })}
        </div>
      )}

      {view === "list" && (
        <GlassCard className="p-0">
          <div className="grid grid-cols-12 border-b border-white/10 px-5 py-3 text-[10px] uppercase tracking-wider text-muted-foreground">
            <div className="col-span-6">Title</div><div className="col-span-2">Dept</div><div className="col-span-2">Date</div><div className="col-span-1">Size</div><div className="col-span-1">Risk</div>
          </div>
          {filtered.map((d) => (
            <Link to="/document/$id" params={{ id: String(d.id) }} key={d.id} className="grid grid-cols-12 items-center px-5 py-3 text-sm hover:bg-white/5">
              <div className="col-span-6 font-medium">{d.title}</div>
              <div className="col-span-2"><MetroPill color={colors[d.dept]}>{d.dept}</MetroPill></div>
              <div className="col-span-2 text-muted-foreground">{d.date}</div>
              <div className="col-span-1 text-muted-foreground">{d.size}</div>
              <div className="col-span-1"><MetroPill color={d.risk === "high" ? "#ff6b6b" : d.risk === "med" ? "#ffb84d" : "var(--cyan-glow)"}>{d.risk}</MetroPill></div>
            </Link>
          ))}
        </GlassCard>
      )}

      {view === "timeline" && (
        <GlassCard>
          <ol className="relative space-y-6 border-l border-white/10 pl-6">
            {filtered.map((d) => (
              <li key={d.id} className="relative">
                <span className="absolute -left-[27px] mt-2 h-3 w-3 rounded-full" style={{ background: colors[d.dept], boxShadow: `0 0 12px ${colors[d.dept]}` }} />
                <div className="text-xs text-muted-foreground">{d.date}</div>
                <Link to="/document/$id" params={{ id: String(d.id) }} className="block text-base font-medium hover:text-gradient">{d.title}</Link>
                <div className="mt-1 text-xs text-muted-foreground">{d.preview}</div>
              </li>
            ))}
          </ol>
        </GlassCard>
      )}
    </PageShell>
  );
}
