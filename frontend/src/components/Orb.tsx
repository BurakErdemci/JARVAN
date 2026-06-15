import { motion } from "framer-motion";
import { MicOff, ShieldAlert } from "lucide-react";
import type { PipelineState } from "../types";

interface Props {
  state: PipelineState;
  accent?: "amber" | "pink";
}

export function Orb({ state, accent = "amber" }: Props) {
  const isMuted = state === "muted";
  const isListening = state === "listening";
  const isTranscribing = state === "transcribing";
  const isResponding = state === "responding";
  const isIdle = state === "idle";

  // JARVIS accent mappings
  const colorHex = isMuted
    ? "#5a5a62"
    : accent === "pink"
    ? "#ff2a85"
    : "#00e5ff"; // Teal by default for tech look!
  const shadowColor = isMuted
    ? "rgba(90, 90, 98, 0.2)"
    : accent === "pink"
    ? "rgba(255, 42, 133, 0.6)"
    : "rgba(0, 229, 255, 0.6)";
  const shadowColorSoft = isMuted
    ? "rgba(90, 90, 98, 0.05)"
    : accent === "pink"
    ? "rgba(255, 42, 133, 0.15)"
    : "rgba(0, 229, 255, 0.12)";

  // Core pulsate configurations
  const coreScale = isMuted ? 0.95 : isListening ? [1, 1.1, 1] : isTranscribing ? [1, 0.96, 1.04, 1] : isResponding ? [1, 1.15, 0.98, 1.08, 1] : [1, 1.04, 1];
  const coreDuration = isListening ? 1.6 : isTranscribing ? 0.7 : isResponding ? 2.2 : 3.5;

  return (
    <div className="relative flex h-[160px] w-[160px] items-center justify-center select-none pointer-events-none">
      
      {/* 1. Muted Overlay */}
      {isMuted && (
        <div className="absolute z-20 flex flex-col items-center justify-center text-red-400/80 animate-pulse">
          <MicOff size={28} className="drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]" />
          <span className="font-mono text-[7px] uppercase tracking-widest mt-1 text-red-400">offline</span>
        </div>
      )}

      {/* 2. Static HUD Bracket Overlays (Sci-Fi corners) */}
      <div className="absolute inset-0 z-10 opacity-45">
        {["top-0 left-0", "top-0 right-0", "bottom-0 left-0", "bottom-0 right-0"].map((pos) => (
          <span
            key={pos}
            className={`absolute ${pos} h-3.5 w-3.5 border-color-hex`}
            style={{
              borderColor: colorHex,
              borderTopWidth: pos.includes("top") ? "1px" : 0,
              borderBottomWidth: pos.includes("bottom") ? "1px" : 0,
              borderLeftWidth: pos.includes("left") ? "1px" : 0,
              borderRightWidth: pos.includes("right") ? "1px" : 0,
            }}
          />
        ))}
      </div>

      {/* 3. Ambient Backlit Glow Circle */}
      <motion.div
        className="absolute h-36 w-36 rounded-full blur-[28px] opacity-75"
        style={{
          background: `radial-gradient(circle, ${shadowColor} 0%, ${shadowColorSoft} 60%, transparent 90%)`,
        }}
        animate={{
          scale: isMuted ? 0.8 : [1, 1.25, 1],
          opacity: isMuted ? 0.15 : [0.65, 0.95, 0.65],
        }}
        transition={{
          duration: coreDuration,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />

      {/* 4. Outer HUD Ring 1 - Dashed Slow-Orbit */}
      <motion.svg
        className="absolute h-[152px] w-[152px] z-10 opacity-35"
        viewBox="0 0 100 100"
        animate={{ rotate: 360 }}
        transition={{
          duration: isIdle ? 30 : isListening ? 12 : isTranscribing ? 4 : 15,
          repeat: Infinity,
          ease: "linear",
        }}
      >
        <circle
          cx="50"
          cy="50"
          r="47"
          fill="none"
          stroke={colorHex}
          strokeWidth="0.6"
          strokeDasharray="2 12 18 12"
        />
      </motion.svg>

      {/* 5. Outer HUD Ring 2 - Reverse Fast-Orbit */}
      <motion.svg
        className="absolute h-[138px] w-[138px] z-10 opacity-45"
        viewBox="0 0 100 100"
        animate={{ rotate: -360 }}
        transition={{
          duration: isListening ? 8 : isTranscribing ? 2.5 : 18,
          repeat: Infinity,
          ease: "linear",
        }}
      >
        <circle
          cx="50"
          cy="50"
          r="46"
          fill="none"
          stroke={colorHex}
          strokeWidth="0.8"
          strokeDasharray="45 15 5 15"
        />
      </motion.svg>

      {/* 6. Concentric Nested Tech Ring 3 (Thin target mesh) */}
      <motion.svg
        className="absolute h-[120px] w-[120px] z-10 opacity-25"
        viewBox="0 0 100 100"
        animate={{ rotate: 180 }}
        transition={{
          duration: 40,
          repeat: Infinity,
          ease: "linear",
        }}
      >
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke={colorHex}
          strokeWidth="0.3"
          strokeDasharray="4 8"
        />
        {/* Tiny Crosshair ticks inside ring */}
        {["0", "90", "180", "270"].map((rot) => (
          <line
            key={rot}
            x1="50"
            y1="5"
            x2="50"
            y2="10"
            stroke={colorHex}
            strokeWidth="0.8"
            transform={`rotate(${rot} 50 50)`}
          />
        ))}
      </motion.svg>

      {/* 7. Soundwave Expanding Ripple rings when responding */}
      {isResponding && (
        <>
          {[1.0, 1.4, 1.8].map((delay, idx) => (
            <motion.div
              key={idx}
              className="absolute rounded-full border border-dashed"
              style={{ borderColor: colorHex, width: 80, height: 80 }}
              initial={{ scale: 0.8, opacity: 0.8 }}
              animate={{ scale: 2.2, opacity: 0 }}
              transition={{
                duration: 2.2,
                repeat: Infinity,
                delay: idx * 0.4,
                ease: "easeOut",
              }}
            />
          ))}
        </>
      )}

      {/* 8. Glowing Core Brain */}
      <motion.div
        className={`z-10 h-20 w-20 rounded-full border shadow-inner flex items-center justify-center transition-all ${
          isMuted
            ? "border-hairline bg-surface-sunken opacity-30"
            : accent === "pink"
            ? "border-pink-glow bg-gradient-to-tr from-pink-live/25 to-pink-glow/45 pink-glow"
            : "border-teal-glow bg-gradient-to-tr from-cyan-600/30 to-cyan-400/50 teal-glow"
        }`}
        animate={{ scale: coreScale }}
        transition={{
          duration: coreDuration,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      >
        {/* Specular glass reflection */}
        {!isMuted && (
          <div className="absolute top-[26%] left-[26%] h-6 w-6 rounded-full bg-white/25 blur-[1.5px] pointer-events-none" />
        )}

        {/* Center Target Core crosshair (+) */}
        {!isMuted && (
          <div className="relative h-2 w-2">
            <span className="absolute top-1/2 left-0 right-0 h-[1px] bg-white/60 -translate-y-1/2" />
            <span className="absolute left-1/2 top-0 bottom-0 w-[1px] bg-white/60 -translate-x-1/2" />
          </div>
        )}
      </motion.div>

      {/* 9. Floating scanner bar when transcribing */}
      {isTranscribing && (
        <motion.div
          className="absolute z-20 w-24 h-[1.5px] bg-white pointer-events-none shadow-[0_0_12px_#fff]"
          animate={{ y: [-48, 48, -48] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
        />
      )}
    </div>
  );
}
