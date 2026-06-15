import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, AlertCircle, Loader2, Cpu } from "lucide-react";
import type { TaskInfo, TaskStatus, TaskTarget } from "../types";

interface Props {
  tasks: TaskInfo[];
  selectedTaskId: string | null;
  onSelectTask: (id: string) => void;
}

const TARGET_LABELS: Record<TaskTarget, string> = {
  codex: "CODEX",
  agy: "AGY CLI",
  local: "LOCAL",
  gemma: "GEMMA",
};

const STATUS_CONFIG: Record<
  TaskStatus,
  { label: string; bg: string; text: string; border: string; icon: React.ReactNode }
> = {
  queued: {
    label: "KUYRUKTA",
    bg: "bg-surface-sunken/45",
    text: "text-ink-muted",
    border: "border-hairline/60",
    icon: <div className="h-1.5 w-1.5 rounded-full bg-ink-muted" />,
  },
  running: {
    label: "ÇALIŞIYOR",
    bg: "bg-cyan-500/5 animate-pulse",
    text: "text-cyan-400",
    border: "border-cyan-400/40 teal-glow",
    icon: <Loader2 size={10} className="animate-spin text-cyan-400" />,
  },
  blocked: {
    label: "BLOKE ⚠",
    bg: "bg-amber/10 animate-pulse",
    text: "text-amber",
    border: "border-amber/50 border-dashed",
    icon: <AlertCircle size={10} className="text-amber" />,
  },
  done: {
    label: "TAMAMLANDI",
    bg: "bg-emerald-500/5",
    text: "text-emerald-400",
    border: "border-emerald-500/25",
    icon: <CheckCircle2 size={10} className="text-emerald-400" />,
  },
  error: {
    label: "HATA ALINDI",
    bg: "bg-red-500/5",
    text: "text-red-400",
    border: "border-red-500/25",
    icon: <AlertCircle size={10} className="text-red-400" />,
  },
};

function formatDuration(ms: number) {
  if (ms < 0) return "0s";
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}dk ${seconds % 60}s`;
}

export function TaskPanel({ tasks, selectedTaskId, onSelectTask }: Props) {
  const [, setTick] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setTick((t) => t + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const activeCount = tasks.filter((t) => t.status === "running").length;
  const blockedCount = tasks.filter((t) => t.status === "blocked").length;
  const doneCount = tasks.filter((t) => t.status === "done").length;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Task Summary Stat Bar */}
      <div className="flex items-center gap-2 border-b border-hairline/80 bg-surface/30 px-3 py-2 font-mono text-[9px] uppercase tracking-wider">
        <Cpu size={10} className="text-cyan-400" />
        <span className="text-ink-soft">ajan kuyruğu:</span>
        <span className="text-cyan-400 font-bold">{activeCount} çalışan</span>
        <span className="text-ink-muted">•</span>
        <span className="text-amber font-bold">{blockedCount} bloke</span>
        <span className="text-ink-muted">•</span>
        <span className="text-emerald-400">{doneCount} biten</span>
      </div>

      {/* Task List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {tasks.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center px-4 py-8 space-y-2">
            <span className="font-display text-lg italic text-ink-muted">Ajanlar Beklemede</span>
            <span className="max-w-[200px] font-mono text-[9px] uppercase tracking-[0.16em] text-ink-faint leading-normal">
              Codex veya AGY ajanı tetiklendiğinde burada canlı akış başlayacak.
            </span>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {tasks.map((task) => {
              const cfg = STATUS_CONFIG[task.status] || STATUS_CONFIG.queued;
              const isSelected = selectedTaskId === task.id;

              const isFinished = task.status === "done" || task.status === "error";
              const elapsed = isFinished
                ? task.updated_at - task.created_at
                : Date.now() - task.created_at;

              return (
                <motion.button
                  layoutId={`task-card-${task.id}`}
                  key={task.id}
                  onClick={() => onSelectTask(task.id)}
                  className={`group relative flex w-full flex-col rounded-lg p-3 text-left transition-all hud-card ${
                    isSelected
                      ? "border-cyan-400/50 bg-surface-raised shadow-[0_0_12px_rgba(0,229,255,0.08)] teal-glow"
                      : "border-hairline/60 bg-surface/20"
                  }`}
                >
                  {/* Outer corner ticks */}
                  <div className="absolute inset-0 pointer-events-none hud-card-corner-top hud-card-corner-bottom" />

                  {/* Top line: Target & Status Badge */}
                  <div className="flex w-full items-center justify-between font-mono text-[8.5px] z-10">
                    <div className="flex items-center gap-1.5">
                      <span className="rounded border border-hairline/80 bg-surface-sunken px-1.5 py-0.5 text-ink-soft uppercase tracking-wider font-semibold">
                        {TARGET_LABELS[task.target]}
                      </span>
                      <span className="text-ink-faint">#{task.id}</span>
                    </div>

                    <div
                      className={`flex items-center gap-1 rounded-full border px-2 py-0.5 font-bold uppercase tracking-[0.06em] text-[8px] ${cfg.text} ${cfg.border} ${cfg.bg}`}
                    >
                      {cfg.icon}
                      <span>{cfg.label}</span>
                    </div>
                  </div>

                  {/* Title & Detail */}
                  <div className="mt-2.5 flex flex-col gap-0.5 z-10">
                    <span className="font-mono text-[11px] font-medium tracking-tight text-ink group-hover:text-cyan-400 transition-colors">
                      {task.title}
                    </span>
                    {task.detail && (
                      <span className="font-mono text-[9px] text-ink-muted truncate">
                        {task.detail}
                      </span>
                    )}
                  </div>

                  {/* Bottom Line: Timestamp & Duration */}
                  <div className="mt-3 flex items-center justify-between border-t border-hairline/40 pt-2 font-mono text-[8px] text-ink-faint z-10">
                    <span>
                      {new Date(task.created_at).toLocaleTimeString("tr-TR", {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </span>
                    <span className="tabular-nums uppercase tracking-wide">
                      süre: {formatDuration(elapsed)}
                    </span>
                  </div>
                </motion.button>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
