import { Link } from "@tanstack/react-router";
import { Search, Command, Sun, Moon, Bell, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

const links = [
  { to: "/", label: "Command" },
  { to: "/explorer", label: "Explorer" },
  { to: "/workspace", label: "AI Workspace" },
  { to: "/upload", label: "Upload" },
  { to: "/graph", label: "Graph" },
  { to: "/analytics", label: "Analytics" },
] as const;

export function TopNav({ onOpenPalette }: { onOpenPalette: () => void }) {
  const [light, setLight] = useState(false);
  useEffect(() => {
    document.documentElement.classList.toggle("light", light);
    document.documentElement.classList.toggle("dark", !light);
  }, [light]);

  return (
    <header className="fixed top-4 left-1/2 z-50 w-[min(1200px,calc(100%-2rem))] -translate-x-1/2">
      <div className="glass-strong flex items-center gap-3 rounded-full px-3 py-2">
        <Link to="/" className="flex items-center gap-2 pl-2 pr-3">
          <div className="relative grid h-8 w-8 place-items-center rounded-xl bg-aurora">
            <Sparkles className="h-4 w-4 text-white" />
            <span className="absolute inset-0 rounded-xl animate-pulse-ring" />
          </div>
          <div className="hidden flex-col leading-none sm:flex">
            <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">KMRL</span>
            <span className="text-sm font-semibold">DocIntel</span>
          </div>
        </Link>

        <nav className="hidden flex-1 items-center justify-center gap-1 md:flex">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className="rounded-full px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground"
              activeProps={{ className: "rounded-full px-3 py-1.5 text-sm bg-white/10 text-foreground" }}
              activeOptions={{ exact: l.to === "/" }}
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <button onClick={onOpenPalette} className="ml-auto flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-white/10">
          <Search className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Search anything</span>
          <kbd className="ml-2 hidden items-center gap-0.5 rounded-md border border-white/10 bg-black/30 px-1.5 py-0.5 text-[10px] sm:flex">
            <Command className="h-2.5 w-2.5" />K
          </kbd>
        </button>

        <button className="grid h-9 w-9 place-items-center rounded-full border border-white/10 bg-white/5 hover:bg-white/10">
          <Bell className="h-4 w-4" />
        </button>
        <button onClick={() => setLight((v) => !v)} className="grid h-9 w-9 place-items-center rounded-full border border-white/10 bg-white/5 hover:bg-white/10">
          {light ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
        </button>
      </div>
    </header>
  );
}
