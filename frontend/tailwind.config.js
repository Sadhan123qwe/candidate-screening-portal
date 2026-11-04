/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // Every value comes from src/styles/tokens.css. Change it there and the whole app follows.
      colors: {
        bg: "var(--bg)",
        ink: "var(--ink)",
        muted: "var(--muted)",
        faint: "var(--faint)",
        glass: "var(--glass)",
        "glass-strong": "var(--glass-strong)",
        line: "var(--line)",
        "line-strong": "var(--line-strong)",
        accent: "var(--accent)",
        "accent-ink": "var(--accent-ink)",
        ok: "var(--ok)",
        "ok-bg": "var(--ok-bg)",
        "ok-line": "var(--ok-line)",
        warn: "var(--warn)",
        "warn-bg": "var(--warn-bg)",
        "warn-line": "var(--warn-line)",
        bad: "var(--bad)",
        "bad-bg": "var(--bad-bg)",
        "bad-line": "var(--bad-line)",
        info: "var(--info)",
        "info-bg": "var(--info-bg)",
      },
      borderRadius: {
        card: "var(--radius-card)",
        ctl: "var(--radius-ctl)",
        btn: "var(--radius-btn)",
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
    },
  },
  plugins: [],
};
