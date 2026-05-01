import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        sf: {
          green: "#16a34a",
          dark: "#12412d",
          mint: "#ecfdf3",
          line: "#d9eadf",
        },
        ember: {
          100: "#fff3e7",
          400: "#d89b6a",
          500: "#e8733a",
          900: "#1f120c",
        },
        terminal: {
          bg: "#080b12",
          card: "#101622",
          border: "#253142",
          text: "#e7edf7",
          muted: "#7d8ba1",
        },
      },
      boxShadow: {
        soft: "0 10px 30px rgba(18, 65, 45, 0.10)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Georgia", "serif"],
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        "slide-down": {
          "0%": { opacity: "0", transform: "translateY(-6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" },
        },
      },
      animation: {
        "fade-in": "fade-in 280ms ease-out both",
        "scale-in": "scale-in 220ms ease-out both",
        "slide-down": "slide-down 180ms ease-out both",
        float: "float 2.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
