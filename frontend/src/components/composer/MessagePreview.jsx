import { Shuffle } from "lucide-react";
import { useMemo, useState } from "react";
import { renderSpintax, renderTelegramHtml } from "../../lib/telegramHtml.js";

function AlbumGrid({ photos }) {
  const n = photos.length;
  if (!n) return null;
  const cols = n === 1 ? "grid-cols-1" : n === 2 || n === 4 ? "grid-cols-2" : "grid-cols-3";
  return (
    <div className={`grid gap-0.5 ${cols}`}>
      {photos.slice(0, 10).map((p, i) => (
        <img
          key={p.url}
          src={p.url}
          alt=""
          className={`w-full object-cover ${n === 1 ? "max-h-64" : "aspect-square"} ${n === 3 && i === 0 ? "col-span-3 aspect-[2/1]" : ""}`}
        />
      ))}
    </div>
  );
}

/** Telegram-style outgoing bubble showing how the message will look. */
export default function MessagePreview({ text, photos = [], signature }) {
  const [seed, setSeed] = useState(0);
  const hasSpintax = /\{[^{}]*\|[^{}]*\}/.test(text);

  const html = useMemo(() => {
    const resolved = renderSpintax(text || "");
    const full = signature ? `${resolved}\n\n${signature}` : resolved;
    return renderTelegramHtml(full);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, signature, seed]);

  return (
    <div className="rounded-[18px] bg-[linear-gradient(135deg,rgb(var(--raised)/0.6),rgb(var(--bg)/0.4))] p-3">
      <div className="ml-auto max-w-[88%] overflow-hidden rounded-[16px] rounded-br-[5px] bg-sky/90 text-onsky shadow-md">
        <AlbumGrid photos={photos} />
        {(text || signature) && (
          <div
            className="tg-preview break-words px-3 py-2 text-[15px] leading-snug [&_a]:!text-onsky [&_a]:underline [&_blockquote]:!border-onsky/60 [&_code]:!bg-black/15"
            onClick={(e) => {
              if (e.target.classList?.contains("spoiler")) e.target.classList.toggle("revealed");
            }}
            dangerouslySetInnerHTML={{ __html: html || "&nbsp;" }}
          />
        )}
      </div>
      {hasSpintax && (
        <button
          type="button"
          onClick={() => setSeed((s) => s + 1)}
          className="mt-2 inline-flex items-center gap-1.5 text-[13px] font-semibold text-sky"
        >
          <Shuffle className="h-3.5 w-3.5" /> Показать другой вариант
        </button>
      )}
    </div>
  );
}
