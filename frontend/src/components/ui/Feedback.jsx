import { motion } from "framer-motion";

export function Skeleton({ className = "" }) {
  return (
    <div className={`relative overflow-hidden rounded-tile bg-surface ${className}`}>
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-ink/5 to-transparent" />
    </div>
  );
}

export function EmptyState({ icon: Icon, title, text, action }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center rounded-[22px] border border-dashed border-line px-6 py-10 text-center"
    >
      {Icon && (
        <span className="mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-sky/12 text-sky">
          <Icon className="h-7 w-7" aria-hidden />
        </span>
      )}
      <p className="font-display text-base font-semibold">{title}</p>
      {text && <p className="mt-1.5 max-w-[30ch] text-sm leading-relaxed text-muted">{text}</p>}
      {action && <div className="mt-5">{action}</div>}
    </motion.div>
  );
}

export function ErrorNote({ children }) {
  if (!children) return null;
  return (
    <motion.p
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-tile bg-danger/10 px-3.5 py-2.5 text-[13px] leading-snug text-danger"
      role="alert"
    >
      {children}
    </motion.p>
  );
}

const TONES = {
  go: "bg-go/15 text-go",
  warn: "bg-warn/15 text-warn",
  muted: "bg-line/60 text-muted",
  sky: "bg-sky/15 text-sky",
  danger: "bg-danger/15 text-danger",
};

export function Pill({ tone = "muted", children, dot }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${TONES[tone]}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}
