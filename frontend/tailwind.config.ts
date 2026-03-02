import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bluecore: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a"
        }
      },
      boxShadow: {
        "blue-glow": "0 0 0 1px rgba(37,99,235,.25), 0 12px 30px -12px rgba(37,99,235,.45)"
      },
      borderRadius: {
        xl2: "1.1rem"
      }
    }
  },
  plugins: []
} satisfies Config;
