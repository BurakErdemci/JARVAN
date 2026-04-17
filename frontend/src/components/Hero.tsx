import { motion } from "framer-motion";
import type { ModeName, PipelineState } from "../types";
import { Waveform } from "./Waveform";
import { ModeBadge } from "./ModeBadge";
import { StateLabel } from "./StateLabel";

interface Props {
  state: PipelineState;
  mode: ModeName;
  live: boolean;
}

export function Hero({ state, mode, live }: Props) {
  const accent = live ? "pink" : "amber";

  return (
    <div className="relative px-4 pt-4 pb-3">
      {/* Ambient backdrop */}
      <div
        className="absolute inset-x-0 top-0 h-40 pointer-events-none"
        style={{
          background:
            accent === "pink"
              ? "radial-gradient(ellipse 70% 60% at 50% 30%, rgba(255,77,143,0.18) 0%, transparent 70%)"
              : "radial-gradient(ellipse 70% 60% at 50% 30%, rgba(255,138,61,0.16) 0%, transparent 70%)",
          transition: "background 0.6s ease",
        }}
      />

      {/* Top row: state label + mode badge */}
      <div className="relative flex items-center justify-between">
        <StateLabel state={state} />
        <ModeBadge mode={mode} />
      </div>

      {/* Visualizer container */}
      <div className="relative mt-3 h-[96px] overflow-hidden rounded-xl border border-hairline bg-surface/40 px-3 py-3">
        {/* Corner tick marks */}
        <div className="absolute inset-0 pointer-events-none">
          {["top-1 left-1", "top-1 right-1", "bottom-1 left-1", "bottom-1 right-1"].map(
            (pos) => (
              <span
                key={pos}
                className={`absolute ${pos} h-[5px] w-[5px] border-ink-faint`}
                style={{
                  borderTopWidth: pos.includes("top") ? "1px" : 0,
                  borderBottomWidth: pos.includes("bottom") ? "1px" : 0,
                  borderLeftWidth: pos.includes("left") ? "1px" : 0,
                  borderRightWidth: pos.includes("right") ? "1px" : 0,
                }}
              />
            )
          )}
        </div>

        <Waveform state={state} accent={accent} />
      </div>

      {/* Brand wordmark overlay — subtle */}
      <div className="relative mt-2 flex items-baseline justify-between gap-3">
        <motion.span
          className="font-display text-[22px] italic leading-none text-ink"
          style={{
            letterSpacing: "-0.02em",
          }}
        >
          Jarvan<span className="text-amber">.</span>
        </motion.span>
        <span className="shrink-0 font-mono text-[8.5px] uppercase tracking-[0.16em] text-ink-faint">
          sesli asistan
        </span>
      </div>
    </div>
  );
}
