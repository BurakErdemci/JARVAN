import { Settings, Wifi, WifiOff } from "lucide-react";

interface Props {
  connected: boolean;
}

export function StatusBar({ connected }: Props) {
  return (
    <div className="flex h-[22px] items-center justify-between border-t border-hairline bg-surface-sunken/60 px-3 font-mono text-[9px] uppercase tracking-[0.12em]">
      <div className="flex items-center gap-1.5">
        {connected ? (
          <>
            <Wifi size={9} className="text-emerald-400" strokeWidth={2.5} />
            <span className="text-ink-muted">127.0.0.1:8765</span>
          </>
        ) : (
          <>
            <WifiOff size={9} className="text-red-400" strokeWidth={2.5} />
            <span className="text-red-400">bağlantı yok</span>
          </>
        )}
      </div>
      <button
        className="flex items-center gap-1 text-ink-muted transition-colors hover:text-ink-soft"
        title="Ayarlar"
      >
        <span>ayarlar</span>
        <Settings size={9} strokeWidth={2} />
      </button>
    </div>
  );
}
