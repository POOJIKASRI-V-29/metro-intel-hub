import { useNavigate } from "@tanstack/react-router";
import { AnimatePresence, motion } from "motion/react";
import { Search, ArrowRight, Sparkles, FileText, Network, Upload, BarChart3, MessageSquare, Compass, Clock } from "lucide-react";
import { useState } from "react";

const suggestions = [
  { icon: FileText, label: "Open Document Explorer", to: "/explorer", hint: "Browse" },
  { icon: MessageSquare, label: "Ask AI Workspace", to: "/workspace", hint: "Chat" },
  { icon: Upload, label: "Upload new documents", to: "/upload", hint: "Studio" },
  { icon: Network, label: "Knowledge Graph Universe", to: "/graph", hint: "Visualize" },
  { icon: BarChart3, label: "Open Analytics Center", to: "/analytics", hint: "Insights" },
  { icon: Compass, label: "Command Center Dashboard", to: "/", hint: "Home" },
];

const recent = [
  "Track 3 safety audit report Q2",
  "Vendor contract — Alstom signalling",
  "Aluva depot electrical schematics",
];

export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const [q, setQ] = useState("");
  const navigate = useNavigate();
  const filtered = suggestions.filter((s) => s.label.toLowerCase().includes(q.toLowerCase()));

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] grid place-items-start justify-center bg-black/60 px-4 pt-[14vh] backdrop-blur-md"
          onClick={() => onOpenChange(false)}
        >
          <motion.div
            initial={{ y: -16, opacity: 0, scale: 0.98 }} animate={{ y: 0, opacity: 1, scale: 1 }} exit={{ y: -8, opacity: 0 }}
            transition={{ type: "spring", stiffness: 280, damping: 24 }}
            onClick={(e) => e.stopPropagation()}
            className="glass-strong w-full max-w-2xl overflow-hidden rounded-3xl"
          >
            <div className="flex items-center gap-3 border-b border-white/10 px-5 py-4">
              <Search className="h-4 w-4 text-muted-foreground" />
              <input
                autoFocus value={q} onChange={(e) => setQ(e.target.value)}
                placeholder="Search documents, ask questions, jump anywhere…"
                className="flex-1 bg-transparent text-base outline-none placeholder:text-muted-foreground"
              />
              <kbd className="rounded-md border border-white/10 bg-black/30 px-1.5 py-0.5 text-[10px] text-muted-foreground">ESC</kbd>
            </div>

            <div className="grid gap-4 p-4 md:grid-cols-[1fr_220px]">
              <div className="space-y-1">
                <div className="flex items-center gap-2 px-3 py-1.5 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  <Sparkles className="h-3 w-3" /> AI Suggestions
                </div>
                {(q ? filtered : suggestions).map((s) => (
                  <button key={s.label} onClick={() => { onOpenChange(false); navigate({ to: s.to }); }}
                    className="group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition hover:bg-white/5">
                    <span className="grid h-8 w-8 place-items-center rounded-lg bg-white/5 group-hover:bg-aurora">
                      <s.icon className="h-4 w-4" />
                    </span>
                    <span className="flex-1">{s.label}</span>
                    <span className="text-xs text-muted-foreground">{s.hint}</span>
                    <ArrowRight className="h-3.5 w-3.5 opacity-0 transition group-hover:opacity-100" />
                  </button>
                ))}
                {q && (
                  <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-3 text-sm">
                    <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground"><Sparkles className="h-3 w-3" /> Semantic AI answer</div>
                    Searching across 12,438 documents for <span className="text-gradient font-medium">"{q}"</span>…
                  </div>
                )}
              </div>
              <div className="space-y-1 border-l border-white/10 pl-4">
                <div className="flex items-center gap-2 px-1 py-1.5 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  <Clock className="h-3 w-3" /> Recent
                </div>
                {recent.map((r) => (
                  <button key={r} className="block w-full rounded-lg px-2 py-2 text-left text-xs text-muted-foreground hover:bg-white/5 hover:text-foreground">{r}</button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between border-t border-white/10 px-5 py-3 text-[11px] text-muted-foreground">
              <div className="flex items-center gap-3">
                <span><kbd className="rounded bg-white/10 px-1.5 py-0.5">↑↓</kbd> navigate</span>
                <span><kbd className="rounded bg-white/10 px-1.5 py-0.5">↵</kbd> open</span>
              </div>
              <span className="flex items-center gap-1"><Sparkles className="h-3 w-3" /> Powered by KMRL AI</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
