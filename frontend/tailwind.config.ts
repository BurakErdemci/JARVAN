import type { Config } from "tailwindcss";

/**
 * KOKPİT 2090 — tasarım tokenları.
 * Çift sıcaklık sistemi: soğuk (coolant) = makine/telemetri,
 * sıcak (plasma) = Jarvan'ın sesi/birincil aksiyon. Renk süs değil bilgidir.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#05070D",        // sayfa tabanı — mavi-siyah gövde
        hull: {
          DEFAULT: "#0A111C",   // panel yüzeyi
          raised: "#0E1726",    // kabarık yüzey (kart)
          sunken: "#070C14",    // çukur yüzey (giriş, kuyu)
        },
        steel: {
          DEFAULT: "#16233A",   // yapısal çizgi/hairline
          bright: "#24374F",    // vurgulu çizgi
        },
        coolant: {
          DEFAULT: "#43E5C9",   // makine/telemetri/ok
          dim: "#1D6E62",
          ghost: "rgba(67,229,201,0.08)",
        },
        plasma: {
          DEFAULT: "#FF7A2F",   // Jarvan'ın sesi/birincil
          dim: "#8C4520",
          ghost: "rgba(255,122,47,0.08)",
        },
        flare: {
          DEFAULT: "#FF4D5E",   // hata/susturma
          dim: "#7A2833",
        },
        ink: {
          DEFAULT: "#D2DEF0",   // ana metin (buz)
          soft: "#A8B9D0",
          muted: "#7C8DA6",     // ikincil (sis)
          ghost: "#46586F",     // en soluk
        },
        agent: {
          codex: "#A78BFA",     // menekşe
          agy: "#43E5C9",       // teal (coolant ailesi)
          claude: "#E8C468",    // altın
          local: "#7C8DA6",
        },
        mode: {
          unreal: "#43E5C9",
          unity: "#E8C468",
          code: "#A78BFA",
          default: "#7C8DA6",
        },
      },
      fontFamily: {
        display: ['"Chakra Petch"', '"IBM Plex Sans"', "system-ui", "sans-serif"],
        body: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
        "3xs": ["0.5625rem", { lineHeight: "0.75rem" }],
      },
      letterSpacing: {
        hud: "0.14em", // etiketlerin HUD havası
      },
    },
  },
} satisfies Config;
