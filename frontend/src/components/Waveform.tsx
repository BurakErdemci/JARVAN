import { useEffect, useRef, useState } from "react";
import type { PipelineState } from "../types";

interface Props {
  state: PipelineState;
  accent?: "amber" | "pink";
}

const BAR_COUNT = 32;

// Performans: framer-motion KULLANMA — 60fps'te bar başına yeni tween üretip
// renderer'ı %70+ CPU'ya çıkarıyordu. Düz div + CSS transition + düşük fps yeter.
export function Waveform({ state, accent = "amber" }: Props) {
  const [amplitudes, setAmplitudes] = useState<number[]>(
    Array.from({ length: BAR_COUNT }, () => 0.1)
  );
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    let t = 0;
    let last = 0;
    // Boşta 10fps'lik nefes yeter; aktifken 24fps akıcı görünür.
    const fpsInterval = state === "idle" ? 100 : 42;

    const tick = (now: number) => {
      frameRef.current = requestAnimationFrame(tick);
      if (now - last < fpsInterval) return;
      t += ((now - last) / 1000) * 2.4; // hız gerçek zamana bağlı (fps'ten bağımsız)
      last = now;
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
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [state]);

  const color = accent === "pink" ? "bg-pink-live" : "bg-amber";
  const dimColor = "bg-ink-faint";
  const isActive = state !== "idle";
  const glow = accent === "pink" ? "rgba(255,77,143,0.5)" : "rgba(255,138,61,0.5)";

  return (
    <div className="flex h-full w-full items-center justify-center gap-[3px]">
      {amplitudes.map((amp, i) => (
        <div
          key={i}
          className={`w-[3px] rounded-full ${isActive ? color : dimColor}`}
          style={{
            height: `${Math.max(3, amp * 100)}%`,
            transition: "height 90ms linear",
            opacity: isActive ? 0.4 + amp * 0.6 : 0.35,
            // Gölge sadece aktifken ve sabit — her karede yeni shadow compositing pahalı
            boxShadow: isActive ? `0 0 6px ${glow}` : "none",
          }}
        />
      ))}
    </div>
  );
}
