import type { LogEntry, SystemMetrics } from "../types";

interface Props {
  logs: LogEntry[];
  metrics: SystemMetrics | null;
  mockMode: boolean;
  connected: boolean;
  onEnableMock: () => void;
}

/** Alt durum şeridi — son transkript + çekirdek kimliği. */
export function StatusStrip({ logs, metrics, mockMode, connected, onEnableMock }: Props) {
  const lastUser = [...logs].reverse().find((l) => l.level === "user");

  return (
    <footer className="flex h-7 shrink-0 items-center gap-3 border-t border-steel bg-hull px-3">
      <span className="font-display text-3xs tracking-hud text-ink-ghost">SON KOMUT</span>
      <span className="min-w-0 flex-1 truncate font-mono text-3xs text-ink-muted">
        {lastUser ? `"${lastUser.text}"` : "—"}
      </span>

      {!connected && !mockMode && (
        <button
          onClick={onEnableMock}
          className="no-drag font-display text-3xs tracking-hud text-plasma transition-colors hover:text-ink"
        >
          SİMÜLASYONU AÇ
        </button>
      )}
      {mockMode && (
        <span className="font-display text-3xs tracking-hud text-plasma">SİMÜLASYON</span>
      )}

      <span className="font-mono text-3xs text-ink-ghost">
        çekirdek: {metrics?.model_loaded ? "gemma yüklü" : "uykuda"}
      </span>
      <span className="font-display text-3xs tracking-hud text-ink-ghost">JRV·05</span>
    </footer>
  );
}
