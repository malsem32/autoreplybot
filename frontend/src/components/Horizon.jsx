import { useReducedMotion } from "framer-motion";

/** The attitude indicator: the app's signature element. Sky over ground,
 * with the brand's steering wheel in front. While the autopilot is engaged
 * the horizon breathes gently; paused, it levels out and dims. */
export default function Horizon({ engaged, size = 208 }) {
  const reduce = useReducedMotion();
  const tilt = engaged && !reduce;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      {engaged && (
        <span
          className="absolute inset-0 rounded-full border-2 border-go/60 will-change-transform animate-pulseRing"
          aria-hidden
        />
      )}
      <div
        className={`relative isolate h-full w-full overflow-hidden rounded-full ring-[6px] transition-[box-shadow,filter] duration-500 [transform:translateZ(0)] ${
          engaged
            ? "ring-go/25 shadow-[0_0_60px_-10px_rgb(var(--go)/0.55)]"
            : "ring-line saturate-50"
        }`}
      >
        <div
          className={`absolute -inset-1/4 will-change-transform ${tilt ? "animate-horizonTilt" : ""}`}
        >
          <div className="h-1/2 bg-gradient-to-b from-[#1E6FD9] to-[#5CC8FF]" />
          <div className="h-1/2 bg-gradient-to-b from-[#1A2A55] to-[#0E1838]" />
          <div className="absolute inset-x-0 top-1/2 h-[2px] -translate-y-1/2 bg-white/80" />
          {[-2, -1, 1, 2].map((n) => (
            <div
              key={n}
              className="absolute left-1/2 h-[2px] -translate-x-1/2 bg-white/45"
              style={{ top: `calc(50% + ${n * 7}%)`, width: n % 2 ? "14%" : "24%" }}
            />
          ))}
        </div>

        <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full" aria-hidden>
          <g fill="none" stroke="white" strokeLinecap="round" strokeWidth="5.5">
            <circle cx="50" cy="50" r="24" />
            <circle cx="50" cy="50" r="6.5" fill="white" />
            <path d="M50 56.5 V74" />
            <path d="M43.8 48 L27.5 43" />
            <path d="M56.2 48 L72.5 43" />
          </g>
        </svg>
      </div>
    </div>
  );
}
