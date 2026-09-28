import { motion } from "framer-motion";
import { useId } from "react";
import { haptic } from "../../lib/telegram.js";

export default function Segmented({ value, onChange, options }) {
  const id = useId();
  const compact = options.length > 3;
  return (
    <div className="flex rounded-tile bg-raised/70 p-1" role="tablist">
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => {
              if (!active) haptic.select();
              onChange(opt.value);
            }}
            className={`relative flex-1 whitespace-nowrap rounded-[10px] py-2 font-semibold transition-colors ${compact ? "px-1 text-[13px]" : "px-3 text-sm"} ${active ? "text-ink" : "text-muted"}`}
          >
            {active && (
              <motion.span
                layoutId={`seg-${id}`}
                transition={{ type: "spring", stiffness: 500, damping: 38 }}
                className="absolute inset-0 rounded-[10px] bg-surface shadow-sm"
              />
            )}
            <span className="relative inline-flex items-center gap-1.5">
              {opt.icon && <opt.icon className="h-4 w-4" aria-hidden />}
              {opt.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
