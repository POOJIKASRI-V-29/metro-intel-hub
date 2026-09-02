import { createFileRoute } from "@tanstack/react-router";
import { motion, AnimatePresence } from "motion/react";
import { useState } from "react";
import { GlassCard, MetroPill } from "@/components/ui-bits";
import { Send, RefreshCw, FileText, Sparkles, Plus, MessageSquare, AlertTriangle, Loader2 } from "lucide-react";
import { useChatSession, useHealth } from "@/lib/api/hooks";
import { API_BASE_URL } from "@/lib/api/client";

export const Route = createFileRoute("/workspace")({
  head: () => ({ meta: [{ title: "AI Workspace — KMRL DocIntel" }, { name: "description", content: "Conversational AI workspace for KMRL document intelligence." }] }),
  component: Workspace,
});

const starters = [
  "What are the open signalling risks and who owns them?",
  "Which vendor contracts are expiring, and what do they block?",
  "Summarise the most recent audit findings.",
];

/** Trims a citation snippet down to something that fits on one or two lines. */
function excerpt(text: string, limit = 160): string {
  const collapsed = text.replace(/\s+/g, " ").trim();
  return collapsed.length > limit ? `${collapsed.slice(0, limit)}…` : collapsed;
}

function Workspace() {
  const [input, setInput] = useState("");
  const chat = useChatSession();
  const health = useHealth();

  const offline = health.isError;
  const questions = chat.messages.filter((m) => m.role === "user");

  const send = (text: string) => {
    if (!text.trim() || chat.isThinking) return;
    chat.send(text);
    setInput("");
  };

  return (
    <div className="mx-auto w-[min(1500px,calc(100%-2rem))]">
      {offline && (
        <div className="mb-3 flex items-center gap-2 rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-2.5 text-xs text-amber-200">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            Backend unreachable at <code className="rounded bg-black/30 px-1">{API_BASE_URL}</code>. Start the API, or set <code className="rounded bg-black/30 px-1">VITE_API_URL</code> to point at it.
          </span>
        </div>
      )}

      <div className="grid h-[calc(100vh-8rem)] gap-4 lg:grid-cols-[260px_1fr_320px]">
        {/* Left — this session's questions */}
        <GlassCard className="flex flex-col overflow-hidden p-0">
          <div className="flex items-center justify-between border-b border-white/10 p-4">
            <h3 className="text-sm font-semibold">This conversation</h3>
            <button
              onClick={chat.reset}
              title="Start a new conversation"
              className="grid h-7 w-7 place-items-center rounded-lg bg-aurora"
            >
              <Plus className="h-3.5 w-3.5 text-white" />
            </button>
          </div>
          <div className="scroll-thin flex-1 overflow-y-auto p-2">
            {questions.length === 0 ? (
              <p className="px-3 py-2 text-[11px] leading-relaxed text-muted-foreground">
                Your questions appear here as you ask them. History lives in this browser tab only.
              </p>
            ) : (
              questions.map((q, i) => (
                <div key={i} className="flex w-full flex-col items-start gap-0.5 rounded-xl px-3 py-2.5 text-left text-sm hover:bg-white/5">
                  <span className="line-clamp-2 font-medium">{q.content}</span>
                  <span className="text-[11px] text-muted-foreground">Turn {i + 1}</span>
                </div>
              ))
            )}
          </div>
          <div className="border-t border-white/10 p-3 text-[11px] text-muted-foreground">
            <div className="flex items-center justify-between">
              <span>Tokens this session</span>
              <span>{chat.totalTokens?.toLocaleString() ?? "—"}</span>
            </div>
          </div>
        </GlassCard>

        {/* Center — chat */}
        <GlassCard className="flex flex-col overflow-hidden p-0">
          <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
            <div>
              <div className="text-sm font-semibold">Document intelligence chat</div>
              <div className="text-[11px] text-muted-foreground">
                {chat.lastCitations.length > 0
                  ? `${chat.lastCitations.length} source${chat.lastCitations.length === 1 ? "" : "s"} referenced`
                  : "Answers are grounded in your indexed documents"}
              </div>
            </div>
            <button
              onClick={chat.reset}
              title="Clear conversation"
              className="grid h-8 w-8 place-items-center rounded-lg bg-white/5 hover:bg-white/10"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>

          <div className="scroll-thin flex-1 space-y-5 overflow-y-auto p-6">
            {chat.messages.length === 0 && !chat.isThinking && (
              <div className="grid h-full place-items-center text-center">
                <div>
                  <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-aurora">
                    <Sparkles className="h-5 w-5 text-white" />
                  </div>
                  <h3 className="mt-4 text-lg font-semibold">Ask about your documents</h3>
                  <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">
                    Every answer is retrieved from documents you have uploaded, and cites the passages it used.
                  </p>
                </div>
              </div>
            )}

            <AnimatePresence initial={false}>
              {chat.messages.map((m, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`}>
                  {m.role === "assistant" && (
                    <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-xl ${m.failed ? "bg-amber-500/20" : "bg-aurora"}`}>
                      {m.failed ? <AlertTriangle className="h-4 w-4 text-amber-300" /> : <Sparkles className="h-4 w-4 text-white" />}
                    </div>
                  )}
                  <div className={`max-w-[78%] rounded-2xl px-4 py-3 ${
                    m.role === "user"
                      ? "bg-aurora text-white"
                      : m.failed
                        ? "border border-amber-400/30 bg-amber-400/10 text-amber-100"
                        : "bg-white/[0.04] border border-white/10"
                  }`}>
                    <div className="whitespace-pre-wrap text-sm leading-relaxed">{m.content}</div>

                    {m.citations && m.citations.length > 0 && (
                      <div className="mt-3 space-y-1.5 border-t border-white/10 pt-3">
                        {m.citations.map((c, idx) => (
                          <div key={`${c.document_id}-${idx}`} className="flex items-start gap-2 text-[11px] text-muted-foreground">
                            <span className="grid h-4 w-4 shrink-0 place-items-center rounded bg-cyan-300/20 text-[9px] text-cyan-200">{idx + 1}</span>
                            <span>
                              <span className="text-foreground">{c.filename}</span>
                              {c.similarity_score != null && ` — score ${c.similarity_score.toFixed(3)}`}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    {m.usage && (
                      <div className="mt-2 text-[10px] uppercase tracking-wider text-muted-foreground">
                        {m.usage.total_tokens.toLocaleString()} tokens
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {chat.isThinking && (
              <div className="flex gap-3">
                <div className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-aurora">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <div className="flex items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-muted-foreground">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Retrieving context and generating an answer…
                </div>
              </div>
            )}

            {chat.messages.length === 0 && (
              <div className="flex flex-wrap justify-center gap-2">
                {starters.map((q) => (
                  <button key={q} onClick={() => send(q)} disabled={chat.isThinking}
                    className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-muted-foreground transition hover:border-cyan-300/30 hover:text-foreground disabled:opacity-40">
                    ↳ {q}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="border-t border-white/10 p-3">
            <div className="glass-strong flex items-end gap-2 rounded-2xl p-2">
              <textarea
                value={input} onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
                rows={1} placeholder="Ask anything about your documents…"
                disabled={chat.isThinking}
                className="max-h-32 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder:text-muted-foreground disabled:opacity-50"
              />
              <button onClick={() => send(input)} disabled={chat.isThinking || !input.trim()}
                className="grid h-9 w-9 place-items-center rounded-xl bg-aurora disabled:opacity-40">
                {chat.isThinking ? <Loader2 className="h-4 w-4 animate-spin text-white" /> : <Send className="h-4 w-4 text-white" />}
              </button>
            </div>
            <div className="mt-2 px-1 text-[10px] text-muted-foreground">Shift + Enter for newline · answers cite the passages they used</div>
          </div>
        </GlassCard>

        {/* Right — referenced docs */}
        <GlassCard className="flex flex-col overflow-hidden p-0">
          <div className="border-b border-white/10 p-4">
            <h3 className="text-sm font-semibold flex items-center gap-2"><FileText className="h-4 w-4" /> Referenced documents</h3>
            <div className="mt-1 text-[11px] text-muted-foreground">Passages retrieved for the latest answer</div>
          </div>
          <div className="scroll-thin flex-1 space-y-3 overflow-y-auto p-4">
            {chat.lastCitations.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 p-4 text-center text-[11px] text-muted-foreground">
                <MessageSquare className="mx-auto mb-1 h-4 w-4" /> Ask a question to surface the sources behind the answer.
              </div>
            ) : (
              chat.lastCitations.map((c, i) => (
                <motion.div key={`${c.document_id}-${i}`} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}
                  className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                  <div className="mb-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                    <span className="grid h-4 w-4 place-items-center rounded bg-cyan-300/20 text-cyan-200">{i + 1}</span>
                    Cited
                  </div>
                  <div className="text-sm font-medium">{c.filename}</div>
                  <div className="mt-2 rounded-lg border-l-2 border-cyan-300/60 bg-cyan-300/5 px-3 py-2 text-xs text-muted-foreground">
                    {excerpt(c.text_snippet)}
                  </div>
                  <div className="mt-2 flex gap-1">
                    {c.similarity_score != null && <MetroPill color="var(--cyan-glow)">{c.similarity_score.toFixed(3)}</MetroPill>}
                    {c.page_number != null && <MetroPill>p. {String(c.page_number)}</MetroPill>}
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
