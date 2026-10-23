import type { Config } from "tailwindcss";
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: { colors: { muted: "#9a9a9a" }, fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] } } },
  plugins: [],
} satisfies Config;
