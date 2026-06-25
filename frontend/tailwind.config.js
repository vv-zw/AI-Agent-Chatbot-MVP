/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        canvas: "#f5f7fb",
        brand: "#635bff",
      },
    },
  },
  plugins: [],
};

