import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { useState } from "react";
import { GlassCard, PageShell, MetroPill } from "@/components/ui-bits";
import { UploadCloud, Check, Loader2, FileText, Eye, Tag, ShieldAlert, Copy } from "lucide-react";

export const Route = createFileRoute("/upload")({
  head: () => ({ meta: [{ title: "Smart Upload Studio — KMRL DocIntel" }, { name: "description", content: "Futuristic AI-powered document upload pipeline." }] }),
  component: UploadPage,
});

const steps = [
  { key: "ocr", label: "OCR extraction", icon: Eye, status: "done" as const },
  { key: "meta", label: "Metadata extraction", icon: Tag, status: "done" as const },
  { key: "sum", label: "AI summary generation", icon: FileText, status: "active" as const },
  { key: "tag", label: "Auto-tagging", icon: Tag, status: "active" as const },
  { key: "dup", label: "Duplicate detection", icon: Copy, status: "pending" as const },
  { key: "risk", label: "Risk detection", icon: ShieldAlert, status: "pending" as const },
];

const files = [
  { name: "Alstom-AMC-2026-renewal.pdf", size: "1.8 MB", risk: "high", tags: ["#vendor", "#renewal", "#legal"], summary: "Renewal of signalling AMC #A-2024-31; expires Jun 28." },
  { name: "Track3-metallurgy-batch7.xlsx", size: "640 KB", risk: "low", tags: ["#engineering", "#track-3"], summary: "Spectrometer results for 14 rail samples." },
  { name: "Coach-C08-incident.docx", size: "920 KB", risk: "high", tags: ["#safety", "#incident"], summary: "Incident timeline and root cause analysis." },
  { name: "Edappally-CAD-layout.dwg", size: "12 MB", risk: "low", tags: ["#cad", "#depot"], summary: "Updated electrical layout drawings." },
];

function UploadPage() {
  const [drag, setDrag] = useState(false);
  return (
    <PageShell title="Smart Upload Studio" subtitle="Drop documents into the pipeline — our AI handles OCR, summarization, tagging and risk detection.">
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-4">
          {/* Upload zone */}
          <motion.div
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); }}
            animate={{ scale: drag ? 1.01 : 1 }}
            className="relative overflow-hidden rounded-[2rem]"
          >
            <div className="glass-strong relative grid place-items-center rounded-[2rem] p-16 text-center">
              <div className="absolute inset-0 -z-10 grid-bg opacity-50" />
              <div className="absolute inset-0 -z-10" style={{ background: "var(--grad-cosmic)" }} />

              <div className="relative mb-6">
                <motion.div animate={{ y: [0, -10, 0] }} transition={{ duration: 3, repeat: Infinity }}
                  className="grid h-28 w-28 place-items-center rounded-full bg-aurora glow-ring">
                  <UploadCloud className="h-12 w-12 text-white" />
                </motion.div>
                <span className="absolute inset-0 rounded-full animate-pulse-ring" />
              </div>

              <h2 className="text-2xl font-semibold sm:text-3xl">Drop files here, or <span className="text-gradient">browse</span></h2>
              <p className="mt-2 max-w-md text-sm text-muted-foreground">PDF · DOCX · XLSX · DWG · Images · Up to 500MB per file. Encrypted at rest.</p>

              <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
                <button className="rounded-full bg-aurora px-5 py-2 text-sm font-medium text-white">Choose files</button>
                <button className="rounded-full border border-white/15 bg-white/5 px-5 py-2 text-sm">Connect SharePoint</button>
                <button className="rounded-full border border-white/15 bg-white/5 px-5 py-2 text-sm">Connect Email</button>
              </div>
            </div>
          </motion.div>

          {/* Pipeline */}
          <GlassCard>
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold">Processing pipeline</h3>
              <MetroPill color="var(--cyan-glow)">4 / 6 stages</MetroPill>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {steps.map((s, i) => (
                <motion.div key={s.key} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.06 }}
                  className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                  <div className={`grid h-9 w-9 place-items-center rounded-xl ${s.status === "done" ? "bg-emerald-500/20 text-emerald-300" : s.status === "active" ? "bg-aurora text-white" : "bg-white/5 text-muted-foreground"}`}>
                    {s.status === "done" ? <Check className="h-4 w-4" /> : s.status === "active" ? <Loader2 className="h-4 w-4 animate-spin" /> : <s.icon className="h-4 w-4" />}
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">{s.label}</div>
                    <div className="mt-1 h-1 overflow-hidden rounded-full bg-white/5">
                      <div className={`h-full ${s.status === "done" ? "w-full bg-emerald-400" : s.status === "active" ? "w-2/3 bg-aurora animate-shimmer" : "w-0"}`} />
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </GlassCard>
        </div>

        {/* Preview cards */}
        <div className="space-y-4">
          <GlassCard>
            <h3 className="mb-3 text-lg font-semibold">Queued files</h3>
            <div className="space-y-3">
              {files.map((f, i) => (
                <motion.div key={f.name} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}
                  className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03]">
                  <div className="flex items-start gap-3 p-3">
                    <div className="grid h-10 w-10 place-items-center rounded-xl bg-aurora"><FileText className="h-5 w-5 text-white" /></div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium">{f.name}</div>
                      <div className="text-[11px] text-muted-foreground">{f.size}</div>
                      <div className="mt-2 text-xs text-muted-foreground">{f.summary}</div>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {f.tags.map((t) => <span key={t} className="rounded-full bg-white/5 px-2 py-0.5 text-[10px]">{t}</span>)}
                        <MetroPill color={f.risk === "high" ? "#ff6b6b" : "var(--cyan-glow)"}>{f.risk} risk</MetroPill>
                      </div>
                    </div>
                  </div>
                  <div className="h-1 overflow-hidden bg-white/5"><div className="h-full bg-aurora animate-shimmer" style={{ width: `${30 + i * 20}%` }} /></div>
                </motion.div>
              ))}
            </div>
          </GlassCard>

          <GlassCard>
            <h3 className="mb-2 text-sm font-semibold">Today's intake</h3>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded-2xl bg-white/[0.03] p-3"><div className="font-display text-2xl font-bold">128</div><div className="text-[10px] text-muted-foreground">Processed</div></div>
              <div className="rounded-2xl bg-white/[0.03] p-3"><div className="font-display text-2xl font-bold">14</div><div className="text-[10px] text-muted-foreground">Duplicates</div></div>
              <div className="rounded-2xl bg-white/[0.03] p-3"><div className="font-display text-2xl font-bold">3</div><div className="text-[10px] text-muted-foreground">High risk</div></div>
            </div>
          </GlassCard>
        </div>
      </div>
    </PageShell>
  );
}
