import { AnimatePresence, motion } from "framer-motion";
import { Crown, MessageCircleReply, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import ChipsInput from "../components/composer/ChipsInput.jsx";
import ChoiceChips from "../components/composer/ChoiceChips.jsx";
import MessagePreview from "../components/composer/MessagePreview.jsx";
import PhotoPicker from "../components/composer/PhotoPicker.jsx";
import { photoRefs, photosFromUrls } from "../components/composer/photos.js";
import RichTextEditor from "../components/composer/RichTextEditor.jsx";
import NeedAccount from "../components/NeedAccount.jsx";
import PageTitle from "../components/PageTitle.jsx";
import Button from "../components/ui/Button.jsx";
import { EmptyState, ErrorNote, Skeleton } from "../components/ui/Feedback.jsx";
import { Field, Label } from "../components/ui/Input.jsx";
import Segmented from "../components/ui/Segmented.jsx";
import Sheet from "../components/ui/Sheet.jsx";
import Switch from "../components/ui/Switch.jsx";
import { confirmDialog, haptic } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";

const COOLDOWNS = [
  { value: 1, label: "1 час" },
  { value: 3, label: "3 часа" },
  { value: 6, label: "6 часов" },
  { value: 12, label: "12 часов" },
  { value: 24, label: "Сутки" },
];

const emptyForm = {
  triggerType: "all",
  keywords: [],
  responseText: "",
  cooldownHours: 3,
  photos: [],
};

function ruleToForm(rule) {
  return {
    triggerType: rule.trigger_type,
    keywords: rule.keywords,
    responseText: rule.response_text,
    cooldownHours: Math.max(1, Math.round(rule.cooldown_seconds / 3600)),
    photos: photosFromUrls(rule.photo_urls),
  };
}

function formToPayload(form) {
  return {
    trigger_type: form.triggerType,
    keywords: form.triggerType === "keywords" ? form.keywords : [],
    response_text: form.responseText,
    photos: photoRefs(form.photos),
    cooldown_seconds: Math.max(1, Number(form.cooldownHours)) * 3600,
  };
}

function RuleSheet({ open, rule, onClose, onSave, onDelete }) {
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm(rule ? ruleToForm(rule) : emptyForm);
      setError("");
    }
  }, [open, rule]);

  const set = (patch) => setForm((f) => ({ ...f, ...patch }));
  const invalid =
    !form.responseText.trim() || (form.triggerType === "keywords" && form.keywords.length === 0);

  async function save() {
    setError("");
    setSaving(true);
    try {
      await onSave(formToPayload(form));
      haptic.success();
    } catch (err) {
      haptic.error();
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={rule ? "Правило автоответа" : "Новое правило"}
      footer={
        <div className="flex gap-2">
          {rule && (
            <Button
              variant="danger"
              icon={Trash2}
              onClick={() => onDelete(rule)}
              aria-label="Удалить правило"
            />
          )}
          <Button className="flex-1" loading={saving} disabled={invalid} onClick={save}>
            {rule ? "Сохранить" : "Добавить правило"}
          </Button>
        </div>
      }
    >
      <div className="space-y-5 pt-1">
        <div>
          <Label>Когда отвечать</Label>
          <Segmented
            value={form.triggerType}
            onChange={(v) => set({ triggerType: v })}
            options={[
              { value: "all", label: "Любое сообщение" },
              { value: "keywords", label: "По словам" },
            ]}
          />
        </div>

        <AnimatePresence initial={false}>
          {form.triggerType === "keywords" && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
            >
              <Field label="Ключевые слова" hint="Enter или запятая" htmlFor="kw">
                <ChipsInput
                  id="kw"
                  value={form.keywords}
                  onChange={(keywords) => set({ keywords })}
                  placeholder="цена, доставка, купить"
                />
              </Field>
            </motion.div>
          )}
        </AnimatePresence>

        <Field label="Ответ" htmlFor="reply">
          <RichTextEditor
            id="reply"
            value={form.responseText}
            onChange={(responseText) => set({ responseText })}
            limit={4096}
            placeholder="{Здравствуйте|Добрый день}! Сейчас не на связи — отвечу в течение часа."
          />
        </Field>

        <Field label="Фото">
          <PhotoPicker value={form.photos} onChange={(photos) => set({ photos })} />
        </Field>

        <div>
          <Label>Не отвечать одному человеку повторно</Label>
          <ChoiceChips
            value={form.cooldownHours}
            onChange={(cooldownHours) => set({ cooldownHours })}
            options={COOLDOWNS}
          />
        </div>

        {(form.responseText || form.photos.length > 0) && (
          <div>
            <Label>Так увидит собеседник</Label>
            <MessagePreview text={form.responseText} photos={form.photos} />
          </div>
        )}

        <ErrorNote>{error}</ErrorNote>
      </div>
    </Sheet>
  );
}

function RuleRow({ rule, onOpen, onToggle }) {
  const preview = rule.response_text.replace(/<[^>]+>/g, "");
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -40 }}
      className="flex items-center gap-3 rounded-[18px] bg-surface p-4"
    >
      <button type="button" onClick={() => onOpen(rule)} className="min-w-0 flex-1 text-left">
        <div className="mb-1 flex flex-wrap gap-1.5">
          {rule.trigger_type === "all" ? (
            <span className="rounded-md bg-sky/12 px-2 py-0.5 text-xs font-semibold text-sky">
              любое сообщение
            </span>
          ) : (
            rule.keywords.slice(0, 4).map((k) => (
              <span
                key={k}
                className="rounded-md bg-raised px-2 py-0.5 text-xs font-medium text-muted"
              >
                {k}
              </span>
            ))
          )}
        </div>
        <p
          className={`line-clamp-2 text-[15px] leading-snug ${rule.is_enabled ? "" : "text-faint"}`}
        >
          {preview}
        </p>
        <p className="mt-1.5 text-xs text-faint">
          {rule.photo_urls.length > 0 &&
            `${rule.photo_urls.length > 1 ? `Альбом, ${rule.photo_urls.length} фото` : "С фото"} · `}
          повтор не чаще раза в {Math.round(rule.cooldown_seconds / 3600)} ч
        </p>
      </button>
      <Switch
        checked={rule.is_enabled}
        onChange={(v) => onToggle(rule, v)}
        label="Правило включено"
      />
    </motion.div>
  );
}

export default function AutoresponderPage() {
  const { activeAccount, pro, openPaywall, toast } = useApp();
  const [rules, setRules] = useState(null);
  const [error, setError] = useState("");
  const [sheet, setSheet] = useState({ open: false, rule: null });

  const accountId = activeAccount?.id;

  useEffect(() => {
    if (!accountId) return;
    setRules(null);
    api
      .listRules(accountId)
      .then(setRules)
      .catch((err) => {
        setError(err.message);
        setRules([]);
      });
  }, [accountId]);

  if (!activeAccount) return <NeedAccount title="Автоответчик" />;

  const limit = pro && !pro.has_access ? pro.free_max_rules : null;
  const atLimit = limit != null && rules && rules.length >= limit;

  function openNew() {
    if (atLimit) {
      openPaywall(`Без Pro — до ${limit} правил на аккаунт`);
      return;
    }
    setSheet({ open: true, rule: null });
  }

  async function save(payload) {
    if (sheet.rule) {
      const updated = await api.updateRule(accountId, sheet.rule.id, payload);
      setRules((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      toast("Правило сохранено");
    } else {
      const created = await api.createRule(accountId, payload);
      setRules((prev) => [...prev, created]);
      toast("Правило добавлено");
    }
    setSheet({ open: false, rule: null });
  }

  async function remove(rule) {
    if (!(await confirmDialog("Удалить это правило?"))) return;
    try {
      await api.deleteRule(accountId, rule.id);
      setRules((prev) => prev.filter((r) => r.id !== rule.id));
      setSheet({ open: false, rule: null });
      toast("Правило удалено");
    } catch (err) {
      toast(err.message, "danger");
    }
  }

  async function toggle(rule, isEnabled) {
    setRules((prev) => prev.map((r) => (r.id === rule.id ? { ...r, is_enabled: isEnabled } : r)));
    try {
      await api.updateRule(accountId, rule.id, { is_enabled: isEnabled });
    } catch (err) {
      setRules((prev) => prev.map((r) => (r.id === rule.id ? rule : r)));
      toast(err.message, "danger");
    }
  }

  return (
    <div className="space-y-4 p-4">
      <PageTitle
        title="Автоответчик"
        subtitle="Отвечает в личных сообщениях, пока вы заняты"
        action={
          rules?.length > 0 && (
            <Button size="sm" icon={atLimit ? Crown : Plus} onClick={openNew}>
              Правило
            </Button>
          )
        }
      />

      <ErrorNote>{error}</ErrorNote>

      {rules === null ? (
        <div className="space-y-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      ) : rules.length === 0 ? (
        <EmptyState
          icon={MessageCircleReply}
          title="Первое правило — за минуту"
          text="Например: на любое сообщение отвечать «Сейчас не на связи, отвечу в течение часа»."
          action={
            <Button icon={Plus} onClick={openNew}>
              Добавить правило
            </Button>
          }
        />
      ) : (
        <div className="space-y-2.5">
          <AnimatePresence initial={false}>
            {rules.map((rule) => (
              <RuleRow
                key={rule.id}
                rule={rule}
                onOpen={(r) => setSheet({ open: true, rule: r })}
                onToggle={toggle}
              />
            ))}
          </AnimatePresence>
          {limit != null && (
            <p className="px-1 pt-1 text-[13px] text-faint">
              {rules.length} из {limit} правил на бесплатном тарифе.{" "}
              <button
                type="button"
                className="font-semibold text-sky"
                onClick={() => openPaywall()}
              >
                Безлимит в Pro
              </button>
            </p>
          )}
          <p className="px-1 text-[13px] leading-snug text-faint">
            Если подходят несколько правил, срабатывает первое в списке. Ботам автопилот не
            отвечает.
          </p>
        </div>
      )}

      <RuleSheet
        open={sheet.open}
        rule={sheet.rule}
        onClose={() => setSheet({ open: false, rule: null })}
        onSave={save}
        onDelete={remove}
      />
    </div>
  );
}
