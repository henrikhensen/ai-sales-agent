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
        // Near-black scale for dark "command-center" surfaces (hero,
        // header accents) — kept separate from `slate` so light work
        // surfaces (cards, forms, tables) are untouched by the dark theme.
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
      },
      fontSize: {
        "display-lg": ["3.5rem", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
        "display-md": ["2.75rem", { lineHeight: "1.08", letterSpacing: "-0.02em" }],
      },
      boxShadow: {
        premium: "0 1px 2px rgba(15,17,21,0.04), 0 12px 32px -12px rgba(15,17,21,0.18)",
        "premium-dark": "0 20px 60px -20px rgba(0,0,0,0.6)",
      },
      backgroundImage: {
        "grid-faint":
          "linear-gradient(to right, rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.06) 1px, transparent 1px)",
      },
      backgroundSize: {
        grid: "40px 40px",
      },
    },
  },
  plugins: [],
};

export default config;
