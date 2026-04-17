import { AnimatePresence, motion } from "framer-motion";
import { Eraser, Terminal } from "lucide-react";
import { useEffect, useRef } from "react";
import type { LogEntry } from "../types";

interface Props {
  logs: LogEntry[];
  onClear: () => void;
}

const LEVEL_CONFIG = {
  user: { prefix: "sen", color: "text-ink" },
  jarvan: { prefix: "jvn", color: "text-amber" },
  system: { prefix: "sys", color: "text-ink-muted" },
  error: { prefix: "err", color: "text-red-400" },
} as const;

function formatTime(ts: number) {
  const d = new Date(ts);
  return `${d.getHours().toString().padStart(2, "0")}:${d
    .getMinutes()
    .toString()
    .padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
}

export function LogPanel({ logs, onClear }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs.length]);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-hairline bg-surface-sunken/80">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-hairline px-2.5 py-1.5">
        <div className="flex items-center gap-1.5">
          <Terminal size={10} className="text-ink-muted" strokeWidth={2} />
          <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-ink-muted">
            akış
          </span>
          <span className="font-mono text-[9px] text-ink-faint tabular">
            {logs.length.toString().padStart(3, "0")}
          </span>
        </div>
        <button
          onClick={onClear}
          disabled={logs.length === 0}
          className="grid h-5 w-5 place-items-center rounded text-ink-muted transition-colors hover:bg-surface-raised hover:text-ink-soft disabled:opacity-30"
          title="Temizle"
        >
          <Eraser size={10} strokeWidth={2} />
        </button>
      </div>

      {/* Log stream */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-2.5 py-1.5 font-mono text-[10.5px] leading-[1.55]"
      >
        {logs.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-ink-faint">
              akış boş — başlatıldığında burası dolacak
            </span>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {logs.map((log) => {
              const cfg = LEVEL_CONFIG[log.level];
              return (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                  className="flex items-start gap-2 py-0.5"
                >
                  <span className="w-[52px] shrink-0 select-text text-ink-faint tabular">
                    {formatTime(log.timestamp)}
                  </span>
                  <span
                    className={`w-[28px] shrink-0 uppercase tracking-wider ${cfg.color} opacity-70`}
                  >
                    {cfg.prefix}
                  </span>
                  <span className={`min-w-0 flex-1 select-text break-words ${cfg.color}`}>
                    {log.text}
                    {log.provider && (
                      <span className="ml-1.5 text-[9px] text-ink-faint">
                        [{log.provider}]
                      </span>
                    )}
                  </span>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
