import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { useApp } from "../state/AppContext.jsx";

export default function Toasts() {
  const { toasts } = useApp();
  return (
    <div className="pointer-events-none fixed inset-x-0 top-3 z-[60] flex flex-col items-center gap-2 px-4">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            layout
            initial={{ opacity: 0, y: -16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.96 }}
            className="pointer-events-auto flex max-w-sm items-center gap-2.5 rounded-2xl bg-raised px-4 py-3 text-sm font-medium shadow-xl ring-1 ring-line"
            role="status"
          >
            {t.tone === "danger" ? (
              <AlertCircle className="h-5 w-5 shrink-0 text-danger" />
            ) : (
              <CheckCircle2 className="h-5 w-5 shrink-0 text-go" />
            )}
            {t.text}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
