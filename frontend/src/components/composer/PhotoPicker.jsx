import { AnimatePresence, motion } from "framer-motion";
import { Crown, ImagePlus, Loader2, Star, X } from "lucide-react";
import { useRef, useState } from "react";
import { api } from "../../api/client.js";
import { haptic } from "../../lib/telegram.js";
import { useApp } from "../../state/AppContext.jsx";

const ACCEPT = "image/jpeg,image/png,image/webp";
const MAX_BYTES = 10 * 1024 * 1024;

/**
 * Multi-photo picker. `value` is a list of `{ ref, url }` where `ref` is what
 * the backend accepts back (upload path or /api/uploads/… URL). 2+ photos are
 * sent as a Telegram album; the first one is the cover and carries the text.
 */
export default function PhotoPicker({ value, onChange }) {
  const { pro, openPaywall } = useApp();
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(0);
  const [error, setError] = useState("");

  const maxPhotos = pro?.max_photos ?? 1;
  const hardMax = 10;
  const canAddFree = value.length < maxPhotos;

  function pick() {
    if (!canAddFree) {
      if (value.length >= hardMax) return;
      openPaywall("Альбомы до 10 фото доступны в Pro");
      return;
    }
    inputRef.current?.click();
  }

  async function handleFiles(e) {
    const files = Array.from(e.target.files || []);
    e.target.value = "";
    if (!files.length) return;
    setError("");

    const room = maxPhotos - value.length;
    const batch = files.slice(0, room);
    if (files.length > room) {
      setError(
        maxPhotos > 1
          ? `Можно прикрепить не больше ${maxPhotos} фото`
          : "Без Pro — одно фото. Альбомы до 10 фото доступны в Pro",
      );
    }

    let current = value;
    for (const file of batch) {
      if (file.size > MAX_BYTES) {
        setError("Файл больше 10 МБ — выберите фото поменьше");
        continue;
      }
      setUploading((n) => n + 1);
      try {
        const { path, url } = await api.uploadPhoto(file);
        current = [...current, { ref: path, url }];
        onChange(current);
        haptic.tap();
      } catch (err) {
        setError(err.message);
      } finally {
        setUploading((n) => n - 1);
      }
    }
  }

  function remove(index) {
    haptic.tap();
    onChange(value.filter((_, i) => i !== index));
  }

  function makeCover(index) {
    if (index === 0) return;
    haptic.select();
    const next = [...value];
    const [item] = next.splice(index, 1);
    onChange([item, ...next]);
  }

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        multiple
        className="hidden"
        onChange={handleFiles}
      />
      <div className="grid grid-cols-4 gap-2">
        <AnimatePresence initial={false}>
          {value.map((photo, index) => (
            <motion.div
              key={photo.url}
              layout
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="relative aspect-square"
            >
              <button
                type="button"
                onClick={() => makeCover(index)}
                className="block h-full w-full overflow-hidden rounded-xl"
                aria-label={index === 0 ? "Обложка альбома" : "Сделать обложкой"}
              >
                <img src={photo.url} alt="" className="h-full w-full object-cover" />
              </button>
              {index === 0 && value.length > 1 && (
                <span className="absolute bottom-1 left-1 inline-flex items-center gap-0.5 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                  <Star className="h-2.5 w-2.5" /> обложка
                </span>
              )}
              <button
                type="button"
                onClick={() => remove(index)}
                className="absolute -right-1.5 -top-1.5 grid h-6 w-6 place-items-center rounded-full bg-bg text-ink shadow ring-1 ring-line"
                aria-label="Убрать фото"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>

        {Array.from({ length: uploading }).map((_, i) => (
          <div
            key={`up-${i}`}
            className="grid aspect-square place-items-center rounded-xl bg-raised/60"
          >
            <Loader2 className="h-5 w-5 animate-spin text-sky" aria-label="Загрузка" />
          </div>
        ))}

        {value.length + uploading < hardMax && (
          <button
            type="button"
            onClick={pick}
            className="relative grid aspect-square place-items-center rounded-xl border-2 border-dashed border-line text-muted transition-colors hover:border-sky hover:text-sky"
            aria-label="Добавить фото"
          >
            <span className="flex flex-col items-center gap-1">
              <ImagePlus className="h-6 w-6" />
              <span className="text-[11px] font-medium tabular-nums">
                {value.length}/{maxPhotos}
              </span>
            </span>
            {!canAddFree && (
              <Crown
                className="absolute right-1.5 top-1.5 h-3.5 w-3.5 text-warn"
                aria-label="Pro"
              />
            )}
          </button>
        )}
      </div>
      {value.length > 1 && (
        <p className="mt-2 text-xs text-faint">
          Уйдёт альбомом. Нажмите на фото, чтобы сделать его обложкой.
        </p>
      )}
      {error && <p className="mt-2 text-[13px] text-warn">{error}</p>}
    </div>
  );
}
