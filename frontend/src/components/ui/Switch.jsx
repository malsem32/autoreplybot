import { motion } from "framer-motion";
import { haptic } from "../../lib/telegram.js";

export default function Switch({ checked, onChange, disabled, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => {
        haptic.select();
        onChange(!checked);
      }}
      className={`relative h-[30px] w-[50px] shrink-0 rounded-full transition-colors disabled:opacity-40 ${checked ? "bg-go" : "bg-line"}`}
    >
      <motion.span
        layout
        transition={{ type: "spring", stiffness: 700, damping: 35 }}
        className={`absolute top-[3px] h-6 w-6 rounded-full bg-white shadow ${checked ? "right-[3px]" : "left-[3px]"}`}
      />
    </button>
  );
}
