import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal, Eraser } from "lucide-react";
import type { LogEntry } from "../types";

interface Props {
  logs: LogEntry[];
  onClear: () => void;
}

function formatTime(ts: number) {
  const d = new Date(ts);
  return `${d.getHours().toString().padStart(2, "0")}:${d
    .getMinutes()
    .toString()
    .padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
}

export function ChatArea({ logs, onClear }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTo({
        top: el.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [logs.length]);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-hairline bg-surface-sunken/60 backdrop-blur-md">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-hairline bg-surface/40 px-3 py-1.5">
        <div className="flex items-center gap-1.5">
          <Terminal size={11} className="text-ink-muted" strokeWidth={2.5} />
          <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-ink-muted">
            sohbet akışı
          </span>
          <span className="rounded bg-surface-sunken/80 px-1 font-mono text-[9px] text-ink-faint tabular">
            {logs.length.toString().padStart(3, "0")}
          </span>
        </div>
        <button
          onClick={onClear}
          disabled={logs.length === 0}
          className="grid h-5.5 w-5.5 place-items-center rounded-md border border-hairline bg-surface/20 text-ink-muted transition-all hover:bg-surface-raised hover:text-ink-soft disabled:pointer-events-none disabled:opacity-25"
          title="Temizle"
        >
          <Eraser size={11} strokeWidth={2} />
        </button>
      </div>

      {/* Bubble Stream */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-3 py-4 space-y-3 scroll-smooth"
      >
        {logs.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center px-4 space-y-2">
            <span className="font-display text-xl italic text-ink-muted">
              Sessizliği Bozun
            </span>
            <span className="max-w-[240px] font-mono text-[9px] uppercase tracking-[0.14em] text-ink-faint">
              Jarvan dinlemede. Sesle veya yazarak komut verebilirsiniz.
            </span>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {logs.map((log) => {
              const isUser = log.level === "user";
              const isJarvan = log.level === "jarvan";
              const isSystem = log.level === "system";
              const isError = log.level === "error";

              if (isSystem || isError) {
                return (
                  <motion.div
                    key={log.id}
                    initial={{ opacity: 0, y: 3 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.15 }}
                    className="flex justify-center px-6 py-1"
                  >
                    <span
                      className={`text-center font-mono text-[9.5px] uppercase tracking-wide leading-relaxed py-0.5 px-2.5 rounded-full border bg-surface-sunken/45 ${
                        isError
                          ? "border-red-500/20 text-red-400/80 shadow-[0_0_8px_rgba(239,68,68,0.15)]"
                          : "border-hairline text-ink-muted/80"
                      }`}
                    >
                      {log.text}
                      {log.provider && (
                        <span className="ml-1 text-[8px] text-ink-faint">
                          ({log.provider})
                        </span>
                      )}
                    </span>
                  </motion.div>
                );
              }

              return (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, y: 8, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ type: "spring", stiffness: 450, damping: 30 }}
                  className={`flex w-full flex-col ${isUser ? "items-end" : "items-start"}`}
                >
                  <div className="flex items-center gap-1.5 mb-1 px-1">
                    <span className="font-mono text-[8.5px] text-ink-faint tabular">
                      {formatTime(log.timestamp)}
                    </span>
                    <span className="font-mono text-[8px] uppercase tracking-widest text-ink-muted">
                      {isUser ? "sen" : "jvn"}
                    </span>
                  </div>

                  <div
                    className={`max-w-[85%] rounded-xl px-3.5 py-2 font-mono text-[11px] leading-relaxed shadow-sm border ${
                      isUser
                        ? "rounded-tr-none border-amber/30 bg-amber/5 text-ink amber-glow-sm"
                        : "rounded-tl-none border-hairline bg-surface/75 text-ink-soft"
                    }`}
                  >
                    <p className="select-text whitespace-pre-wrap break-words">{log.text}</p>
                    {log.provider && (
                      <div className="mt-1 flex justify-end">
                        <span className="font-mono text-[8px] text-ink-faint uppercase tracking-wider">
                          via {log.provider}
                        </span>
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
