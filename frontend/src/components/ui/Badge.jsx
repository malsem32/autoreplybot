const COLORS = {
  active: "bg-emerald-500/15 text-emerald-400",
  paused: "bg-amber-500/15 text-amber-400",
  finished: "bg-slate-500/15 text-slate-400",
  error: "bg-red-500/15 text-red-400",
};

const LABELS = {
  active: "Активна",
  paused: "На паузе",
  finished: "Завершена",
};

export default function Badge({ status }) {
  return (
    <span
      className={`text-xs px-2 py-1 rounded-full font-medium ${COLORS[status] || COLORS.finished}`}
    >
      {LABELS[status] || status}
    </span>
  );
}
