import { motion } from "motion/react";
import { type ReactNode } from "react";

export function GlassCard({ children, className = "", hover = false }: { children: ReactNode; className?: string; hover?: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      whileHover={hover ? { y: -4 } : undefined}
      className={`glass rounded-3xl p-6 ${className}`}
    >{children}</motion.div>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return <div className="mb-1 text-[10px] uppercase tracking-[0.25em] text-muted-foreground">{children}</div>;
}

export function PageShell({ title, subtitle, children, action }: { title: string; subtitle?: string; children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mx-auto w-[min(1400px,calc(100%-2rem))]">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <SectionLabel>KMRL · Document Intelligence</SectionLabel>
          <h1 className="text-3xl font-bold sm:text-4xl">{title}</h1>
          {subtitle && <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{subtitle}</p>}
        </div>
        {action}
      </motion.div>
      {children}
    </div>
  );
}

export function MetroPill({ color = "var(--electric)", children }: { color?: string; children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px]">
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
      {children}
    </span>
  );
}

export function Stat({ label, value, delta, accent = "var(--cyan-glow)" }: { label: string; value: string; delta?: string; accent?: string }) {
  return (
    <div className="glass relative overflow-hidden rounded-3xl p-5">
      <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-30 blur-2xl" style={{ background: accent }} />
      <div className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">{label}</div>
      <div className="mt-2 font-display text-3xl font-bold">{value}</div>
      {delta && <div className="mt-1 text-xs" style={{ color: accent }}>{delta}</div>}
    </div>
  );
}
