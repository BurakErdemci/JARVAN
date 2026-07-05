import { useEffect, useState } from "react";
import { Server, Activity, Database, Cpu, HardDrive, Compass, Mic2 } from "lucide-react";
import type { ModeName, SystemMetrics } from "../types";

interface Props {
  connected: boolean;
  mockMode: boolean;
  mode: ModeName;
  metrics: SystemMetrics | null;
}

function Meter({
  icon, label, value, max, display, color,
}: {
  icon: React.ReactNode; label: string; value: number; max: number; display: string; color: string;
}) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-[10.5px] font-semibold text-ink-soft">
        <span className="flex items-center gap-1.5">{icon} {label}</span>
        <span className="tabular-nums" style={{ color }}>{display}</span>
      </div>
      <div className="h-1.5 w-full bg-surface-sunken rounded-full overflow-hidden border border-hairline/60">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color, boxShadow: `0 0 6px ${color}` }}
        />
      </div>
    </div>
  );
}

export function SystemDiagnostics({ connected, mockMode, mode, metrics }: Props) {
  const [radarDots, setRadarDots] = useState<{ x: number; y: number; opacity: number; id: number }[]>([]);

  // Decorative radar sweep
  useEffect(() => {
    const spawn = setInterval(() => {
      if (Math.random() > 0.4) {
        const angle = Math.random() * Math.PI * 2;
        const radius = 15 + Math.random() * 25;
        setRadarDots((prev) => [
          ...prev.slice(-4),
          { x: 50 + Math.cos(angle) * radius, y: 50 + Math.sin(angle) * radius, opacity: 1, id: Date.now() + Math.random() },
        ]);
      }
    }, 2000);
    const fade = setInterval(() => {
      setRadarDots((prev) => prev.map((d) => ({ ...d, opacity: d.opacity - 0.15 })).filter((d) => d.opacity > 0));
    }, 300);
    return () => { clearInterval(spawn); clearInterval(fade); };
  }, []);

  const showActive = connected || mockMode;
  const cpu = metrics?.cpu ?? 0;
  const ramUsed = metrics?.ram_used ?? 0;
  const ramTotal = metrics?.ram_total ?? 0;
  const ramPct = metrics?.ram_pct ?? 0;
  const vramUsed = metrics?.vram_used ?? 0;
  const vramTotal = metrics?.vram_total || 12;
  const modelLoaded = !!metrics?.model_loaded;

  // Ollama satırı: yüklü = aktif (yeşil), değil = uykuda (amber) — unload-on-sleep'i gösterir
  const ollamaState = modelLoaded
    ? { dot: "bg-emerald-400 animate-pulse shadow-[0_0_6px_#34d399]", txt: "text-emerald-400", label: "AKTİF" }
    : showActive
    ? { dot: "bg-amber", txt: "text-amber", label: "UYKUDA" }
    : { dot: "bg-ink-muted", txt: "text-ink-muted", label: "BEKLEMEDE" };

  return (
    <div className="flex h-full flex-col overflow-hidden p-3.5 font-mono">
      {/* Title */}
      <div className="flex items-center gap-2 border-b border-hairline pb-2.5 mb-3.5">
        <Activity size={13} className="text-cyan-400" />
        <span className="font-sci text-[11px] font-bold uppercase tracking-[0.25em] text-ink">
          Sistem Telemetrisi
        </span>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto pr-1">
        {/* Connections */}
        <div className="hud-card hud-card-corner-top hud-card-corner-bottom rounded-lg p-3.5 space-y-3">
          <span className="font-sci text-[9.5px] uppercase tracking-[0.2em] text-ink-muted block">
            Bağlantı Durumları
          </span>

          <div className="flex items-center justify-between text-[11px]">
            <div className="flex items-center gap-2 text-ink-soft">
              <Server size={12} className="text-cyan-400" /><span>Gateway (WebSocket)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-400 animate-pulse shadow-[0_0_6px_#34d399]" : "bg-red-400"}`} />
              <span className={connected ? "text-emerald-400" : "text-red-400"}>{connected ? "ON" : "OFF"}</span>
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px]">
            <div className="flex items-center gap-2 text-ink-soft">
              <Database size={12} className="text-purple-400" /><span>Gemma 12B (Ollama)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${ollamaState.dot}`} />
              <span className={ollamaState.txt}>{ollamaState.label}</span>
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px]">
            <div className="flex items-center gap-2 text-ink-soft">
              <Mic2 size={12} className="text-pink-live" /><span>Whisper + Kokoro</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${showActive ? "bg-emerald-400 animate-pulse shadow-[0_0_6px_#34d399]" : "bg-ink-muted"}`} />
              <span className={showActive ? "text-emerald-400" : "text-ink-muted"}>{showActive ? "HAZIR" : "BEKLEMEDE"}</span>
            </div>
          </div>
        </div>

        {/* Radar */}
        <div className="hud-card hud-card-corner-top hud-card-corner-bottom rounded-lg p-3.5 flex flex-col items-center">
          <span className="font-sci text-[9.5px] uppercase tracking-[0.2em] text-ink-muted self-start mb-3">
            Sinyal Tarayıcı
          </span>
          <div className="relative h-28 w-28 border border-cyan-400/25 rounded-full flex items-center justify-center">
            <div className="absolute inset-2 border border-cyan-400/12 rounded-full" />
            <div className="absolute inset-8 border border-cyan-400/8 rounded-full" />
            <div className="absolute left-0 right-0 h-[0.5px] bg-cyan-400/12" />
            <div className="absolute top-0 bottom-0 w-[0.5px] bg-cyan-400/12" />
            <div className="absolute h-full w-full rounded-full overflow-hidden animate-spin-slow origin-center">
              <div className="absolute top-1/2 left-1/2 w-[56px] h-[56px] origin-top-left -translate-y-full"
                style={{ background: "conic-gradient(from 0deg, rgba(0,229,255,0.22) 0deg, transparent 90deg)", transform: "rotate(-90deg)" }} />
            </div>
            {radarDots.map((dot) => (
              <div key={dot.id} className="absolute h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_#00e5ff]"
                style={{ left: `${dot.x}%`, top: `${dot.y}%`, opacity: dot.opacity, transform: "translate(-50%,-50%)" }} />
            ))}
            <div className="absolute h-2 w-2 rounded-full border border-cyan-400 bg-cyan-400/20 animate-pulse shadow-[0_0_4px_#00e5ff]" />
          </div>
        </div>

        {/* Real Resources */}
        <div className="hud-card hud-card-corner-top hud-card-corner-bottom rounded-lg p-3.5 space-y-3.5">
          <span className="font-sci text-[9.5px] uppercase tracking-[0.2em] text-ink-muted block">
            Kaynak Kullanımı {metrics ? "" : "(bekleniyor…)"}
          </span>
          <Meter icon={<Cpu size={11} />} label="CPU" value={cpu} max={100}
            display={`${cpu.toFixed(0)}%`} color="#00e5ff" />
          <Meter icon={<HardDrive size={11} />} label="RAM" value={ramPct} max={100}
            display={`${ramUsed.toFixed(1)} / ${ramTotal.toFixed(0)} GB`} color="#a78bfa" />
          <Meter icon={<Compass size={11} />} label="VRAM (GPU)" value={vramUsed} max={vramTotal}
            display={modelLoaded ? `${vramUsed.toFixed(1)} / ${vramTotal.toFixed(0)} GB` : "boşta"} color="#ff4d8f" />
        </div>

        {/* Environment */}
        <div className="hud-card hud-card-corner-top hud-card-corner-bottom rounded-lg p-3.5 text-[11px] space-y-2 text-ink-soft leading-relaxed">
          <span className="font-sci text-[9.5px] uppercase tracking-[0.2em] text-ink-muted block mb-1">
            Ortam Parametreleri
          </span>
          <div><span className="text-ink-muted">AKTİF MOD:</span> <span className="text-cyan-400 font-bold uppercase">{mode}</span></div>
          <div><span className="text-ink-muted">AĞ ADRESİ:</span> <span className="text-ink">127.0.0.1:8765</span></div>
          <div className="truncate"><span className="text-ink-muted">DURUM:</span> <span className="text-emerald-400">{showActive ? "ÇEVRİMİÇİ (LOCAL)" : "ÇEVRİMDIŞI"}</span></div>
        </div>
      </div>
    </div>
  );
}
