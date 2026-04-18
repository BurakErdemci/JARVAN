import { motion } from "framer-motion";
import { ReactNode } from "react";

interface Props {
  label: string;
  caption: string;
  enabled: boolean;
  accent: "amber" | "pink";
  disabled?: boolean;
  icon: ReactNode;
  onToggle: (next: boolean) => void;
}

export function ToggleRow({
  label,
  caption,
  enabled,
  accent,
  disabled,
  icon,
  onToggle,
}: Props) {
  const accentBg = accent === "pink" ? "bg-pink-live" : "bg-amber";
  const accentBorder = accent === "pink" ? "border-pink-live/50" : "border-amber/50";
  const accentText = accent === "pink" ? "text-pink-live" : "text-amber";
  const accentGlow = accent === "pink" ? "pink-glow" : "amber-glow";

  return (
    <button
      onClick={() => !disabled && onToggle(!enabled)}
      disabled={disabled}
      className={`group flex w-full items-center justify-between rounded-lg border border-hairline bg-surface/60 px-3 py-2.5 text-left transition-all hover:border-ink-muted/60 hover:bg-surface-raised disabled:cursor-not-allowed disabled:opacity-50 ${
        enabled ? `${accentBorder} bg-surface-raised/80` : ""
      }`}
    >
      <div className="flex items-center gap-3">
        <span
          className={`grid h-7 w-7 place-items-center rounded-md border transition-colors ${
            enabled
              ? `border-transparent ${accentBg}/15 ${accentText}`
              : "border-hairline bg-surface text-ink-muted"
          }`}
        >
          {icon}
        </span>
        <div className="flex flex-col gap-0.5">
          <span className="font-mono text-[11px] font-medium uppercase tracking-[0.06em] text-ink">
            {label}
          </span>
          <span className="font-mono text-[9.5px] leading-snug text-ink-muted">
            {caption}
          </span>
        </div>
      </div>

      {/* Switch */}
      <div
        className={`relative h-[18px] w-[30px] shrink-0 rounded-full border transition-colors ${
          enabled
            ? `${accentBorder} ${accentBg}/25 ${enabled ? accentGlow : ""}`
            : "border-hairline bg-surface-sunken"
        }`}
      >
        <motion.span
          layout
          transition={{ type: "spring", stiffness: 500, damping: 32 }}
          className={`absolute top-1/2 h-[10px] w-[10px] -translate-y-1/2 rounded-full ${
            enabled ? `${accentBg} shadow-sm` : "bg-ink-muted"
          }`}
          style={{
            left: enabled ? "calc(100% - 13px)" : "3px",
          }}
        />
      </div>
    </button>
  );
}
