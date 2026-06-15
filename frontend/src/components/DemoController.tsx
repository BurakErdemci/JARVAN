import { useState } from "react";
import { Sparkles, X, Activity, Play, Code, AlertTriangle, AlertCircle, MessageSquare } from "lucide-react";
import type { TaskStatus } from "../types";

interface Props {
  mockMode: boolean;
  setMockMode: (val: boolean) => void;
  simulateTask: (type: "done" | "blocked" | "error") => void;
  onSendMessage: (text: string) => void;
}

export function DemoController({ mockMode, setMockMode, simulateTask, onSendMessage }: Props) {
  const [collapsed, setCollapsed] = useState(true);

  if (!mockMode) {
    return (
      <div className="flex justify-center p-2">
        <button
          onClick={() => setMockMode(true)}
          className="flex items-center gap-1.5 rounded-full border border-amber/30 bg-amber/5 px-3 py-1 font-mono text-[9px] uppercase tracking-wider text-amber transition-all hover:bg-amber/15 hover:border-amber/60 amber-glow-sm"
        >
          <Sparkles size={9} className="animate-pulse" />
          <span>simülasyon modunu aç</span>
        </button>
      </div>
    );
  }

  return (
    <div className="mx-4 mb-2 overflow-hidden rounded-xl border border-dashed border-amber/40 bg-surface-sunken/90 p-2.5 backdrop-blur-md transition-all shadow-[0_0_15px_rgba(255,138,61,0.06)]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-wider text-amber font-semibold">
          <Activity size={11} className="animate-pulse" />
          <span>simülasyon kontrol paneli</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="font-mono text-[8px] uppercase tracking-wider text-ink-muted hover:text-ink-soft"
          >
            {collapsed ? "[ göster ]" : "[ gizle ]"}
          </button>
          <button
            onClick={() => setMockMode(false)}
            className="grid h-4.5 w-4.5 place-items-center rounded-md hover:bg-surface text-ink-muted hover:text-red-400"
            title="Demo Kapat"
          >
            <X size={10} />
          </button>
        </div>
      </div>

      {/* Buttons */}
      {!collapsed && (
        <div className="mt-3 grid grid-cols-2 gap-2 font-mono text-[9px]">
          <button
            onClick={() => simulateTask("done")}
            className="flex items-center justify-center gap-1.5 rounded-lg border border-hairline bg-surface/50 p-2 text-ink-soft transition-all hover:border-emerald-500/35 hover:bg-emerald-500/5 hover:text-emerald-400"
          >
            <Code size={10} />
            <span>Simüle: Başarılı Görev</span>
          </button>

          <button
            onClick={() => simulateTask("blocked")}
            className="flex items-center justify-center gap-1.5 rounded-lg border border-hairline bg-surface/50 p-2 text-ink-soft transition-all hover:border-amber/45 hover:bg-amber/5 hover:text-amber"
          >
            <AlertTriangle size={10} />
            <span>Simüle: Bloke Görev</span>
          </button>

          <button
            onClick={() => simulateTask("error")}
            className="flex items-center justify-center gap-1.5 rounded-lg border border-hairline bg-surface/50 p-2 text-ink-soft transition-all hover:border-red-500/35 hover:bg-red-500/5 hover:text-red-400"
          >
            <AlertCircle size={10} />
            <span>Simüle: Hatalı Görev</span>
          </button>

          <button
            onClick={() => onSendMessage("Merhaba Jarvan, nasılsın?")}
            className="flex items-center justify-center gap-1.5 rounded-lg border border-hairline bg-surface/50 p-2 text-ink-soft transition-all hover:border-amber-deep/45 hover:bg-amber/5 hover:text-amber"
          >
            <MessageSquare size={10} />
            <span>Simüle: Sesli Konuşma</span>
          </button>
        </div>
      )}
    </div>
  );
}
