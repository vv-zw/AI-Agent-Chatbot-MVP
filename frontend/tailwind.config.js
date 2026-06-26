/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1f2933",
        muted: "#6b7280",
        canvas: "#f4f5f2",
        panel: "#fbfbf8",
        line: "#e2e0d8",
        brand: "#2f5d50",
        accent: "#b46a3c",
        success: "#2f7d57",
        warning: "#b7791f",
        danger: "#b42318",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "PingFang SC",
          "Microsoft YaHei",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "SFMono-Regular", "Consolas", "monospace"],
      },
      boxShadow: {
        shell: "0 28px 70px rgb(31 41 51 / 0.12)",
        soft: "0 14px 32px rgb(31 41 51 / 0.08)",
      },
    },
  },
  plugins: [],
};
