import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { haptic } from "../../lib/telegram.js";

const VARIANTS = {
  primary: "bg-sky text-onsky shadow-[0_8px_24px_-12px_rgb(var(--sky))] hover:brightness-110",
  secondary: "bg-raised text-ink hover:bg-raised/80",
  ghost: "bg-transparent text-sky hover:bg-sky/10",
  danger: "bg-danger/12 text-danger hover:bg-danger/20",
  go: "bg-go text-onsky hover:brightness-110",
  pro: "bg-warn text-[#2A1A00] shadow-[0_8px_24px_-12px_rgb(var(--warn))] hover:brightness-105",
};

const SIZES = {
  md: "h-12 px-5 text-[15px] rounded-tile",
  sm: "h-9 px-3.5 text-sm rounded-[11px]",
};

export default function Button({
  variant = "primary",
  size = "md",
  className = "",
  type = "button",
  loading = false,
  disabled,
  icon: Icon,
  children,
  onClick,
  ...props
}) {
  return (
    <motion.button
      type={type}
      whileTap={{ scale: 0.97 }}
      transition={{ type: "spring", stiffness: 600, damping: 30 }}
      disabled={disabled || loading}
      onClick={(e) => {
        haptic.tap();
        onClick?.(e);
      }}
      className={`inline-flex items-center justify-center gap-2 font-semibold transition-[filter,background-color,opacity] disabled:opacity-45 disabled:pointer-events-none ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...props}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      ) : (
        Icon && <Icon className="h-[18px] w-[18px]" aria-hidden />
      )}
      {children}
    </motion.button>
  );
}
