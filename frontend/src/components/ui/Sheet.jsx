import { AnimatePresence, motion, useDragControls, useIsPresent } from "framer-motion";
import { X } from "lucide-react";
import { useEffect } from "react";
import { createPortal } from "react-dom";
import { bindBackButton } from "../../lib/telegram.js";

/** While the closing animation plays the sheet must not catch taps meant
 * for the page underneath. */
function SheetFrame({ children }) {
  const present = useIsPresent();
  return (
    <div
      className={`fixed inset-0 z-50 flex items-end justify-center ${present ? "" : "pointer-events-none"}`}
      role="dialog"
      aria-modal
    >
      {children}
    </div>
  );
}

/** Bottom sheet: slides up over the page, closes by drag-down, backdrop
 * tap, the ✕ or Telegram's native back button. */
export default function Sheet({ open, onClose, title, children, footer }) {
  const drag = useDragControls();

  useEffect(() => {
    if (!open) return undefined;
    const unbind = bindBackButton(onClose);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      unbind();
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  return createPortal(
    <AnimatePresence>
      {open && (
        <SheetFrame>
          <motion.div
            className="absolute inset-0 bg-black/55"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="relative flex w-full max-w-lg flex-col rounded-t-sheet bg-surface shadow-2xl"
            style={{ maxHeight: "calc(100% - var(--inset-top) - 12px)" }}
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 380, damping: 38 }}
            drag="y"
            dragListener={false}
            dragControls={drag}
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0, bottom: 0.6 }}
            onDragEnd={(_, info) => {
              if (info.offset.y > 120 || info.velocity.y > 600) onClose();
            }}
          >
            <div
              className="flex cursor-grab touch-none flex-col items-center pt-2.5"
              onPointerDown={(e) => drag.start(e)}
            >
              <span className="h-1.5 w-10 rounded-full bg-line" />
              <div className="flex w-full items-center justify-between px-5 pb-2 pt-3">
                <h2 className="font-display text-[17px] font-semibold tracking-tight">{title}</h2>
                <button
                  type="button"
                  onClick={onClose}
                  className="grid h-8 w-8 place-items-center rounded-full bg-raised text-muted"
                  aria-label="Закрыть"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
            <div
              className="overflow-y-auto overscroll-contain px-5"
              style={{ paddingBottom: footer ? "1.25rem" : "calc(1.25rem + var(--inset-bottom))" }}
            >
              {children}
            </div>
            {footer && (
              <div
                className="border-t border-line/60 px-5 pt-3"
                style={{ paddingBottom: "calc(0.75rem + var(--inset-bottom))" }}
              >
                {footer}
              </div>
            )}
          </motion.div>
        </SheetFrame>
      )}
    </AnimatePresence>,
    document.body,
  );
}
