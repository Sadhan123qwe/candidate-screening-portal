import colors from "tailwindcss/colors";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // The one accent color. Change it here and the whole app follows.
      colors: { accent: colors.indigo },
    },
  },
  plugins: [],
};
