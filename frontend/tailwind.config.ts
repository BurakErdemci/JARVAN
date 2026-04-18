import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        obsidian: "#0b0b0e",
        surface: {
          DEFAULT: "#141418",
          raised: "#1a1a20",
          sunken: "#0e0e12",
        },
        hairline: "#1f1f24",
        ink: {
          DEFAULT: "#ededed",
          soft: "#8a8a92",
          muted: "#5a5a62",
          faint: "#3a3a42",
        },
        amber: {
          DEFAULT: "#ff8a3d",
          glow: "#ff9a4d",
          deep: "#c86a2a",
        },
        pink: {
          live: "#ff4d8f",
          glow: "#ff7aad",
        },
        mode: {
          unreal: "#5eead4",
          unity: "#fbbf24",
          code: "#a78bfa",
          default: "#8a8a92",
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        display: ['"Instrument Serif"', "Georgia", "serif"],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },
      animation: {
        "breath": "breath 4s ease-in-out infinite",
        "pulse-slow": "pulse 3s ease-in-out infinite",
        "grain": "grain 8s steps(10) infinite",
      },
      keyframes: {
        breath: {
          "0%, 100%": { opacity: "0.4", transform: "scaleY(1)" },
          "50%": { opacity: "0.7", transform: "scaleY(1.15)" },
        },
        grain: {
          "0%, 100%": { transform: "translate(0, 0)" },
          "10%": { transform: "translate(-5%, -10%)" },
          "20%": { transform: "translate(-15%, 5%)" },
          "30%": { transform: "translate(7%, -25%)" },
          "40%": { transform: "translate(-5%, 25%)" },
          "50%": { transform: "translate(-15%, 10%)" },
          "60%": { transform: "translate(15%, 0%)" },
          "70%": { transform: "translate(0%, 15%)" },
          "80%": { transform: "translate(3%, 35%)" },
          "90%": { transform: "translate(-10%, 10%)" },
        },
      },
    },
  },
} satisfies Config;
