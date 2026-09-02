import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "motion/react";
import { useMemo, useState } from "react";
import { GlassCard, PageShell, MetroPill } from "@/components/ui-bits";
import { LayoutGrid, List, GitBranch, FileText, FileSpreadsheet, FileImage, AlertTriangle, Loader2, Upload } from "lucide-react";
import { useDocuments } from "@/lib/api/hooks";
import type { DocumentSummary } from "@/lib/api/types";

export const Route = createFileRoute("/explorer")({
  head: () => ({ meta: [{ title: "Document Explorer — KMRL DocIntel" }, { name: "description", content: "Browse every document indexed for retrieval." }] }),
  component: Explorer,
});

const palette = ["var(--cyan-glow)", "var(--purple-glow)", "#ffb84d", "#7cffb2", "var(--electric)", "#ff6b9d", "#a78bfa"];

/** Stable colour per department, so a given department looks the same across renders. */
function departmentColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  return palette[hash % palette.length];
}

function iconFor(extension: string | null) {
  switch (extension) {
    case ".xlsx":
    case ".xls":
      return FileSpreadsheet;
    case ".png":
    case ".jpg":
    case ".jpeg":
      return FileImage;
    default:
      return FileText;
  }
}

function departmentOf(doc: DocumentSummary): string | null {
  const value = doc.metadata?.department;
  return typeof value === "string" ? value : null;
}

function formatDate(iso: string | null): string {
  if (!iso) return "date unknown";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "date unknown";
  return parsed.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

type View = "grid" | "list" | "timeline";

function Explorer() {
  const [view, setView] = useState<View>("grid");
  const [department, setDepartment] = useState("All");
  const documents = useDocuments();

  const docs = useMemo(() => documents.data?.documents ?? [], [documents.data]);

  // Filters come from the corpus itself rather than a fixed list, so they can never
  // offer a department that has no documents behind it.
  const departments = useMemo(() => {
    const found = new Set<string>();
    docs.forEach((d) => { const dept = departmentOf(d); if (dept) found.add(dept); });
    return ["All", ...Array.from(found).sort()];
  }, [docs]);

  const filtered = department === "All" ? docs : docs.filter((d) => departmentOf(d) === department);

  const byNewest = useMemo(
    () => [...filtered].sort((a, b) => (b.upload_date ?? "").localeCompare(a.upload_date ?? "")),
    [filtered],
  );

  const totalChunks = docs.reduce((sum, d) => sum + d.chunk_count, 0);

  return (
    <PageShell
      title="Document Explorer"
      subtitle={
        documents.data
          ? `${documents.data.truncated ? "at least " : ""}${documents.data.total} document${documents.data.total === 1 ? "" : "s"} indexed · ${totalChunks} retrievable chunk${totalChunks === 1 ? "" : "s"}`
          : "Everything indexed and available to search and chat."
      }
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
      {documents.isLoading && (
        <GlassCard>
          <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading indexed documents…
          </div>
        </GlassCard>
      )}

      {documents.isError && (
        <GlassCard className="border-amber-400/30">
          <div className="flex items-start gap-2 py-4 text-sm text-amber-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <div className="font-medium">Cannot list documents</div>
              <p className="mt-1 text-xs text-amber-200/80">{documents.error.userMessage}</p>
            </div>
          </div>
        </GlassCard>
      )}

      {documents.isSuccess && docs.length === 0 && (
        <GlassCard>
          <div className="py-12 text-center">
            <FileText className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
            <div className="text-sm font-medium">Nothing indexed yet</div>
            <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
              Upload a document and it will appear here, searchable and available to the AI workspace.
            </p>
            <Link to="/upload" className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-aurora px-4 py-1.5 text-xs font-medium text-white">
              <Upload className="h-3.5 w-3.5" /> Upload documents
            </Link>
          </div>
        </GlassCard>
      )}

      {documents.data?.truncated && (
        <GlassCard className="mb-4 border-amber-400/30">
          <div className="flex items-start gap-2 text-xs text-amber-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              Showing the first {docs.length} documents. The index is larger than the listing scan covers, so this is a partial view — use search to reach the rest.
            </span>
          </div>
        </GlassCard>
      )}

      {docs.length > 0 && (
        <>
          {departments.length > 1 && (
            <div className="mb-4 flex flex-wrap items-center gap-2">
              {departments.map((t) => (
                <button key={t} onClick={() => setDepartment(t)} className={`rounded-full border px-3 py-1.5 text-xs transition ${department === t ? "border-transparent bg-aurora text-white" : "border-white/10 bg-white/5 text-muted-foreground hover:text-foreground"}`}>{t}</button>
              ))}
            </div>
          )}

          {view === "grid" && (
            <div className="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4">
              {filtered.map((d, i) => {
                const Ic = iconFor(d.extension);
                const dept = departmentOf(d);
                const accent = dept ? departmentColor(dept) : "var(--cyan-glow)";
                return (
                  <motion.div key={d.document_id} initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.03 }}
                    className="mb-4 break-inside-avoid">
                    <Link to="/document/$id" params={{ id: d.document_id }}>
                      <motion.div whileHover={{ y: -4 }} className="group glass overflow-hidden rounded-2xl">
                        <div className="relative h-36 overflow-hidden" style={{ background: `linear-gradient(135deg, ${accent}33, transparent)` }}>
                          <div className="absolute inset-0 grid-bg opacity-40" />
                          <Ic className="absolute right-4 top-4 h-6 w-6 opacity-60" />
                          {dept && (
                            <div className="absolute bottom-3 left-3 right-3">
                              <MetroPill color={accent}>{dept}</MetroPill>
                            </div>
                          )}
                        </div>
                        <div className="p-4">
                          <div className="break-words font-medium leading-tight">{d.filename}</div>
                          <div className="mt-3 flex flex-wrap gap-1.5 text-[10px] text-muted-foreground">
                            {d.extension && <span className="rounded-full bg-white/5 px-2 py-0.5">{d.extension.replace(".", "").toUpperCase()}</span>}
                            <span className="rounded-full bg-white/5 px-2 py-0.5">{d.chunk_count} chunk{d.chunk_count === 1 ? "" : "s"}</span>
                            <span className="rounded-full bg-white/5 px-2 py-0.5">{formatDate(d.upload_date)}</span>
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
                <div className="col-span-6">Filename</div><div className="col-span-2">Department</div><div className="col-span-2">Indexed</div><div className="col-span-2">Chunks</div>
              </div>
              {filtered.map((d) => {
                const dept = departmentOf(d);
                return (
                  <Link to="/document/$id" params={{ id: d.document_id }} key={d.document_id} className="grid grid-cols-12 items-center px-5 py-3 text-sm hover:bg-white/5">
                    <div className="col-span-6 truncate font-medium">{d.filename}</div>
                    <div className="col-span-2">{dept ? <MetroPill color={departmentColor(dept)}>{dept}</MetroPill> : <span className="text-[11px] text-muted-foreground">—</span>}</div>
                    <div className="col-span-2 text-muted-foreground">{formatDate(d.upload_date)}</div>
                    <div className="col-span-2 text-muted-foreground">{d.chunk_count}</div>
                  </Link>
                );
              })}
            </GlassCard>
          )}

          {view === "timeline" && (
            <GlassCard>
              <ol className="relative space-y-6 border-l border-white/10 pl-6">
                {byNewest.map((d) => {
                  const dept = departmentOf(d);
                  const accent = dept ? departmentColor(dept) : "var(--cyan-glow)";
                  return (
                    <li key={d.document_id} className="relative">
                      <span className="absolute -left-[27px] mt-2 h-3 w-3 rounded-full" style={{ background: accent, boxShadow: `0 0 12px ${accent}` }} />
                      <div className="text-xs text-muted-foreground">{formatDate(d.upload_date)}</div>
                      <Link to="/document/$id" params={{ id: d.document_id }} className="block break-words text-base font-medium hover:text-gradient">{d.filename}</Link>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {d.chunk_count} chunk{d.chunk_count === 1 ? "" : "s"} indexed{dept ? ` · ${dept}` : ""}
                      </div>
                    </li>
                  );
                })}
              </ol>
            </GlassCard>
          )}
        </>
      )}
    </PageShell>
  );
}
