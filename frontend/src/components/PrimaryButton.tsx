import { motion } from "framer-motion";
import { Power, Square } from "lucide-react";

interface Props {
  running: boolean;
  disabled?: boolean;
  onClick: () => void;
}

export function PrimaryButton({ running, disabled, onClick }: Props) {
  return (
    <motion.button
      onClick={onClick}
      disabled={disabled}
      whileTap={{ scale: 0.98 }}
      whileHover={disabled ? {} : { scale: 1.005 }}
      className={`group relative flex w-full items-center justify-between overflow-hidden rounded-xl border px-4 py-3 font-mono transition-all disabled:cursor-not-allowed disabled:opacity-50 ${
        running
          ? "amber-glow border-amber/60 bg-amber/10 text-amber"
          : "border-hairline bg-surface text-ink hover:border-ink-muted hover:bg-surface-raised"
      }`}
    >
      {/* Moving bg sheen when running */}
      {running && (
        <motion.div
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            background:
              "linear-gradient(90deg, transparent 0%, rgba(255,138,61,0.25) 50%, transparent 100%)",
          }}
          animate={{ x: ["-100%", "200%"] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }}
        />
      )}

      <div className="relative flex items-center gap-3">
        <span
          className={`grid h-8 w-8 place-items-center rounded-lg ${
            running ? "bg-amber/25" : "bg-surface-raised"
          }`}
        >
          {running ? (
            <Square size={12} strokeWidth={2.5} fill="currentColor" />
          ) : (
            <Power size={13} strokeWidth={2} />
          )}
        </span>
        <div className="flex flex-col items-start gap-0.5">
          <span className="text-[13px] font-medium tracking-tight">
            {running ? "Durdur" : "Başlat"}
          </span>
          <span className="text-[9px] uppercase tracking-[0.12em] opacity-60">
            {running ? "dinliyor" : "pipeline kapalı"}
          </span>
        </div>
      </div>

      <kbd
        className={`relative hidden rounded border px-1.5 py-0.5 text-[9px] uppercase tracking-wider sm:block ${
          running ? "border-amber/30 text-amber/70" : "border-hairline text-ink-muted"
        }`}
      >
        ⌘ K
      </kbd>
    </motion.button>
  );
}
