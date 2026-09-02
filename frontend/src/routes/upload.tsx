import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { useRef, useState } from "react";
import { GlassCard, PageShell, MetroPill } from "@/components/ui-bits";
import { UploadCloud, Check, Loader2, FileText, AlertTriangle, X } from "lucide-react";
import { api, ApiError, API_BASE_URL } from "@/lib/api/client";

export const Route = createFileRoute("/upload")({
  head: () => ({ meta: [{ title: "Smart Upload Studio — KMRL DocIntel" }, { name: "description", content: "Upload documents into the KMRL ingestion pipeline." }] }),
  component: UploadPage,
});

/** What the backend's DocumentValidator accepts (src/ingestion/validator.py). */
const ACCEPTED = ".pdf,.docx,.doc,.xlsx,.xls,.png,.jpg,.jpeg";

type Phase = "queued" | "uploading" | "processing" | "indexed" | "failed";

interface QueueItem {
  id: string;
  name: string;
  size: number;
  phase: Phase;
  /** Upload progress 0-100; only meaningful while `phase === "uploading"`. */
  progress: number;
  chunks?: number;
  documentId?: string;
  error?: string;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const phaseLabel: Record<Phase, string> = {
  queued: "Queued",
  uploading: "Uploading",
  processing: "Parsing, chunking and embedding on the server",
  indexed: "Indexed",
  failed: "Failed",
};

function UploadPage() {
  const [drag, setDrag] = useState(false);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const patch = (id: string, changes: Partial<QueueItem>) =>
    setQueue((current) => current.map((item) => (item.id === id ? { ...item, ...changes } : item)));

  const ingest = async (files: FileList | File[]) => {
    const incoming = Array.from(files);
    if (incoming.length === 0) return;

    const items: QueueItem[] = incoming.map((file, i) => ({
      id: `${Date.now()}-${i}-${file.name}`,
      name: file.name,
      size: file.size,
      phase: "queued",
      progress: 0,
    }));
    setQueue((current) => [...items, ...current]);

    // Sequential: each request loads the embedding model and hits the vector store, so
    // firing them in parallel just contends for the same backend.
    for (let i = 0; i < incoming.length; i += 1) {
      const file = incoming[i];
      const { id } = items[i];
      patch(id, { phase: "uploading" });

      try {
        const result = await api.upload(file, {}, (percent) => {
          patch(id, { progress: percent, phase: percent >= 100 ? "processing" : "uploading" });
        });
        patch(id, {
          phase: "indexed",
          progress: 100,
          chunks: result.chunks_created,
          documentId: result.document_id,
        });
      } catch (error) {
        patch(id, {
          phase: "failed",
          error: error instanceof ApiError ? error.userMessage : "Upload failed",
        });
      }
    }
  };

  const indexed = queue.filter((q) => q.phase === "indexed");
  const failed = queue.filter((q) => q.phase === "failed");
  const totalChunks = indexed.reduce((sum, q) => sum + (q.chunks ?? 0), 0);

  return (
    <PageShell title="Smart Upload Studio" subtitle="Drop documents into the pipeline — the backend extracts text, chunks it, embeds it and indexes it for retrieval.">
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-4">
          <motion.div
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); void ingest(e.dataTransfer.files); }}
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
              <p className="mt-2 max-w-md text-sm text-muted-foreground">PDF · DOCX · XLSX · PNG · JPG — up to 50 MB per file. Images need the OCR extras installed on the backend.</p>

              <input ref={inputRef} type="file" multiple accept={ACCEPTED} className="hidden"
                onChange={(e) => { if (e.target.files) void ingest(e.target.files); e.target.value = ""; }} />

              <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
                <button onClick={() => inputRef.current?.click()} className="rounded-full bg-aurora px-5 py-2 text-sm font-medium text-white">Choose files</button>
              </div>
            </div>
          </motion.div>

          <GlassCard>
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold">Ingestion pipeline</h3>
              <MetroPill color="var(--cyan-glow)">{indexed.length} indexed</MetroPill>
            </div>
            <p className="text-xs text-muted-foreground">
              Each file is validated, parsed (PyMuPDF for PDF, python-docx, openpyxl), cleaned, split into token-aware chunks, embedded with the configured sentence-transformer, and upserted into Qdrant. The server reports back how many chunks it stored.
            </p>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-2xl bg-white/[0.03] p-3">
                <div className="font-display text-2xl font-bold">{indexed.length}</div>
                <div className="text-[10px] text-muted-foreground">Indexed this session</div>
              </div>
              <div className="rounded-2xl bg-white/[0.03] p-3">
                <div className="font-display text-2xl font-bold">{totalChunks}</div>
                <div className="text-[10px] text-muted-foreground">Chunks stored</div>
              </div>
              <div className="rounded-2xl bg-white/[0.03] p-3">
                <div className="font-display text-2xl font-bold">{failed.length}</div>
                <div className="text-[10px] text-muted-foreground">Failed</div>
              </div>
            </div>
          </GlassCard>
        </div>

        <div className="space-y-4">
          <GlassCard>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-lg font-semibold">Queue</h3>
              {queue.length > 0 && (
                <button onClick={() => setQueue([])} className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground">
                  <X className="h-3 w-3" /> Clear
                </button>
              )}
            </div>

            {queue.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-white/10 p-6 text-center text-xs text-muted-foreground">
                Nothing queued yet. Files you add appear here with live progress and the number of chunks indexed.
              </div>
            ) : (
              <div className="space-y-3">
                {queue.map((f, i) => (
                  <motion.div key={f.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                    className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03]">
                    <div className="flex items-start gap-3 p-3">
                      <div className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${
                        f.phase === "indexed" ? "bg-emerald-500/20" : f.phase === "failed" ? "bg-amber-500/20" : "bg-aurora"
                      }`}>
                        {f.phase === "indexed" ? <Check className="h-5 w-5 text-emerald-300" />
                          : f.phase === "failed" ? <AlertTriangle className="h-5 w-5 text-amber-300" />
                          : f.phase === "queued" ? <FileText className="h-5 w-5 text-white" />
                          : <Loader2 className="h-5 w-5 animate-spin text-white" />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-medium">{f.name}</div>
                        <div className="text-[11px] text-muted-foreground">{formatSize(f.size)}</div>
                        <div className="mt-2 text-xs text-muted-foreground">
                          {f.phase === "uploading" ? `${phaseLabel.uploading} — ${f.progress}%` : phaseLabel[f.phase]}
                        </div>
                        {f.phase === "indexed" && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            <MetroPill color="var(--cyan-glow)">{f.chunks} chunk{f.chunks === 1 ? "" : "s"}</MetroPill>
                          </div>
                        )}
                        {f.phase === "failed" && <div className="mt-2 text-[11px] text-amber-200">{f.error}</div>}
                      </div>
                    </div>
                    <div className="h-1 overflow-hidden bg-white/5">
                      <div className={`h-full ${
                        f.phase === "indexed" ? "w-full bg-emerald-400"
                          : f.phase === "failed" ? "w-full bg-amber-400"
                          : f.phase === "processing" ? "w-full bg-aurora animate-shimmer"
                          : "bg-aurora"
                      }`} style={f.phase === "uploading" ? { width: `${f.progress}%` } : undefined} />
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </GlassCard>

          <GlassCard>
            <h3 className="mb-2 text-sm font-semibold">Where files go</h3>
            <p className="text-xs text-muted-foreground">
              Uploads are sent to <code className="rounded bg-black/30 px-1">{API_BASE_URL}</code> and indexed into the Qdrant collection backing search and chat. Nothing is stored in this browser.
            </p>
          </GlassCard>
        </div>
      </div>
    </PageShell>
  );
}
