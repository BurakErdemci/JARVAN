import type { PipelineState } from "../types";

interface Props {
  state: PipelineState;
  /** px cinsinden kenar uzunluğu */
  size?: number;
}

const STATE_LABEL: Record<PipelineState, string> = {
  idle: "BEKLEMEDE",
  listening: "DİNLEMEDE",
  transcribing: "ÇÖZÜMLEME",
  responding: "YANITLIYOR",
  muted: "SUSTURULDU",
};

const STATE_SUB: Record<PipelineState, string> = {
  idle: "wake up ile uyandır",
  listening: "sesi bekliyor",
  transcribing: "kayıt yazıya dökülüyor",
  responding: "jarvan konuşuyor",
  muted: "mikrofon kapalı",
};

/**
 * REAKTÖR — sesli döngünün kalbi ve arayüzün imza öğesi.
 * Eşmerkezli SVG halkalar; durum = renk + dönüş hızı.
 * Soğuk (coolant) = makine dinliyor, sıcak (plasma) = Jarvan konuşuyor,
 * kızıl (flare) = susturuldu. Animasyonların tamamı CSS keyframe —
 * JS frame döngüsü YOK (eski Waveform %85 CPU yakıyordu; bu sınıf hata
 * burada yapısal olarak imkânsız).
 */
export function Reactor({ state, size = 190 }: Props) {
  const hot = state === "responding";
  const dead = state === "muted";
  const color = dead ? "#FF4D5E" : hot ? "#FF7A2F" : "#43E5C9";
  const dim = dead ? "#7A2833" : hot ? "#8C4520" : "#1D6E62";

  // Dış halka: 60 radyal çentik (sabit, gravür)
  const ticks = Array.from({ length: 60 }, (_, i) => {
    const a = (i / 60) * Math.PI * 2;
    const r1 = 88, r2 = i % 5 === 0 ? 80 : 84;
    return (
      <line
        key={i}
        x1={100 + Math.cos(a) * r1} y1={100 + Math.sin(a) * r1}
        x2={100 + Math.cos(a) * r2} y2={100 + Math.sin(a) * r2}
        stroke={i % 5 === 0 ? dim : "#16233A"}
        strokeWidth={i % 5 === 0 ? 1.5 : 1}
      />
    );
  });

  return (
    <div className={`reactor-${state} relative flex flex-col items-center`}>
      <svg width={size} height={size} viewBox="0 0 200 200" aria-hidden="true">
        {/* Gravür çentik halkası (sabit) */}
        <g>{ticks}</g>

        {/* Orta halka: parçalı yay — döner */}
        <g className="reactor-ring ring-mid">
          <circle
            cx="100" cy="100" r="68"
            fill="none" stroke={color} strokeWidth="2.5"
            strokeDasharray="52 18 8 18 90 18 8 18"
            strokeLinecap="butt" opacity="0.85"
          />
        </g>

        {/* İç halka: ince yay — ters döner */}
        <g className="reactor-ring ring-inner">
          <circle
            cx="100" cy="100" r="52"
            fill="none" stroke={dim} strokeWidth="1.5"
            strokeDasharray="120 40 30 40"
          />
          {/* muted: halka kırığı işareti */}
          {dead && (
            <line x1="100" y1="42" x2="100" y2="62" stroke="#FF4D5E" strokeWidth="3" />
          )}
        </g>

        {/* Çekirdek */}
        <circle className="core-glow" cx="100" cy="100" r="30" fill={color} opacity="0.12" />
        <circle cx="100" cy="100" r="18" fill="none" stroke={color} strokeWidth="1" opacity="0.6" />
        <circle cx="100" cy="100" r="5" fill={color} />
      </svg>

      {/* Durum yazısı — çekirdeğin altında */}
      <div className="pointer-events-none -mt-3 text-center">
        <div
          className="font-display text-[13px] font-semibold tracking-hud"
          style={{ color }}
        >
          {STATE_LABEL[state]}
        </div>
        <div className="font-mono text-3xs text-ink-ghost mt-0.5">
          {STATE_SUB[state]}
        </div>
      </div>
    </div>
  );
}
