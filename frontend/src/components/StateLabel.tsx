import { AnimatePresence, motion } from "framer-motion";
import type { PipelineState } from "../types";

interface Props {
  state: PipelineState;
}

const LABELS: Record<PipelineState, { text: string; accent: string }> = {
  idle: { text: "Hazır", accent: "text-ink-muted" },
  listening: { text: "Dinliyor", accent: "text-amber" },
  transcribing: { text: "Anlıyor", accent: "text-ink" },
  responding: { text: "Cevaplıyor", accent: "text-amber" },
};

export function StateLabel({ state }: Props) {
  const cfg = LABELS[state];
  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-ink-muted">
        durum
      </span>
      <AnimatePresence mode="wait">
        <motion.span
          key={state}
          initial={{ opacity: 0, y: 3 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -3 }}
          transition={{ duration: 0.15 }}
          className={`font-mono text-[10.5px] uppercase tracking-[0.08em] ${cfg.accent}`}
        >
          {cfg.text}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}
