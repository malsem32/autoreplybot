import { useState } from "react";

const W = 320;
const H = 112;
const GAP = 2;

function dayLabel(iso) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
  });
}

/** Daily bars for the admin section: one series, or two stacked (e.g.
 * delivered / failed). Tap or hover a day to read its exact values. */
export default function BarChart({ title, days, series, format = (v) => String(v), note }) {
  const [active, setActive] = useState(null);
  const totals = days.map((_, i) => series.reduce((sum, s) => sum + (s.values[i] || 0), 0));
  const max = Math.max(1, ...totals);
  const slot = W / days.length;
  const barW = Math.max(2, slot - GAP);
  const periodTotal = totals.reduce((a, b) => a + b, 0);
  const shown = active ?? null;

  return (
    <section className="rounded-[18px] bg-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-[14px] font-semibold">{title}</h3>
          <p className="mt-0.5 text-[12px] text-faint">{note || "за 30 дней"}</p>
        </div>
        <p className="shrink-0 font-display text-[22px] font-semibold leading-none tabular-nums">
          {format(periodTotal)}
        </p>
      </div>

      {series.length > 1 && (
        <div className="mt-3 flex flex-wrap gap-3 text-[12px] text-muted">
          {series.map((s) => (
            <span key={s.key} className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} />
              {s.label}
            </span>
          ))}
        </div>
      )}

      <div className="mt-3 h-5 text-[12px] tabular-nums text-muted" aria-live="polite">
        {shown !== null ? (
          <>
            <span className="font-semibold text-ink">{dayLabel(days[shown])}</span>
            {series.map((s) => (
              <span key={s.key}>
                {" · "}
                {series.length > 1 ? `${s.label.toLowerCase()} ` : ""}
                <span className="font-semibold text-ink">{format(s.values[shown] || 0)}</span>
              </span>
            ))}
          </>
        ) : (
          <span className="text-faint">максимум в день: {format(max)}</span>
        )}
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="mt-1 block h-28 w-full touch-none"
        preserveAspectRatio="none"
        role="img"
        aria-label={`${title}: ${format(periodTotal)} за период`}
        onPointerLeave={() => setActive(null)}
      >
        <line x1="0" x2={W} y1={H - 0.5} y2={H - 0.5} stroke="rgb(var(--line))" strokeWidth="1" />
        {days.map((day, i) => {
          const x = i * slot + GAP / 2;
          let y = H - 1;
          const dim = active !== null && active !== i;
          return (
            <g key={day} opacity={dim ? 0.4 : 1}>
              {series.map((s, si) => {
                const v = s.values[i] || 0;
                if (!v) return null;
                const h = Math.max(2, (v / max) * (H - 8));
                const segGap = si > 0 ? GAP : 0;
                y -= h + segGap;
                const top =
                  si === series.length - 1 || series.slice(si + 1).every((t) => !t.values[i]);
                return (
                  <rect
                    key={s.key}
                    x={x}
                    y={y}
                    width={barW}
                    height={h}
                    rx={top ? Math.min(2, barW / 2) : 0}
                    fill={s.color}
                  />
                );
              })}
              <rect
                x={i * slot}
                y="0"
                width={slot}
                height={H}
                fill="transparent"
                onPointerEnter={() => setActive(i)}
                onPointerDown={() => setActive(i)}
              />
            </g>
          );
        })}
      </svg>
      <div className="mt-1.5 flex justify-between text-[11px] tabular-nums text-faint">
        <span>{dayLabel(days[0])}</span>
        <span>{dayLabel(days[Math.floor(days.length / 2)])}</span>
        <span>сегодня</span>
      </div>
    </section>
  );
}
