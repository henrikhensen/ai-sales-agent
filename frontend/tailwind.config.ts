import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
        },
        // Near-black scale — the editorial redesign's primary structural
        // color (hero, section frames, headline text, borders). Kept
        // separate from `slate` so nothing else silently shifts tone.
        ink: {
          50: "#f5f6f8",
          100: "#e9eaee",
          200: "#cbcdd6",
          300: "#9ea2b0",
          400: "#6c7080",
          500: "#4a4e5c",
          600: "#34363f",
          700: "#24252c",
          800: "#17181d",
          900: "#0c0d10",
          950: "#07070a",
        },
        // Slightly warm off-white used to alternate large sections against
        // pure white, the way a printed editorial page alternates stock —
        // without introducing another hue.
        bone: "#F5F4F1",
      },
      fontSize: {
        // Huge, tight-tracking display sizes for the hero headline — set
        // with clamp() so three stacked headline lines never overflow on
        // narrow viewports without a separate mobile override.
        display: ["clamp(2.75rem, 9vw, 6.5rem)", { lineHeight: "0.98", letterSpacing: "-0.03em" }],
        "display-md": ["clamp(2rem, 5vw, 3rem)", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
      },
      letterSpacing: {
        widest2: "0.2em",
      },
      // Short, purposeful motion only — entrance/reveal and one "live"
      // pulse for status dots. Every animation here is capped well under
      // 500ms; `prefers-reduced-motion` is handled globally in
      // globals.css, and `pulse-soft` is only ever applied via the
      // `motion-safe:` variant so it never fires for users who asked for
      // reduced motion.
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.9)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.35s ease-out both",
        "fade-in-up": "fade-in-up 0.4s ease-out both",
        "scale-in": "scale-in 0.25s ease-out both",
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
