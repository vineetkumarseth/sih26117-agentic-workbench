/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Deep graphite base with a blue undertone (not pure black) --
        // reads as an instrument console, not a generic dark-mode SaaS app.
        graphite: {
          950: "#0F1216",
          900: "#14181D",
          800: "#1C222B",
          700: "#252C37",
          600: "#2C333D",
          500: "#3A4350",
        },
        // Instrument amber -- gauge-needle / warning-plate accent.
        amber: {
          400: "#D9A257",
          500: "#C68A3E",
          600: "#A8722F",
        },
        // Control-room verified/online teal.
        teal: {
          400: "#6FCBBB",
          500: "#4FB7A6",
          600: "#3B9384",
        },
        // Muted industrial warning red (guardrail blocks, thresholds breached).
        alert: {
          400: "#D97C72",
          500: "#C0524A",
          600: "#9E4038",
        },
        ink: {
          100: "#E8E6E1",
          300: "#B7BCC4",
          500: "#8B93A0",
          700: "#5B6472",
        },
      },
      fontFamily: {
        sans: ["'Space Grotesk'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      borderRadius: {
        sm: "4px",
        DEFAULT: "6px",
        md: "8px",
      },
      keyframes: {
        "step-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
      },
      animation: {
        "step-in": "step-in 220ms ease-out",
        "pulse-dot": "pulse-dot 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
