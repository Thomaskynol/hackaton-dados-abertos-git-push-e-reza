import type { Config } from "tailwindcss";

/**
 * Design system AgroPilot — paleta terrosa (fuga do verde-agro genérico).
 * Terracota (ação) + off-white quente (base) + oliva dessaturado só para "favorável".
 * Tudo via CSS vars em globals.css para permitir Modo Campo (alto contraste).
 */
const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // base
        canvas: "rgb(var(--c-canvas) / <alpha-value>)",
        surface: "rgb(var(--c-surface) / <alpha-value>)",
        line: "rgb(var(--c-line) / <alpha-value>)",
        ink: "rgb(var(--c-ink) / <alpha-value>)",
        muted: "rgb(var(--c-muted) / <alpha-value>)",
        // marca / ação
        terra: {
          DEFAULT: "rgb(var(--c-terra) / <alpha-value>)",
          soft: "rgb(var(--c-terra-soft) / <alpha-value>)",
          ink: "rgb(var(--c-terra-ink) / <alpha-value>)",
        },
        // estados honestos (ZARC 4 estados)
        favoravel: "rgb(var(--c-favoravel) / <alpha-value>)",
        atencao: "rgb(var(--c-atencao) / <alpha-value>)",
        risco: "rgb(var(--c-risco) / <alpha-value>)",
        pendente: "rgb(var(--c-pendente) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xl2: "1.25rem",
      },
      boxShadow: {
        soft: "0 2px 10px rgb(42 36 32 / 0.06)",
        card: "0 6px 22px rgb(42 36 32 / 0.08)",
        lift: "0 14px 34px rgb(42 36 32 / 0.14)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        wave: {
          "0%,100%": { transform: "scaleY(0.4)" },
          "50%": { transform: "scaleY(1)" },
        },
        pulseDot: {
          "0%,100%": { transform: "scale(1)", opacity: "1" },
          "50%": { transform: "scale(1.35)", opacity: "0.5" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.25s cubic-bezier(0.16,1,0.3,1)",
        wave: "wave 0.9s ease-in-out infinite",
        "pulse-dot": "pulseDot 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
