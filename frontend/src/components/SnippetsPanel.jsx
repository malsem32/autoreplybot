import { AnimatePresence, motion } from "framer-motion";
import { Crown, Plus, Trash2, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { confirmDialog, haptic } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";
import PhotoPicker from "./composer/PhotoPicker.jsx";
import { photoRefs, photosFromUrls } from "./composer/photos.js";
import RichTextEditor from "./composer/RichTextEditor.jsx";
import Button from "./ui/Button.jsx";
import { EmptyState, ErrorNote, Skeleton } from "./ui/Feedback.jsx";
import { Field, Input } from "./ui/Input.jsx";
import Sheet from "./ui/Sheet.jsx";

const SHORTCUT_RE = /^[0-9a-zа-яё_]{1,32}$/;

function SnippetSheet({ open, snippet, onClose, onSave, onDelete }) {
  const [shortcut, setShortcut] = useState("");
  const [text, setText] = useState("");
  const [photos, setPhotos] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setShortcut(snippet?.shortcut || "");
    setText(snippet?.text || "");
    setPhotos(photosFromUrls(snippet?.photo_urls || []));
    setError("");
  }, [open, snippet]);

  const normalized = shortcut.trim().replace(/^!/, "").toLowerCase();
  const valid = SHORTCUT_RE.test(normalized) && text.trim();

  async function save() {
    setSaving(true);
    setError("");
    try {
      await onSave({ shortcut: normalized, text, photos: photoRefs(photos) });
      haptic.success();
    } catch (err) {
      setError(err.message);
      haptic.error();
    } finally {
      setSaving(false);
    }
  }

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={snippet ? `!${snippet.shortcut}` : "Новая фраза"}
      footer={
        <div className="flex gap-2">
          {snippet && (
            <Button
              variant="danger"
              icon={Trash2}
              onClick={() => onDelete(snippet)}
              aria-label="Удалить"
            />
          )}
          <Button className="flex-1" loading={saving} disabled={!valid} onClick={save}>
            Сохранить
          </Button>
        </div>
      }
    >
      <div className="space-y-4 pt-1">
        <Field label="Сокращение" hint="буквы, цифры и _, без пробелов" htmlFor="snippet-shortcut">
          <div className="relative">
            <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-[15px] font-semibold text-sky">
              !
            </span>
            <Input
              id="snippet-shortcut"
              value={shortcut.replace(/^!/, "")}
              onChange={(e) => setShortcut(e.target.value)}
              placeholder="цена"
              autoCapitalize="none"
              autoComplete="off"
              className="pl-7"
            />
          </div>
        </Field>
        <Field label="Текст" htmlFor="snippet-text">
          <RichTextEditor
            id="snippet-text"
            value={text}
            onChange={setText}
            limit={4096}
            placeholder="Стоимость доставки по городу — 300 ₽, бесплатно от 3000 ₽."
          />
        </Field>
        <Field label="Фото">
          <PhotoPicker value={photos} onChange={setPhotos} />
        </Field>
        <ErrorNote>{error}</ErrorNote>
      </div>
    </Sheet>
  );
}

/** Quick phrases: type `!shortcut` in any Telegram chat and the autopilot
 * swaps it for the saved text (workers/snippets.py). */
export default function SnippetsPanel({ accountId }) {
  const { openPaywall, toast } = useApp();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [sheet, setSheet] = useState({ open: false, snippet: null });

  useEffect(() => {
    setData(null);
    api
      .listSnippets(accountId)
      .then(setData)
      .catch((err) => {
        setError(err.message);
        setData({ snippets: [], limit: null });
      });
  }, [accountId]);

  const atLimit = data?.limit != null && data.snippets.length >= data.limit;

  function openNew() {
    if (atLimit) {
      openPaywall(`Без Pro — до ${data.limit} быстрых фраз`);
      return;
    }
    setSheet({ open: true, snippet: null });
  }

  async function save(payload) {
    if (sheet.snippet) {
      const updated = await api.updateSnippet(accountId, sheet.snippet.id, payload);
      setData((d) => ({
        ...d,
        snippets: d.snippets.map((s) => (s.id === updated.id ? updated : s)),
      }));
    } else {
      const created = await api.createSnippet(accountId, payload);
      setData((d) => ({ ...d, snippets: [...d.snippets, created] }));
    }
    toast("Фраза сохранена");
    setSheet({ open: false, snippet: null });
  }

  async function remove(snippet) {
    if (!(await confirmDialog(`Удалить фразу !${snippet.shortcut}?`))) return;
    try {
      await api.deleteSnippet(accountId, snippet.id);
      setData((d) => ({ ...d, snippets: d.snippets.filter((s) => s.id !== snippet.id) }));
      setSheet({ open: false, snippet: null });
      toast("Фраза удалена");
    } catch (err) {
      toast(err.message, "danger");
    }
  }

  return (
    <div className="space-y-3">
      <div className="rounded-[18px] bg-surface p-4">
        <p className="flex items-center gap-2 text-[15px] font-semibold">
          <Zap className="h-4 w-4 text-sky" aria-hidden /> Как это работает
        </p>
        <p className="mt-1.5 text-[14px] leading-snug text-muted">
          Напишите в любом чате <b className="text-ink">!цена</b> — автопилот тут же заменит это
          сообщение на сохранённый текст с фото. Работает с телефона и компьютера.
        </p>
      </div>
      <ErrorNote>{error}</ErrorNote>
      {data === null ? (
        <Skeleton className="h-20" />
      ) : data.snippets.length === 0 ? (
        <EmptyState
          icon={Zap}
          title="Ни одной фразы"
          text="Сохраните ответы, которые пишете чаще всего: цены, реквизиты, адрес, условия доставки."
          action={
            <Button icon={Plus} onClick={openNew}>
              Добавить фразу
            </Button>
          }
        />
      ) : (
        <>
          <AnimatePresence initial={false}>
            {data.snippets.map((s) => (
              <motion.button
                key={s.id}
                type="button"
                layout
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -40 }}
                onClick={() => setSheet({ open: true, snippet: s })}
                className="flex w-full items-center gap-3 rounded-[18px] bg-surface p-4 text-left"
              >
                <span className="shrink-0 rounded-lg bg-sky/12 px-2.5 py-1 font-mono text-[14px] font-semibold text-sky">
                  !{s.shortcut}
                </span>
                <span className="line-clamp-2 min-w-0 flex-1 text-[14px] leading-snug text-muted">
                  {s.photo_urls.length > 0 && "🖼 "}
                  {s.text.replace(/<[^>]+>/g, "")}
                </span>
              </motion.button>
            ))}
          </AnimatePresence>
          <Button
            variant="secondary"
            className="w-full"
            icon={atLimit ? Crown : Plus}
            onClick={openNew}
          >
            Добавить фразу
          </Button>
          {data.limit != null && (
            <p className="px-1 text-[13px] text-faint">
              {data.snippets.length} из {data.limit} фраз на бесплатном тарифе. Безлимит — в Pro.
            </p>
          )}
        </>
      )}
      <SnippetSheet
        open={sheet.open}
        snippet={sheet.snippet}
        onClose={() => setSheet({ open: false, snippet: null })}
        onSave={save}
        onDelete={remove}
      />
    </div>
  );
}
