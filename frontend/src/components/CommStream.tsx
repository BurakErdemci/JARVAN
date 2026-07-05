import { useEffect, useMemo, useRef } from "react";
import { Trash2 } from "lucide-react";
import type { LogEntry } from "../types";

interface Props {
  logs: LogEntry[];
  onClear: () => void;
}

function fmtTime(ts: number): string {
  return new Date(ts).toLocaleTimeString("tr-TR", {
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

/** [TOOL] / [tool sonuç] satırlarını telemetri olarak ayrıştır */
function isTelemetry(l: LogEntry): boolean {
  return l.level === "system" && /^\[.*\]|^\[tool/i.test(l.text.trim());
}

function UserFrame({ l }: { l: LogEntry }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[78%]">
        <div className="mb-0.5 flex items-baseline justify-end gap-2">
          <span className="font-mono text-3xs text-ink-ghost">{fmtTime(l.timestamp)}</span>
          <span className="font-display text-3xs font-semibold tracking-hud text-coolant">SEN</span>
        </div>
        <div className="chamfer-sm selectable border border-coolant-dim/60 bg-coolant-ghost px-3 py-2 text-[13px] leading-relaxed text-ink">
          {l.text}
        </div>
      </div>
    </div>
  );
}

function JarvanFrame({ l }: { l: LogEntry }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[78%]">
        <div className="mb-0.5 flex items-baseline gap-2">
          <span className="font-display text-3xs font-semibold tracking-hud text-plasma">JARVAN</span>
          <span className="font-mono text-3xs text-ink-ghost">{fmtTime(l.timestamp)}</span>
          {l.provider && (
            <span className="font-mono text-3xs uppercase text-ink-ghost">· {l.provider}</span>
          )}
        </div>
        <div className="chamfer-sm selectable border border-plasma-dim/60 bg-plasma-ghost px-3 py-2 text-[13px] leading-relaxed text-ink">
          {l.text}
        </div>
      </div>
    </div>
  );
}

function SystemLine({ l }: { l: LogEntry }) {
  const err = l.level === "error";
  return (
    <div className="flex justify-center">
      <div
        className={`selectable max-w-[92%] break-all border-l-2 py-0.5 pl-2 pr-1 font-mono text-3xs leading-relaxed ${
          err ? "border-flare text-flare" : "border-steel-bright text-ink-ghost"
        }`}
      >
        {l.text}
      </div>
    </div>
  );
}

/**
 * İLETİŞİM KAYDI — konuşma-merkezli merkez panel.
 * SEN = soğuk çerçeve (makineye giden), JARVAN = sıcak çerçeve (makineden gelen),
 * telemetri (tool çağrıları/sistem) kenar çizgili ince mono satır.
 */
export function CommStream({ logs, onClear }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const count = useMemo(() => logs.filter((l) => l.level !== "system").length, [logs]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [logs.length]);

  return (
    <section className="flex min-h-0 flex-1 flex-col">
      {/* Panel başlığı */}
      <div className="flex items-center justify-between border-b border-steel px-4 py-2">
        <div className="flex items-baseline gap-2">
          <h2 className="font-display text-2xs font-semibold tracking-hud text-ink-soft">
            İLETİŞİM KAYDI
          </h2>
          <span className="font-mono text-3xs tabular-nums text-ink-ghost">
            {String(count).padStart(3, "0")}
          </span>
        </div>
        <button
          onClick={onClear}
          title="Kaydı temizle"
          className="p-1 text-ink-ghost transition-colors hover:text-flare"
        >
          <Trash2 size={13} />
        </button>
      </div>

      {/* Akış */}
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {logs.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-1 text-center">
            <div className="font-display text-2xs tracking-hud text-ink-ghost">KAYIT BOŞ</div>
            <div className="font-mono text-3xs text-ink-ghost">
              konuş ya da aşağıya komut yaz — akış burada görünür
            </div>
          </div>
        )}
        {logs.map((l) =>
          l.level === "user" ? (
            <UserFrame key={l.id} l={l} />
          ) : l.level === "jarvan" ? (
            <JarvanFrame key={l.id} l={l} />
          ) : isTelemetry(l) || l.level === "system" || l.level === "error" ? (
            <SystemLine key={l.id} l={l} />
          ) : null
        )}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
