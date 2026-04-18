import { motion, AnimatePresence } from "framer-motion";
import type { ModeName } from "../types";

interface Props {
  mode: ModeName;
}

const MODE_CONFIG: Record<
  ModeName,
  { label: string; dotClass: string; borderClass: string; textClass: string }
> = {
  unreal: {
    label: "UNREAL",
    dotClass: "bg-mode-unreal",
    borderClass: "border-mode-unreal/40",
    textClass: "text-mode-unreal",
  },
  unity: {
    label: "UNITY",
    dotClass: "bg-mode-unity",
    borderClass: "border-mode-unity/40",
    textClass: "text-mode-unity",
  },
  code: {
    label: "CODE",
    dotClass: "bg-mode-code",
    borderClass: "border-mode-code/40",
    textClass: "text-mode-code",
  },
  default: {
    label: "DEFAULT",
    dotClass: "bg-mode-default",
    borderClass: "border-ink-faint",
    textClass: "text-ink-soft",
  },
};

export function ModeBadge({ mode }: Props) {
  const cfg = MODE_CONFIG[mode];

  return (
    <div className="flex items-center gap-1.5">
      <span className="font-mono text-[8.5px] uppercase tracking-[0.16em] text-ink-muted">
        mod
      </span>
      <AnimatePresence mode="wait">
        <motion.div
          key={mode}
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 4 }}
          transition={{ duration: 0.2 }}
          className={`flex items-center gap-1.5 rounded-full border ${cfg.borderClass} bg-surface-raised/60 px-2 py-[3px]`}
        >
          <span className={`inline-block h-[5px] w-[5px] rounded-full ${cfg.dotClass}`} />
          <span className={`font-mono text-[9px] font-medium uppercase tracking-[0.14em] ${cfg.textClass}`}>
            {cfg.label}
          </span>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
