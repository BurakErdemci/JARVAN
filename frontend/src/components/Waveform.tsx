import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import type { PipelineState } from "../types";

interface Props {
  state: PipelineState;
  accent?: "amber" | "pink";
}

const BAR_COUNT = 32;

export function Waveform({ state, accent = "amber" }: Props) {
  const [amplitudes, setAmplitudes] = useState<number[]>(
    Array.from({ length: BAR_COUNT }, () => 0.1)
  );
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    let t = 0;

    const tick = () => {
      t += 0.04;
      setAmplitudes(() => {
        return Array.from({ length: BAR_COUNT }, (_, i) => {
          const center = (BAR_COUNT - 1) / 2;
          const distFromCenter = Math.abs(i - center) / center;
          const centerBias = 1 - distFromCenter * 0.55;

          if (state === "idle") {
            // Gentle breath — low and sparse
            const wave = Math.sin(t * 0.8 + i * 0.35) * 0.5 + 0.5;
            return 0.08 + wave * 0.12 * centerBias;
          }
          if (state === "listening") {
            // Active — irregular, reactive feel
            const wave1 = Math.sin(t * 4 + i * 0.7) * 0.5 + 0.5;
            const wave2 = Math.sin(t * 7 + i * 1.3) * 0.5 + 0.5;
            const noise = Math.random() * 0.3;
            return 0.2 + (wave1 * 0.5 + wave2 * 0.3 + noise) * centerBias;
          }
          if (state === "transcribing") {
            // Processing — pulsing from left to right
            const sweep = ((t * 2.5) % 2) - 1;
            const dist = Math.abs(i / BAR_COUNT - (sweep + 1) / 2);
            return 0.15 + Math.max(0, 0.7 - dist * 2) * centerBias;
          }
          if (state === "responding") {
            // Speaking back — flowing curves
            const wave = Math.sin(t * 3.5 + i * 0.4) * 0.5 + 0.5;
            return 0.25 + wave * 0.55 * centerBias;
          }
          return 0.1;
        });
      });
      frameRef.current = requestAnimationFrame(tick);
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [state]);

  const color = accent === "pink" ? "bg-pink-live" : "bg-amber";
  const dimColor = "bg-ink-faint";
  const isActive = state !== "idle";

  return (
    <div className="flex h-full w-full items-center justify-center gap-[3px]">
      {amplitudes.map((amp, i) => (
        <motion.div
          key={i}
          className={`w-[3px] rounded-full ${isActive ? color : dimColor}`}
          animate={{ height: `${Math.max(3, amp * 100)}%` }}
          transition={{ type: "tween", duration: 0.08, ease: "linear" }}
          style={{
            opacity: isActive ? 0.4 + amp * 0.6 : 0.35,
            boxShadow: isActive
              ? `0 0 ${Math.min(8, amp * 10)}px ${
                  accent === "pink" ? "rgba(255,77,143,0.5)" : "rgba(255,138,61,0.5)"
                }`
              : "none",
          }}
        />
      ))}
    </div>
  );
}
