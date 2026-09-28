/** @type {import('tailwindcss').Config} */
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: token("bg"),
        surface: token("surface"),
        raised: token("raised"),
        line: token("line"),
        ink: token("ink"),
        muted: token("muted"),
        faint: token("faint"),
        sky: token("sky"),
        go: token("go"),
        warn: token("warn"),
        danger: token("danger"),
        onsky: token("onsky"),
      },
      fontFamily: {
        display: ["Unbounded", "system-ui", "sans-serif"],
        sans: ["Onest", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      borderRadius: {
        tile: "14px",
        sheet: "26px",
      },
      keyframes: {
        shimmer: { "100%": { transform: "translateX(100%)" } },
        pulseRing: {
          "0%": { transform: "scale(0.9)", opacity: "0.7" },
          "100%": { transform: "scale(1.35)", opacity: "0" },
        },
      },
      animation: {
        shimmer: "shimmer 1.4s infinite",
        pulseRing: "pulseRing 2.4s cubic-bezier(0.2, 0.6, 0.3, 1) infinite",
      },
    },
  },
  plugins: [],
};
