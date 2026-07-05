import { useState } from "react";
import { ChevronDown, ChevronRight, Trash2 } from "lucide-react";
import type { TaskInfo, TaskStatus, TaskTarget } from "../types";

interface Props {
  tasks: TaskInfo[];
  onClear: () => void;
}

const AGENT: Record<TaskTarget, { label: string; color: string }> = {
  codex: { label: "CDX", color: "#A78BFA" },
  agy: { label: "AGY", color: "#43E5C9" },
  claude: { label: "CLD", color: "#E8C468" },
  gemma: { label: "GMA", color: "#FF7A2F" },
  local: { label: "LOC", color: "#7C8DA6" },
};

const STATUS: Record<TaskStatus, { label: string; color: string }> = {
  queued: { label: "SIRADA", color: "#7C8DA6" },
  running: { label: "ÇALIŞIYOR", color: "#43E5C9" },
  blocked: { label: "TAKILDI", color: "#E8C468" },
  done: { label: "TAMAM", color: "#43E5C9" },
  error: { label: "HATA", color: "#FF4D5E" },
};

function fmtClock(ts: number): string {
  return new Date(ts).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function elapsed(t: TaskInfo): string {
  const end = t.status === "running" || t.status === "queued" ? Date.now() : t.updated_at;
  const s = Math.max(0, Math.round((end - t.created_at) / 1000));
  return s < 60 ? `${s}sn` : `${Math.floor(s / 60)}dk ${s % 60}sn`;
}

function TaskCard({ t }: { t: TaskInfo }) {
  const [open, setOpen] = useState(t.status === "running");
  const agent = AGENT[t.target] ?? AGENT.local;
  const st = STATUS[t.status] ?? STATUS.queued;
  const live = t.status === "running" || t.status === "queued";

  return (
    <article
      className={`chamfer-sm border bg-hull-raised ${live ? "edge-running" : ""}`}
      style={{ borderColor: live ? agent.color : "#16233A" }}
    >
      {/* Kart başlığı */}
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-2.5 py-2 text-left"
        aria-expanded={open}
      >
        {/* Ajan rozeti */}
        <span
          className="shrink-0 border px-1 py-0.5 font-display text-3xs font-semibold tracking-hud"
          style={{ color: agent.color, borderColor: agent.color }}
        >
          {agent.label}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-2xs font-medium text-ink">{t.title}</span>
          <span className="block truncate font-mono text-3xs text-ink-ghost">
            {t.detail || "—"}
          </span>
        </span>
        <span className="shrink-0 text-right">
          <span className="block font-display text-3xs font-semibold tracking-hud" style={{ color: st.color }}>
            {st.label}
          </span>
          <span className="block font-mono text-3xs tabular-nums text-ink-ghost">{elapsed(t)}</span>
        </span>
        <span className="shrink-0 text-ink-ghost">
          {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </span>
      </button>

      {/* Detay: adım telemetrisi + sonuç */}
      {open && (
        <div className="border-t border-steel px-2.5 py-2">
          {(t.steps?.length ?? 0) > 0 && (
            <ol className="space-y-1">
              {t.steps!.map((s, i) => (
                <li key={i} className="flex gap-2 font-mono text-3xs leading-relaxed">
                  <span className="shrink-0 tabular-nums text-ink-ghost">{fmtClock(s.ts)}</span>
                  <span className="text-ink-muted">{s.text}</span>
                </li>
              ))}
            </ol>
          )}
          {t.error && (
            <div className="selectable mt-2 border-l-2 border-flare bg-flare/5 px-2 py-1.5 font-mono text-3xs leading-relaxed text-flare">
              {t.error}
            </div>
          )}
          {t.result && (
            <pre className="selectable mt-2 max-h-52 overflow-y-auto whitespace-pre-wrap border border-steel bg-hull-sunken px-2 py-1.5 font-mono text-3xs leading-relaxed text-ink-soft">
              {t.result}
            </pre>
          )}
        </div>
      )}
    </article>
  );
}

/**
 * GÖREV MATRİSİ — ajan filosunun canlı panosu.
 * Her kart bir arka plan görevi: hangi beyin (CDX/AGY/CLD), durum, geçen süre;
 * açınca adım adım telemetri + sonuç. Ayrı sayfa yok — detay satır içi.
 */
export function TaskMatrix({ tasks, onClear }: Props) {
  const active = tasks.filter((t) => t.status === "running" || t.status === "queued").length;
  const sorted = [...tasks].sort((a, b) => b.created_at - a.created_at);

  return (
    <aside className="boot-3 flex h-full w-[330px] shrink-0 flex-col border-l border-steel bg-hull/40">
      <div className="flex items-center justify-between border-b border-steel px-3.5 py-2">
        <div className="flex items-baseline gap-2">
          <h2 className="font-display text-2xs font-semibold tracking-hud text-ink-soft">
            GÖREV MATRİSİ
          </h2>
          {active > 0 && (
            <span className="font-mono text-3xs tabular-nums text-coolant">{active} aktif</span>
          )}
        </div>
        {tasks.length > 0 && (
          <button
            onClick={onClear}
            title="Biten görevleri temizle"
            className="p-1 text-ink-ghost transition-colors hover:text-flare"
          >
            <Trash2 size={13} />
          </button>
        )}
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto px-3 py-3">
        {sorted.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-1 text-center">
            <div className="font-display text-2xs tracking-hud text-ink-ghost">FİLO BOŞTA</div>
            <div className="max-w-[200px] font-mono text-3xs leading-relaxed text-ink-ghost">
              ağır bir iş verdiğinde codex / agy / claude görevleri burada canlı akar
            </div>
          </div>
        ) : (
          sorted.map((t) => <TaskCard key={t.id} t={t} />)
        )}
      </div>
    </aside>
  );
}
