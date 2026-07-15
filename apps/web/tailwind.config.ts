import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0e14",
        panel: "#12161f",
        panel2: "#1a2030",
        border: "#232a3b",
        accent: "#6ea8fe",
        accent2: "#8b5cf6",
        muted: "#8a93a6",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
