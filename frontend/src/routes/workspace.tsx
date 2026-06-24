import { createFileRoute } from "@tanstack/react-router";
import { motion, AnimatePresence } from "motion/react";
import { useState } from "react";
import { PageShell, GlassCard, MetroPill } from "@/components/ui-bits";
import { Mic, Send, RefreshCw, Download, FileText, Sparkles, Plus, MessageSquare } from "lucide-react";

export const Route = createFileRoute("/workspace")({
  head: () => ({ meta: [{ title: "AI Workspace — KMRL DocIntel" }, { name: "description", content: "Conversational AI workspace for KMRL document intelligence." }] }),
  component: Workspace,
});

type Msg = { role: "user" | "assistant"; text: string; cites?: { id: number; title: string; line: string }[]; confidence?: number };

const initial: Msg[] = [
  { role: "user", text: "Summarize all signalling-related risks identified in the last quarter." },
  {
    role: "assistant",
    confidence: 96,
    text:
      "Across 47 signalling documents from Apr–Jun 2026, three risk clusters emerged:\n\n1. **Aluva–Pettah corridor** — 12 intermittent ATP faults traced to firmware mismatch on rev 4.2 OBUs.\n2. **Edappally junction** — 4 incidents of premature signal aspect changes during monsoon humidity peaks.\n3. **Vendor AMC gap** — Alstom AMC #A-2024-31 lapses on Jun 28 with no continuity plan filed.\n\nRecommended action: schedule joint review with Engineering + Procurement before Jun 25.",
    cites: [
      { id: 1, title: "Aluva–Pettah Signalling Audit Q2", line: "Section 4.2 — ATP firmware compatibility matrix" },
      { id: 2, title: "Vendor Contract — Alstom AMC", line: "Clause 11.3 — Renewal & continuity obligations" },
      { id: 4, title: "Coach C-08 Incident Report", line: "Annex B — Edappally signalling logs" },
    ],
  },
];

const threads = [
  { id: "t1", title: "Signalling risk analysis Q2", time: "Today" },
  { id: "t2", title: "Vendor renewals — next 60 days", time: "Today" },
  { id: "t3", title: "Track-3 metallurgy review", time: "Yesterday" },
  { id: "t4", title: "Annual safety audit prep", time: "Jun 18" },
  { id: "t5", title: "Edappally land acquisition", time: "Jun 15" },
];

const followups = [
  "Which vendors are tied to those signalling faults?",
  "Draft an escalation memo to Procurement.",
  "Show ATP firmware versions across all OBUs.",
];

function Workspace() {
  const [msgs, setMsgs] = useState<Msg[]>(initial);
  const [input, setInput] = useState("");
  const [active, setActive] = useState("t1");

  const send = (text: string) => {
    if (!text.trim()) return;
    setMsgs((m) => [...m, { role: "user", text }, { role: "assistant", text: "Analyzing 12,438 indexed documents…", confidence: 92 }]);
    setInput("");
  };

  return (
    <div className="mx-auto w-[min(1500px,calc(100%-2rem))]">
      <div className="grid h-[calc(100vh-8rem)] gap-4 lg:grid-cols-[260px_1fr_320px]">
        {/* Left — threads */}
        <GlassCard className="flex flex-col overflow-hidden p-0">
          <div className="flex items-center justify-between border-b border-white/10 p-4">
            <h3 className="text-sm font-semibold">Conversations</h3>
            <button className="grid h-7 w-7 place-items-center rounded-lg bg-aurora"><Plus className="h-3.5 w-3.5 text-white" /></button>
          </div>
          <div className="scroll-thin flex-1 overflow-y-auto p-2">
            {threads.map((t) => (
              <button key={t.id} onClick={() => setActive(t.id)} className={`flex w-full flex-col items-start gap-0.5 rounded-xl px-3 py-2.5 text-left text-sm ${active === t.id ? "bg-white/10" : "hover:bg-white/5"}`}>
                <span className="line-clamp-1 font-medium">{t.title}</span>
                <span className="text-[11px] text-muted-foreground">{t.time}</span>
              </button>
            ))}
          </div>
          <div className="border-t border-white/10 p-3 text-[11px] text-muted-foreground">
            <div className="flex items-center justify-between"><span>Tokens used</span><span>34.2k / 200k</span></div>
            <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-white/5"><div className="h-full w-[17%] bg-aurora" /></div>
          </div>
        </GlassCard>

        {/* Center — chat */}
        <GlassCard className="flex flex-col overflow-hidden p-0">
          <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
            <div>
              <div className="text-sm font-semibold">Signalling risk analysis Q2</div>
              <div className="text-[11px] text-muted-foreground">3 documents referenced · gpt-kmrl-v3</div>
            </div>
            <div className="flex gap-1">
              <button className="grid h-8 w-8 place-items-center rounded-lg bg-white/5 hover:bg-white/10"><Download className="h-4 w-4" /></button>
              <button className="grid h-8 w-8 place-items-center rounded-lg bg-white/5 hover:bg-white/10"><RefreshCw className="h-4 w-4" /></button>
            </div>
          </div>

          <div className="scroll-thin flex-1 space-y-5 overflow-y-auto p-6">
            <AnimatePresence initial={false}>
              {msgs.map((m, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
                  {m.role === "assistant" && <div className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-aurora"><Sparkles className="h-4 w-4 text-white" /></div>}
                  <div className={`max-w-[78%] rounded-2xl px-4 py-3 ${m.role === "user" ? "bg-aurora text-white" : "bg-white/[0.04] border border-white/10"}`}>
                    {m.role === "assistant" && m.confidence != null && (
                      <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted-foreground">
                        <span>AI confidence</span>
                        <div className="h-1 w-20 overflow-hidden rounded-full bg-white/10">
                          <div className="h-full bg-aurora" style={{ width: `${m.confidence}%` }} />
                        </div>
                        <span>{m.confidence}%</span>
                      </div>
                    )}
                    <div className="whitespace-pre-wrap text-sm leading-relaxed">{m.text}</div>
                    {m.cites && (
                      <div className="mt-3 space-y-1.5 border-t border-white/10 pt-3">
                        {m.cites.map((c, idx) => (
                          <div key={c.id} className="flex items-start gap-2 text-[11px] text-muted-foreground">
                            <span className="grid h-4 w-4 shrink-0 place-items-center rounded bg-cyan-300/20 text-[9px] text-cyan-200">{idx + 1}</span>
                            <span><span className="text-foreground">{c.title}</span> — {c.line}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            <div className="flex flex-wrap gap-2 pl-11">
              {followups.map((q) => (
                <button key={q} onClick={() => send(q)} className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-muted-foreground transition hover:border-cyan-300/30 hover:text-foreground">
                  ↳ {q}
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-white/10 p-3">
            <div className="glass-strong flex items-end gap-2 rounded-2xl p-2">
              <button className="grid h-9 w-9 place-items-center rounded-xl bg-white/5"><Mic className="h-4 w-4" /></button>
              <textarea
                value={input} onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
                rows={1} placeholder="Ask anything about your documents…"
                className="max-h-32 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder:text-muted-foreground"
              />
              <button onClick={() => send(input)} className="grid h-9 w-9 place-items-center rounded-xl bg-aurora"><Send className="h-4 w-4 text-white" /></button>
            </div>
            <div className="mt-2 px-1 text-[10px] text-muted-foreground">Shift + Enter for newline · responses cite sources · powered by KMRL AI</div>
          </div>
        </GlassCard>

        {/* Right — referenced docs */}
        <GlassCard className="flex flex-col overflow-hidden p-0">
          <div className="border-b border-white/10 p-4">
            <h3 className="text-sm font-semibold flex items-center gap-2"><FileText className="h-4 w-4" /> Referenced documents</h3>
            <div className="mt-1 text-[11px] text-muted-foreground">Auto-pinned by the AI</div>
          </div>
          <div className="scroll-thin flex-1 space-y-3 overflow-y-auto p-4">
            {(initial[1].cites ?? []).map((c, i) => (
              <motion.div key={c.id} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                <div className="mb-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                  <span className="grid h-4 w-4 place-items-center rounded bg-cyan-300/20 text-cyan-200">{i + 1}</span>
                  Cited
                </div>
                <div className="text-sm font-medium">{c.title}</div>
                <div className="mt-2 rounded-lg border-l-2 border-cyan-300/60 bg-cyan-300/5 px-3 py-2 text-xs text-muted-foreground">
                  <span className="text-cyan-200">Highlighted:</span> {c.line}
                </div>
                <div className="mt-2 flex gap-1">
                  <MetroPill color="var(--cyan-glow)">PDF</MetroPill>
                  <MetroPill>2026</MetroPill>
                </div>
              </motion.div>
            ))}
            <div className="rounded-2xl border border-dashed border-white/10 p-4 text-center text-[11px] text-muted-foreground">
              <MessageSquare className="mx-auto mb-1 h-4 w-4" /> Continue the conversation to surface more sources.
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
