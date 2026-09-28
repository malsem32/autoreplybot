import { haptic } from "../../lib/telegram.js";

export default function ChoiceChips({ value, onChange, options }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => {
              haptic.select();
              onChange(opt.value);
            }}
            className={`rounded-full px-3.5 py-2 text-sm font-semibold transition-colors ${
              active ? "bg-sky text-onsky" : "bg-raised/70 text-muted hover:text-ink"
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
