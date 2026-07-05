import { Cpu, MemoryStick, Layers, Radio, Eye, MicOff } from "lucide-react";
import { Reactor } from "./Reactor";
import type { BackendStatus, ModeName, PipelineState, SystemMetrics } from "../types";

interface Props {
  state: PipelineState;
  status: BackendStatus;
  mode: ModeName;
  metrics: SystemMetrics | null;
  connected: boolean;
  onToggleLive: (v: boolean) => void;
  onToggleProactive: (v: boolean) => void;
  onToggleMute: (v: boolean) => void;
}

function Gauge({
  icon, label, value, max, display, hot,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  max: number;
  display: string;
  hot?: boolean;
}) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  const color = hot ? "#FF7A2F" : pct > 85 ? "#FF4D5E" : "#43E5C9";
  return (
    <div>
      <div className="flex items-center justify-between text-2xs">
        <span className="flex items-center gap-1.5 font-display tracking-hud text-ink-muted">
          {icon} {label}
        </span>
        <span className="font-mono tabular-nums" style={{ color }}>{display}</span>
      </div>
      <div className="mt-1 flex h-[5px] gap-[2px]" role="img" aria-label={`${label} ${Math.round(pct)}%`}>
        {Array.from({ length: 20 }, (_, i) => (
          <span
            key={i}
            className="flex-1"
            style={{
              background: (i + 0.5) / 20 <= pct / 100 ? color : "#16233A",
              opacity: (i + 0.5) / 20 <= pct / 100 ? 0.9 : 0.6,
              transition: "background 500ms",
            }}
          />
        ))}
      </div>
    </div>
  );
}

function Switch({
  icon, label, caption, enabled, disabled, danger, onToggle,
}: {
  icon: React.ReactNode;
  label: string;
  caption: string;
  enabled: boolean;
  disabled?: boolean;
  danger?: boolean;
  onToggle: (v: boolean) => void;
}) {
  const on = enabled;
  const color = danger ? "#FF4D5E" : "#43E5C9";
  return (
    <button
      onClick={() => onToggle(!enabled)}
      disabled={disabled}
      aria-pressed={on}
      className="chamfer-sm group flex w-full items-center gap-2.5 border border-steel bg-hull px-2.5 py-2 text-left transition-colors hover:border-steel-bright disabled:opacity-40"
    >
      <span style={{ color: on ? color : "#46586F" }}>{icon}</span>
      <span className="min-w-0 flex-1">
        <span className="block font-display text-2xs font-medium tracking-hud text-ink-soft">
          {label}
        </span>
        <span className="block truncate font-mono text-3xs text-ink-ghost">{caption}</span>
      </span>
      {/* durum pimi */}
      <span
        className="h-3.5 w-[18px] shrink-0 border"
        style={{
          borderColor: on ? color : "#24374F",
          background: on ? color : "transparent",
          boxShadow: on ? `0 0 8px ${color}66` : "none",
          transition: "all 250ms",
        }}
      />
    </button>
  );
}

const MODE_LABEL: Record<ModeName, string> = {
  unreal: "UNREAL",
  unity: "UNITY",
  code: "KOD",
  default: "GENEL",
};

export function CoreColumn({
  state, status, mode, metrics, connected,
  onToggleLive, onToggleProactive, onToggleMute,
}: Props) {
  const modelOn = !!metrics?.model_loaded;
  return (
    <aside className="boot-1 flex h-full w-[236px] shrink-0 flex-col border-r border-steel bg-hull/40">
      {/* Reaktör — imza öğe */}
      <div className="flex flex-col items-center px-3 pb-1 pt-4">
        <Reactor state={state} />
      </div>

      {/* Vitals */}
      <div className="space-y-3 border-t border-steel px-3.5 py-3.5">
        <div className="font-display text-3xs font-semibold tracking-hud text-ink-ghost">
          SİSTEM VERİLERİ
        </div>
        <Gauge
          icon={<Cpu size={11} />}
          label="CPU"
          value={metrics?.cpu ?? 0}
          max={100}
          display={`%${Math.round(metrics?.cpu ?? 0)}`}
        />
        <Gauge
          icon={<MemoryStick size={11} />}
          label="RAM"
          value={metrics?.ram_used ?? 0}
          max={metrics?.ram_total || 1}
          display={`${(metrics?.ram_used ?? 0).toFixed(1)} GB`}
        />
        <Gauge
          icon={<Layers size={11} />}
          label="VRAM"
          value={metrics?.vram_used ?? 0}
          max={metrics?.vram_total || 12}
          display={`${(metrics?.vram_used ?? 0).toFixed(1)} GB`}
          hot={modelOn}
        />
        {/* Beyin durumu */}
        <div className="flex items-center justify-between border border-steel bg-hull-sunken px-2.5 py-1.5">
          <span className="font-display text-3xs tracking-hud text-ink-muted">GEMMA ÇEKİRDEĞİ</span>
          <span
            className="flex items-center gap-1.5 font-mono text-3xs"
            style={{ color: modelOn ? "#FF7A2F" : "#46586F" }}
          >
            <span
              className="h-1.5 w-1.5"
              style={{
                background: modelOn ? "#FF7A2F" : "#46586F",
                boxShadow: modelOn ? "0 0 6px #FF7A2F" : "none",
              }}
            />
            {modelOn ? "YÜKLÜ" : "UYKUDA"}
          </span>
        </div>
      </div>

      {/* Modlar / anahtarlar */}
      <div className="space-y-2 border-t border-steel px-3.5 py-3.5">
        <div className="font-display text-3xs font-semibold tracking-hud text-ink-ghost">
          KONTROLLER
        </div>
        <Switch
          icon={<Radio size={13} />}
          label="CANLI SES"
          caption="whisper + gemma + kokoro"
          enabled={status.live}
          disabled={!connected}
          onToggle={onToggleLive}
        />
        <Switch
          icon={<Eye size={13} />}
          label="PROAKTİF BAKIŞ"
          caption="ekranı periyodik analiz et"
          enabled={status.proactive}
          disabled={!connected}
          onToggle={onToggleProactive}
        />
        <Switch
          icon={<MicOff size={13} />}
          label="SESSİZE AL"
          caption="mikrofonu kapat (M)"
          enabled={status.muted}
          disabled={!connected}
          danger
          onToggle={onToggleMute}
        />
      </div>

      {/* Aktif mod rozeti — alta sabit */}
      <div className="mt-auto border-t border-steel px-3.5 py-2.5">
        <div className="flex items-center justify-between">
          <span className="font-display text-3xs tracking-hud text-ink-ghost">AKTİF MOD</span>
          <span className="font-display text-2xs font-semibold tracking-hud text-mode-code">
            {MODE_LABEL[mode]}
          </span>
        </div>
      </div>
    </aside>
  );
}
