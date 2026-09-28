import { AnimatePresence, motion } from "framer-motion";
import {
  Bold,
  Check,
  Code,
  EyeOff,
  Italic,
  Link2,
  Quote,
  Shuffle,
  Strikethrough,
  Underline,
  X,
} from "lucide-react";
import { useRef, useState } from "react";
import { haptic } from "../../lib/telegram.js";
import { visibleLength } from "../../lib/telegramHtml.js";
import { Input } from "../ui/Input.jsx";

const TOOLS = [
  { id: "b", icon: Bold, label: "Жирный", open: "<b>", close: "</b>" },
  { id: "i", icon: Italic, label: "Курсив", open: "<i>", close: "</i>" },
  { id: "u", icon: Underline, label: "Подчёркнутый", open: "<u>", close: "</u>" },
  { id: "s", icon: Strikethrough, label: "Зачёркнутый", open: "<s>", close: "</s>" },
  { id: "spoiler", icon: EyeOff, label: "Спойлер", open: "<tg-spoiler>", close: "</tg-spoiler>" },
  { id: "code", icon: Code, label: "Моноширинный", open: "<code>", close: "</code>" },
  { id: "quote", icon: Quote, label: "Цитата", open: "<blockquote>", close: "</blockquote>" },
];

/** Plain textarea + a toolbar that wraps the selection in Telegram HTML
 * tags. Chosen over a contenteditable editor: what is stored and sent is
 * exactly what the user sees in the field, with no hidden markup drift. */
export default function RichTextEditor({ value, onChange, limit, placeholder, id }) {
  const ref = useRef(null);
  const [linkOpen, setLinkOpen] = useState(false);
  const [url, setUrl] = useState("https://");
  const [savedRange, setSavedRange] = useState([0, 0]);

  function wrap(open, close, fallback = "текст") {
    const el = ref.current;
    const start = el?.selectionStart ?? value.length;
    const end = el?.selectionEnd ?? value.length;
    const selected = value.slice(start, end) || fallback;
    const next = value.slice(0, start) + open + selected + close + value.slice(end);
    onChange(next);
    haptic.select();
    requestAnimationFrame(() => {
      el?.focus();
      el?.setSelectionRange(start + open.length, start + open.length + selected.length);
    });
  }

  function openLink() {
    const el = ref.current;
    setSavedRange([el?.selectionStart ?? value.length, el?.selectionEnd ?? value.length]);
    setUrl("https://");
    setLinkOpen(true);
  }

  function applyLink() {
    const [start, end] = savedRange;
    const selected = value.slice(start, end) || "ссылка";
    const safeUrl = url.trim().replace(/"/g, "%22");
    const tag = `<a href="${safeUrl}">${selected}</a>`;
    onChange(value.slice(0, start) + tag + value.slice(end));
    setLinkOpen(false);
    haptic.success();
  }

  const length = visibleLength(value);
  const over = limit && length > limit;

  return (
    <div className="overflow-hidden rounded-tile border border-line bg-raised/40 focus-within:border-sky">
      <div className="flex items-center gap-0.5 overflow-x-auto border-b border-line/70 px-1.5 py-1.5 [scrollbar-width:none]">
        {TOOLS.map((tool) => (
          <button
            key={tool.id}
            type="button"
            title={tool.label}
            aria-label={tool.label}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => wrap(tool.open, tool.close)}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-muted transition-colors hover:bg-raised hover:text-ink active:bg-sky/15 active:text-sky"
          >
            <tool.icon className="h-[18px] w-[18px]" />
          </button>
        ))}
        <button
          type="button"
          title="Ссылка"
          aria-label="Ссылка"
          onMouseDown={(e) => e.preventDefault()}
          onClick={openLink}
          className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-muted hover:bg-raised hover:text-ink"
        >
          <Link2 className="h-[18px] w-[18px]" />
        </button>
        <span className="mx-1 h-5 w-px shrink-0 bg-line" />
        <button
          type="button"
          title="Варианты текста: каждому получателю — случайный"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => wrap("{", "|вариант 2}", "вариант 1")}
          className="flex h-9 shrink-0 items-center gap-1.5 rounded-lg px-2.5 text-[13px] font-semibold text-muted hover:bg-raised hover:text-ink"
        >
          <Shuffle className="h-4 w-4" /> Варианты
        </button>
      </div>

      <AnimatePresence>
        {linkOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="flex items-center gap-2 border-b border-line/70 bg-surface/60 px-2 py-2"
          >
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              inputMode="url"
              aria-label="Адрес ссылки"
              autoFocus
              className="!py-2"
            />
            <button
              type="button"
              onClick={applyLink}
              className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-sky text-onsky"
              aria-label="Вставить ссылку"
            >
              <Check className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={() => setLinkOpen(false)}
              className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-raised text-muted"
              aria-label="Отмена"
            >
              <X className="h-5 w-5" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <textarea
        id={id}
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="block min-h-[140px] w-full resize-y bg-transparent px-3.5 py-3 text-[15px] leading-relaxed text-ink placeholder:text-faint focus:outline-none focus-visible:ring-0 focus-visible:ring-offset-0"
      />
      {limit && (
        <div className="flex justify-end px-3 pb-2">
          <span
            className={`text-xs tabular-nums ${over ? "font-semibold text-warn" : "text-faint"}`}
          >
            {length} / {limit}
          </span>
        </div>
      )}
    </div>
  );
}
