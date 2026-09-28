import { AnimatePresence, motion } from "framer-motion";
import { BookmarkPlus, Crown, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../../api/client.js";
import { confirmDialog, haptic } from "../../lib/telegram.js";
import { useApp } from "../../state/AppContext.jsx";
import Button from "../ui/Button.jsx";
import { ErrorNote, Skeleton } from "../ui/Feedback.jsx";
import { Input } from "../ui/Input.jsx";
import Sheet from "../ui/Sheet.jsx";

/**
 * Template library: the user's saved templates (Pro) and the built-in ones.
 * `onPick(text)` inserts a template; `currentText` can be saved as a new one.
 */
export default function TemplatesSheet({ open, onClose, onPick, currentText }) {
  const { pro, openPaywall, toast } = useApp();
  const [templates, setTemplates] = useState(null);
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setError("");
    setTitle("");
    api
      .listTemplates()
      .then(setTemplates)
      .catch((err) => setError(err.message));
  }, [open]);

  async function save() {
    if (!pro?.has_access) {
      openPaywall("Свои шаблоны доступны в Pro");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const created = await api.createTemplate({ title: title.trim(), text: currentText });
      setTemplates((prev) => [created, ...(prev || [])]);
      setTitle("");
      haptic.success();
      toast("Шаблон сохранён");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function remove(template) {
    if (!(await confirmDialog(`Удалить шаблон «${template.title}»?`))) return;
    try {
      await api.deleteTemplate(template.id);
      setTemplates((prev) => prev.filter((t) => t.id !== template.id));
    } catch (err) {
      toast(err.message, "danger");
    }
  }

  const groups = [];
  for (const t of templates || []) {
    let group = groups.find((g) => g.category === t.category);
    if (!group) groups.push((group = { category: t.category, items: [] }));
    group.items.push(t);
  }

  return (
    <Sheet open={open} onClose={onClose} title="Шаблоны">
      <div className="space-y-5 pt-1">
        {currentText?.trim() && (
          <div className="rounded-tile bg-raised/50 p-3">
            <p className="mb-2 flex items-center gap-1.5 text-[13px] font-medium text-muted">
              Сохранить текущий текст как шаблон
              {!pro?.has_access && <Crown className="h-3.5 w-3.5 text-warn" aria-label="Pro" />}
            </p>
            <div className="flex gap-2">
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Название шаблона"
                maxLength={100}
                aria-label="Название шаблона"
                className="!py-2.5"
              />
              <Button
                icon={BookmarkPlus}
                loading={saving}
                disabled={!title.trim()}
                onClick={save}
                aria-label="Сохранить шаблон"
              />
            </div>
          </div>
        )}

        <ErrorNote>{error}</ErrorNote>
        {!templates && !error && (
          <>
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
          </>
        )}

        {groups.map((group) => (
          <section key={group.category}>
            <h3 className="mb-2 text-[13px] font-medium text-muted">{group.category}</h3>
            <div className="space-y-2">
              <AnimatePresence initial={false}>
                {group.items.map((t) => (
                  <motion.div
                    key={t.id}
                    layout
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0, x: -30 }}
                    className="flex items-start gap-2 rounded-tile bg-raised/50 p-3"
                  >
                    <button
                      type="button"
                      className="min-w-0 flex-1 text-left"
                      onClick={() => {
                        haptic.select();
                        onPick(t.text);
                        onClose();
                      }}
                    >
                      <span className="block text-[15px] font-semibold">{t.title}</span>
                      <span className="mt-0.5 line-clamp-2 block text-[13px] leading-snug text-muted">
                        {t.text.replace(/<[^>]+>/g, "")}
                      </span>
                    </button>
                    {!t.builtin && (
                      <button
                        type="button"
                        onClick={() => remove(t)}
                        className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-faint hover:text-danger"
                        aria-label={`Удалить шаблон «${t.title}»`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </section>
        ))}
      </div>
    </Sheet>
  );
}
