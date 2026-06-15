import { Minus, X, Pin, Cpu } from "lucide-react";
import { useState } from "react";
import { motion } from "framer-motion";

interface Props {
  connected: boolean;
  onToggleTasks?: () => void;
  showTasksButton?: boolean;
  activeTasksCount?: number;
}

export function TitleBar({ connected, onToggleTasks, showTasksButton = false, activeTasksCount = 0 }: Props) {
  const [pinned, setPinned] = useState(false);

  const handlePin = async () => {
    const next = await window.jarvan.toggleAlwaysOnTop();
    setPinned(next);
  };

  return (
    <div className="drag-region relative flex h-[38px] items-center justify-between border-b border-hairline bg-obsidian/90 px-3 backdrop-blur">
      {/* Left: wordmark + connection dot */}
      <div className="flex items-center gap-2.5">
        <motion.span
          className={`inline-block h-1.5 w-1.5 rounded-full ${
            connected ? "bg-emerald-400" : "bg-ink-muted"
          }`}
          animate={
            connected
              ? { boxShadow: ["0 0 0px rgba(52,211,153,0.6)", "0 0 8px rgba(52,211,153,0.8)", "0 0 0px rgba(52,211,153,0.6)"] }
              : {}
          }
          transition={{ duration: 2, repeat: Infinity }}
        />
        <div className="flex items-baseline gap-1">
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-ink">
            Jarvan
          </span>
          <span className="font-mono text-[9px] text-ink-muted">v0.1</span>
        </div>
      </div>

      {/* Right: tasks, pin + window controls */}
      <div className="no-drag flex items-center gap-1">
        {showTasksButton && (
          <button
            onClick={onToggleTasks}
            className={`relative grid h-6 w-6 place-items-center rounded-md transition-colors text-ink-muted hover:bg-surface-raised hover:text-ink-soft`}
            title="Görev Paneli"
          >
            <Cpu size={11} strokeWidth={2} />
            {activeTasksCount > 0 && (
              <span className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-amber animate-pulse shadow-[0_0_6px_#ff8a3d]" />
            )}
          </button>
        )}
        <button
          onClick={handlePin}
          className={`grid h-6 w-6 place-items-center rounded-md transition-colors ${
            pinned
              ? "bg-amber/15 text-amber"
              : "text-ink-muted hover:bg-surface-raised hover:text-ink-soft"
          }`}
          title="Her zaman üstte"
        >
          <Pin size={11} strokeWidth={2} className={pinned ? "rotate-45" : ""} />
        </button>
        <button
          onClick={() => window.jarvan.minimize()}
          className="grid h-6 w-6 place-items-center rounded-md text-ink-muted transition-colors hover:bg-surface-raised hover:text-ink-soft"
          title="Gizle"
        >
          <Minus size={12} strokeWidth={2} />
        </button>
        <button
          onClick={() => window.jarvan.close()}
          className="grid h-6 w-6 place-items-center rounded-md text-ink-muted transition-colors hover:bg-red-500/20 hover:text-red-400"
          title="Tepsiye gönder"
        >
          <X size={12} strokeWidth={2} />
        </button>
      </div>
    </div>
  );
}
