import { motion } from "framer-motion";
import type { ModeName, PipelineState } from "../types";
import { Waveform } from "./Waveform";
import { ModeBadge } from "./ModeBadge";
import { StateLabel } from "./StateLabel";
import { Orb } from "./Orb";

interface Props {
  state: PipelineState;
  mode: ModeName;
  live: boolean;
  lastUserMsg?: string;
  lastJarvanMsg?: string;
}

export function Hero({ state, mode, live, lastUserMsg = "", lastJarvanMsg = "" }: Props) {
  const accent = live ? "pink" : "amber";

  // Compute live subtitle captions
  const getSubtitle = () => {
    if (state === "muted") {
      return "SİSTEM SES ALICILARI DEVRE DIŞI BIRAKILDI.";
    }
    if (state === "transcribing") {
      return lastUserMsg ? `"${lastUserMsg.toUpperCase()}"` : "ANALİZ EDİLİYOR...";
    }
    if (state === "responding") {
      return lastJarvanMsg ? `JARVAN: "${lastJarvanMsg}"` : "CEVAP HAZIRLANIYOR...";
    }
    if (state === "listening") {
      return "SİSTEM DİNLEMEDE. UYANDIRMA KELİMESİ: 'UYAN JARVAN'";
    }
    return "ASİSTAN HAZIR. BİR EMİR BEKLENİYOR.";
  };

  return (
    <div className="relative px-4 pt-3 pb-2 flex flex-col items-center">
      {/* Ambient backdrop glow */}
      <div
        className="absolute inset-x-0 top-0 h-56 pointer-events-none"
        style={{
          background:
            state === "muted"
              ? "radial-gradient(ellipse 80% 60% at 50% 30%, rgba(239,68,68,0.04) 0%, transparent 75%)"
              : accent === "pink"
              ? "radial-gradient(ellipse 80% 60% at 50% 30%, rgba(255,42,133,0.12) 0%, transparent 75%)"
              : "radial-gradient(ellipse 80% 60% at 50% 30%, rgba(0,229,255,0.08) 0%, transparent 75%)",
          transition: "background 0.8s ease",
        }}
      />

      {/* Top row: state label + mode badge */}
      <div className="relative w-full flex items-center justify-between z-10 mb-2">
        <StateLabel state={state} />
        <ModeBadge mode={mode} />
      </div>

      {/* Main Core HUD Panel (Scaled up) */}
      <div className="relative w-full flex flex-col items-center justify-center rounded-xl border border-hairline/60 bg-surface/20 px-6 py-6 shadow-sm hud-card">
        {/* Corner tick marks */}
        <div className="absolute inset-0 pointer-events-none hud-card-corner-top hud-card-corner-bottom" />

        {/* Central Holographic Orb */}
        <div className="my-2">
          <Orb state={state} accent={accent} />
        </div>

        {/* Audio Waveform analyzer */}
        <div className="mt-4 h-6 w-full opacity-75">
          <Waveform state={state} accent={accent} />
        </div>

        {/* Live Subtitle Captions box (Typewriter style telemetry feedback) */}
        <div className="mt-4 w-full border-t border-hairline/50 pt-3 text-center">
          <div className="font-mono text-[7.5px] uppercase tracking-[0.2em] text-ink-faint mb-1.5 flex items-center justify-center gap-1">
            <span className={`h-1 w-1 rounded-full ${state === 'muted' ? 'bg-red-500' : 'bg-cyan-400 animate-pulse'}`} />
            <span>ses telemetri altyazısı</span>
          </div>
          <div className="h-9 flex items-center justify-center px-2">
            <motion.p
              key={getSubtitle()}
              initial={{ opacity: 0, y: 3 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className={`font-mono text-[10px] uppercase tracking-wider leading-relaxed select-text ${
                state === "muted"
                  ? "text-red-400/70"
                  : state === "responding"
                  ? "text-cyan-400"
                  : "text-ink-soft"
              }`}
            >
              {getSubtitle()}
            </motion.p>
          </div>
        </div>
      </div>
    </div>
  );
}
