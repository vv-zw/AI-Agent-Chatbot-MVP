/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#2e293b",
        muted: "#776f86",
        canvas: "#f8f5ee",
        panel: "#fffdf8",
        parchment: "#faf7f0",
        line: "#e8dcc8",
        brand: "#6d5bd0",
        brandDeep: "#4c3f9f",
        accent: "#d6a84f",
        success: "#2f9e7e",
        warning: "#b7791f",
        danger: "#d94c4c",
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
        shell: "0 28px 80px rgb(80 63 120 / 0.16)",
        soft: "0 14px 32px rgb(80 63 120 / 0.10)",
        scroll: "0 10px 28px rgb(109 91 208 / 0.14)",
      },
      backgroundImage: {
        parchment: "linear-gradient(180deg, #fffdf8 0%, #faf7f0 100%)",
        arcana: "radial-gradient(circle at 18px 18px, rgb(214 168 79 / 0.18) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};
