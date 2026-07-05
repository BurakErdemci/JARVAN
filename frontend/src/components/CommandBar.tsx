import { useEffect, useState } from "react";
import { Pin, Minus, X } from "lucide-react";

interface Props {
  connected: boolean;
}

/** Üst komuta çubuğu — sürüklenebilir başlık, saat, hat durumu, pencere kontrolleri. */
export function CommandBar({ connected }: Props) {
  const [clock, setClock] = useState(() =>
    new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
  );
  const [pinned, setPinned] = useState(false);

  useEffect(() => {
    const t = setInterval(() => {
      setClock(new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    }, 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <header className="drag-region flex h-9 shrink-0 items-center gap-3 border-b border-steel bg-hull px-3">
      {/* Kimlik */}
      <div className="flex items-center gap-2">
        <span className="h-3.5 w-1 bg-plasma" aria-hidden="true" />
        <span className="font-display text-xs font-semibold tracking-hud text-ink">
          JARVAN
        </span>
        <span className="font-display text-3xs tracking-hud text-ink-ghost">KOKPİT · 2090</span>
      </div>

      <div className="flex-1" />

      {/* Saat */}
      <span className="font-mono text-2xs tabular-nums text-ink-muted">{clock}</span>

      {/* Hat durumu */}
      <span className="flex items-center gap-1.5 font-display text-3xs tracking-hud">
        <span
          className="h-1.5 w-1.5"
          style={{
            background: connected ? "#43E5C9" : "#FF4D5E",
            boxShadow: connected ? "0 0 6px #43E5C9" : "0 0 6px #FF4D5E",
          }}
        />
        <span style={{ color: connected ? "#43E5C9" : "#FF4D5E" }}>
          {connected ? "HAT AÇIK" : "HAT KAPALI"}
        </span>
      </span>

      {/* Pencere kontrolleri */}
      <div className="no-drag flex items-center gap-0.5">
        <button
          onClick={async () => {
            const v = await window.jarvan?.toggleAlwaysOnTop?.();
            setPinned(!!v);
          }}
          title={pinned ? "Üstte tutmayı bırak" : "Hep üstte tut"}
          className="p-1.5 transition-colors hover:text-coolant"
          style={{ color: pinned ? "#43E5C9" : "#46586F" }}
        >
          <Pin size={13} />
        </button>
        <button
          onClick={() => window.jarvan?.minimize?.()}
          title="Küçült"
          className="p-1.5 text-ink-ghost transition-colors hover:text-ink"
        >
          <Minus size={13} />
        </button>
        <button
          onClick={() => window.jarvan?.hide?.()}
          title="Tepsiye gizle"
          className="p-1.5 text-ink-ghost transition-colors hover:text-flare"
        >
          <X size={13} />
        </button>
      </div>
    </header>
  );
}
