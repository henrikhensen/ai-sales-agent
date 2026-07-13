import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Central brand palette — mirrors the CSS custom properties in
        // `app/globals.css` (`--color-bg`/`--color-surface`/
        // `--color-muted`/`--color-white`). Every dark surface, text
        // color, and border in this app traces back to one of these
        // four (`white` is Tailwind's own built-in #fff, used sparingly
        // per the brand brief — small accents/icons/strong CTA text
        // only, never a background).
        canvas: "#1A0B12",
        surface: "#3D1022",
        muted: "#E3C5BB",

        // Warm accent derived from the palette (not a generic SaaS
        // indigo/blue) — used only for focus rings and the rare
        // "this is a live/interactive link" moment.
        brand: {
          50: "#2E1420",
          100: "#3D1022",
          200: "#5A1B32",
          300: "#7A2842",
          400: "#9C3654",
          500: "#B84868",
          600: "#C96A82",
          700: "#D8899C",
          800: "#E3C5BB",
          900: "#EDD9D1",
        },
        // Structural dark scale for the rare spot that wants a shade
        // between `canvas` and `surface` (e.g. a hover state) rather
        // than a flat brand token.
        ink: {
          50: "#4A1B2E",
          100: "#42172A",
          200: "#3D1022",
          300: "#33101F",
          400: "#2C0D1B",
          500: "#260C18",
          600: "#210A15",
          700: "#1D0912",
          800: "#1A0B12",
          900: "#160810",
          950: "#12070D",
        },
        // Tailwind's built-in `slate` scale is overridden wholesale so
        // every page still written against `text-slate-*`/`bg-slate-*`/
        // `border-slate-*` (the majority of secondary/admin routes)
        // retints to the new dark palette centrally, without having to
        // hand-edit each file. Low numbers = subtle recessed surfaces/
        // hairlines (was: light background tints); high numbers = brighter
        // muted text (was: darker text) — the same role each shade played
        // before, just re-targeted to a dark canvas.
        slate: {
          50: "#241019",
          100: "#2E1420",
          200: "rgba(227,197,187,0.14)",
          300: "rgba(227,197,187,0.24)",
          400: "#9C8079",
          500: "#B79C93",
          600: "#C9A99C",
          700: "#D8BBAE",
          800: "#E0C3B8",
          900: "#E3C5BB",
        },
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
        // A slow, subtle drift for the hero's ambient background shapes —
        // never a full loop back to the exact start (keeps it feeling
        // alive rather than mechanically looping), always under
        // `motion-safe:` so a reduced-motion request removes it entirely
        // rather than just speeding it up.
        "drift-a": {
          "0%": { transform: "translate(0, 0) scale(1)" },
          "50%": { transform: "translate(3%, 4%) scale(1.08)" },
          "100%": { transform: "translate(0, 0) scale(1)" },
        },
        "drift-b": {
          "0%": { transform: "translate(0, 0) scale(1)" },
          "50%": { transform: "translate(-4%, -3%) scale(1.05)" },
          "100%": { transform: "translate(0, 0) scale(1)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.35s ease-out both",
        "fade-in-up": "fade-in-up 0.4s ease-out both",
        "scale-in": "scale-in 0.25s ease-out both",
        "pulse-soft": "pulse-soft 2s ease-in-out infinite",
        "drift-a": "drift-a 22s ease-in-out infinite",
        "drift-b": "drift-b 26s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
