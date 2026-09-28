import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useState } from "react";

/** Keywords as removable chips; Enter or comma adds one. */
export default function ChipsInput({ value, onChange, placeholder, id }) {
  const [draft, setDraft] = useState("");

  function commit(raw = draft) {
    const words = raw
      .split(",")
      .map((w) => w.trim())
      .filter(Boolean)
      .filter((w) => !value.some((v) => v.toLowerCase() === w.toLowerCase()));
    if (words.length) onChange([...value, ...words]);
    setDraft("");
  }

  return (
    <div className="field flex min-h-[52px] flex-wrap items-center gap-1.5 !py-2">
      <AnimatePresence initial={false}>
        {value.map((word) => (
          <motion.span
            key={word}
            layout
            initial={{ scale: 0.7, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.7, opacity: 0 }}
            className="inline-flex items-center gap-1 rounded-lg bg-sky/15 py-1 pl-2.5 pr-1 text-sm font-medium text-sky"
          >
            {word}
            <button
              type="button"
              onClick={() => onChange(value.filter((v) => v !== word))}
              className="grid h-5 w-5 place-items-center rounded-md hover:bg-sky/20"
              aria-label={`Убрать «${word}»`}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </motion.span>
        ))}
      </AnimatePresence>
      <input
        id={id}
        value={draft}
        onChange={(e) => {
          const v = e.target.value;
          if (v.includes(",")) commit(v);
          else setDraft(v);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            commit();
          } else if (e.key === "Backspace" && !draft && value.length) {
            onChange(value.slice(0, -1));
          }
        }}
        onBlur={() => commit()}
        placeholder={value.length ? "" : placeholder}
        className="min-w-[8rem] flex-1 bg-transparent py-1 text-[15px] placeholder:text-faint focus:outline-none"
      />
    </div>
  );
}
