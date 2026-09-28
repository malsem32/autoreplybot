import { AnimatePresence, motion } from "framer-motion";
import {
  BellRing,
  Clock,
  Crown,
  Hand,
  Keyboard,
  MessageCircleReply,
  Plus,
  FlaskConical,
  Sparkles,
  Trash2,
  UserPlus,
  UsersRound,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import ChipsInput from "../components/composer/ChipsInput.jsx";
import ChoiceChips from "../components/composer/ChoiceChips.jsx";
import MessagePreview from "../components/composer/MessagePreview.jsx";
import PhotoPicker from "../components/composer/PhotoPicker.jsx";
import { photoRefs, photosFromUrls } from "../components/composer/photos.js";
import RichTextEditor from "../components/composer/RichTextEditor.jsx";
import AiPanel from "../components/AiPanel.jsx";
import NeedAccount from "../components/NeedAccount.jsx";
import PageTitle from "../components/PageTitle.jsx";
import SnippetsPanel from "../components/SnippetsPanel.jsx";
import OptionRow from "../components/pro/OptionRow.jsx";
import Button from "../components/ui/Button.jsx";
import { EmptyState, ErrorNote, Skeleton } from "../components/ui/Feedback.jsx";
import { Field, Input, Label } from "../components/ui/Input.jsx";
import { ListGroup } from "../components/ui/List.jsx";
import Segmented from "../components/ui/Segmented.jsx";
import Sheet from "../components/ui/Sheet.jsx";
import Switch from "../components/ui/Switch.jsx";
import plural from "../lib/plural.js";
import { confirmDialog, haptic } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";

const COOLDOWNS = [
  { value: 1, label: "1 час" },
  { value: 3, label: "3 часа" },
  { value: 6, label: "6 часов" },
  { value: 12, label: "12 часов" },
  { value: 24, label: "Сутки" },
];

const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

const ACTIVE_WINDOWS = [
  { value: 15, label: "15 мин" },
  { value: 30, label: "30 мин" },
  { value: 60, label: "1 час" },
  { value: 180, label: "3 часа" },
];

const TYPING_DELAYS = [
  { value: 3, label: "3 сек" },
  { value: 5, label: "5 сек" },
  { value: 10, label: "10 сек" },
  { value: 20, label: "20 сек" },
];

function browserTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Moscow";
  } catch {
    return "Europe/Moscow";
  }
}

const MATCH_MODES = [
  { value: "contains", label: "Содержит" },
  { value: "word", label: "Целое слово" },
  { value: "exact", label: "Точно" },
];

const MATCH_HINTS = {
  contains: "«цен» сработает на «цена», «ценник», «бесценно»",
  word: "«цена» сработает на «а цена?», но не на «ценами»",
  exact: "Сообщение должно совпадать со словом целиком",
};

const emptyForm = () => ({
  triggerType: "all",
  matchMode: "contains",
  scope: "private",
  keywords: [],
  responseText: "",
  cooldownHours: 3,
  photos: [],
  scheduleEnabled: false,
  scheduleDays: [0, 1, 2, 3, 4, 5, 6],
  scheduleStart: "19:00",
  scheduleEnd: "09:00",
  timezone: browserTimezone(),
  newContactsOnly: false,
  skipActiveMinutes: 0,
  typingDelay: 0,
  notifyOwner: false,
  aiReply: false,
});

function ruleToForm(rule) {
  return {
    triggerType: rule.trigger_type,
    matchMode: rule.match_mode,
    scope: rule.scope,
    keywords: rule.keywords,
    responseText: rule.response_text,
    cooldownHours: Math.max(1, Math.round(rule.cooldown_seconds / 3600)),
    photos: photosFromUrls(rule.photo_urls),
    scheduleEnabled: rule.schedule_enabled,
    scheduleDays: rule.schedule_days,
    scheduleStart: rule.schedule_start,
    scheduleEnd: rule.schedule_end,
    timezone: rule.timezone,
    newContactsOnly: rule.new_contacts_only,
    skipActiveMinutes: rule.skip_if_owner_active_minutes,
    typingDelay: rule.typing_delay_seconds,
    notifyOwner: rule.notify_owner,
    aiReply: rule.ai_reply,
  };
}

function formToPayload(form, hasPro) {
  return {
    trigger_type: form.triggerType,
    keywords: form.triggerType === "keywords" ? form.keywords : [],
    match_mode: form.matchMode,
    scope: hasPro ? form.scope : "private",
    response_text: form.responseText,
    photos: photoRefs(form.photos),
    cooldown_seconds: Math.max(1, Number(form.cooldownHours)) * 3600,
    schedule_days: form.scheduleDays,
    schedule_start: form.scheduleStart,
    schedule_end: form.scheduleEnd,
    timezone: form.timezone,
    // Pro options saved earlier are switched off on edit once Pro expires,
    // instead of blocking the whole save (the backend would answer 402).
    schedule_enabled: hasPro && form.scheduleEnabled,
    new_contacts_only: hasPro && form.newContactsOnly,
    skip_if_owner_active_minutes: hasPro ? form.skipActiveMinutes : 0,
    typing_delay_seconds: hasPro ? form.typingDelay : 0,
    notify_owner: hasPro && form.notifyOwner,
    ai_reply: hasPro && form.aiReply,
  };
}

function ScheduleEditor({ form, set }) {
  const toggleDay = (d) =>
    set({
      scheduleDays: form.scheduleDays.includes(d)
        ? form.scheduleDays.filter((x) => x !== d)
        : [...form.scheduleDays, d].sort(),
    });
  return (
    <div className="space-y-3">
      <div className="flex gap-1.5">
        {WEEKDAYS.map((name, d) => {
          const on = form.scheduleDays.includes(d);
          return (
            <button
              key={name}
              type="button"
              aria-pressed={on}
              onClick={() => {
                haptic.select();
                toggleDay(d);
              }}
              className={`h-9 flex-1 rounded-lg text-[13px] font-semibold transition-colors ${
                on ? "bg-sky text-onsky" : "bg-raised/70 text-muted"
              }`}
            >
              {name}
            </button>
          );
        })}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Field label="С" htmlFor="sch-from">
          <Input
            id="sch-from"
            type="time"
            value={form.scheduleStart}
            onChange={(e) => set({ scheduleStart: e.target.value })}
          />
        </Field>
        <Field label="До" htmlFor="sch-to">
          <Input
            id="sch-to"
            type="time"
            value={form.scheduleEnd}
            onChange={(e) => set({ scheduleEnd: e.target.value })}
          />
        </Field>
      </div>
      <p className="text-xs leading-snug text-faint">
        Если «до» раньше «с», интервал переходит через полночь: 19:00–09:00 — вечер и ночь. Часовой
        пояс: {form.timezone}.
      </p>
    </div>
  );
}

function RuleSheet({ open, rule, onClose, onSave, onDelete }) {
  const { pro, openPaywall } = useApp();
  const hasPro = Boolean(pro?.has_access);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm(rule ? ruleToForm(rule) : emptyForm());
      setError("");
    }
  }, [open, rule]);

  const set = (patch) => setForm((f) => ({ ...f, ...patch }));
  const invalid =
    !form.responseText.trim() ||
    (form.triggerType === "keywords" && form.keywords.length === 0) ||
    (hasPro && form.scheduleEnabled && form.scheduleDays.length === 0);

  async function save() {
    setError("");
    setSaving(true);
    try {
      await onSave(formToPayload(form, hasPro));
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
              <div className="mt-3">
                <ChoiceChips
                  value={form.matchMode}
                  onChange={(matchMode) => set({ matchMode })}
                  options={MATCH_MODES}
                />
                <p className="mt-1.5 text-xs text-faint">{MATCH_HINTS[form.matchMode]}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div>
          <Label>Где отвечать</Label>
          <Segmented
            value={hasPro ? form.scope : "private"}
            onChange={(scope) =>
              scope !== "private" && !hasPro
                ? openPaywall("Ответы в группах — функция Pro")
                : set({ scope })
            }
            options={[
              { value: "private", label: "В личке" },
              { value: "groups", label: "В группах", icon: hasPro ? null : Crown },
              { value: "all", label: "Везде", icon: hasPro ? null : Crown },
            ]}
          />
          {hasPro && form.scope !== "private" && (
            <p className="mt-1.5 text-xs leading-snug text-faint">
              В группах автопилот отвечает, только когда вас упомянули или ответили на ваше
              сообщение.
            </p>
          )}
        </div>

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

        <ListGroup
          title="Умный автоответ"
          footer={hasPro ? null : "Функции с короной доступны в Pro."}
        >
          <OptionRow
            icon={Clock}
            title="Рабочие часы"
            subtitle="Отвечать только в выбранное время"
            checked={form.scheduleEnabled}
            onChange={(scheduleEnabled) => set({ scheduleEnabled })}
            proOnly
          >
            <ScheduleEditor form={form} set={set} />
          </OptionRow>
          <OptionRow
            icon={UserPlus}
            title="Только новым собеседникам"
            subtitle="Не отвечать тем, с кем вы уже переписывались"
            checked={form.newContactsOnly}
            onChange={(newContactsOnly) => set({ newContactsOnly })}
            proOnly
          />
          <OptionRow
            icon={Hand}
            title="Не мешать живому диалогу"
            subtitle="Молчать, если вы сами недавно писали в этот чат"
            checked={form.skipActiveMinutes > 0}
            onChange={(v) => set({ skipActiveMinutes: v ? 30 : 0 })}
            proOnly
          >
            <ChoiceChips
              value={form.skipActiveMinutes}
              onChange={(skipActiveMinutes) => set({ skipActiveMinutes })}
              options={ACTIVE_WINDOWS}
            />
          </OptionRow>
          <OptionRow
            icon={Keyboard}
            title="Эффект «печатает…»"
            subtitle="Пауза с индикатором набора перед ответом"
            checked={form.typingDelay > 0}
            onChange={(v) => set({ typingDelay: v ? 5 : 0 })}
            proOnly
          >
            <ChoiceChips
              value={form.typingDelay}
              onChange={(typingDelay) => set({ typingDelay })}
              options={TYPING_DELAYS}
            />
          </OptionRow>
          <OptionRow
            icon={BellRing}
            title="Уведомлять меня"
            subtitle="Бот пришлёт вам сообщение о каждом новом обращении"
            checked={form.notifyOwner}
            onChange={(notifyOwner) => set({ notifyOwner })}
            proOnly
          />
          <OptionRow
            icon={Sparkles}
            title="Отвечать с помощью ИИ"
            subtitle="ИИ напишет ответ по вашей базе знаний, текст выше — запасной"
            checked={form.aiReply}
            onChange={(aiReply) => set({ aiReply })}
            proOnly
          />
        </ListGroup>

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

function RuleTester({ accountId, rules }) {
  const [text, setText] = useState("");
  const [inGroup, setInGroup] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      setResult(await api.testRules(accountId, text, inGroup));
      haptic.select();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const answer = result && rules.find((r) => r.id === result.answer_rule_id);
  const reasons = {
    disabled: "выключено",
    scope: "не для этого чата",
    schedule: "сейчас нерабочее время",
  };

  return (
    <section className="rounded-[18px] bg-surface p-4">
      <h2 className="flex items-center gap-2 text-[15px] font-semibold">
        <FlaskConical className="h-4 w-4 text-sky" aria-hidden /> Проверить правила
      </h2>
      <p className="mt-1 text-[13px] leading-snug text-muted">
        Напишите сообщение как клиент — покажем, что ответит автопилот.
      </p>
      <form onSubmit={run} className="mt-3 flex gap-2">
        <Input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Сколько стоит доставка?"
          aria-label="Пример сообщения"
          className="!py-2.5"
        />
        <Button type="submit" loading={loading} disabled={!text.trim()}>
          Проверить
        </Button>
      </form>
      <label className="mt-2 flex items-center gap-2 text-[13px] text-muted">
        <input
          type="checkbox"
          checked={inGroup}
          onChange={(e) => setInGroup(e.target.checked)}
          className="h-4 w-4 accent-[rgb(var(--sky))]"
        />
        Как упоминание в группе
      </label>
      <ErrorNote>{error}</ErrorNote>
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-3 space-y-2"
          >
            {answer ? (
              <div className="rounded-tile bg-go/10 p-3">
                <p className="text-[13px] font-semibold text-go">Автопилот ответит:</p>
                <p className="mt-1 line-clamp-3 text-[14px] leading-snug">
                  {answer.response_text.replace(/<[^>]+>/g, "")}
                </p>
              </div>
            ) : (
              <div className="rounded-tile bg-warn/10 p-3 text-[13px] font-semibold text-warn">
                Ни одно правило не ответит на это сообщение.
              </div>
            )}
            {result.verdicts
              .filter((v) => v.matched && v.blocked_by)
              .map((v) => {
                const rule = rules.find((r) => r.id === v.rule_id);
                return (
                  <p key={v.rule_id} className="text-xs text-faint">
                    Подошло, но промолчит: «
                    {rule?.response_text.replace(/<[^>]+>/g, "").slice(0, 40)}
                    …» — {reasons[v.blocked_by] || v.blocked_by}
                  </p>
                );
              })}
            <p className="text-xs leading-snug text-faint">{result.note}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}

function RuleRow({ rule, onOpen, onToggle }) {
  const preview = rule.response_text.replace(/<[^>]+>/g, "");
  const smart = [
    rule.schedule_enabled && {
      icon: Clock,
      label: `${rule.schedule_start}–${rule.schedule_end}`,
    },
    rule.scope !== "private" && {
      icon: UsersRound,
      label: rule.scope === "groups" ? "группы" : "везде",
    },
    rule.new_contacts_only && { icon: UserPlus, label: "новым" },
    rule.skip_if_owner_active_minutes > 0 && { icon: Hand, label: "не мешать" },
    rule.typing_delay_seconds > 0 && { icon: Keyboard, label: "печатает" },
    rule.notify_owner && { icon: BellRing, label: "уведомления" },
    rule.ai_reply && { icon: Sparkles, label: "ИИ" },
  ].filter(Boolean);
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
          {` · ${rule.replies_7d} ${plural(rule.replies_7d, "ответ", "ответа", "ответов")} за неделю`}
        </p>
        {smart.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {smart.map(({ icon: Icon, label }) => (
              <span
                key={label}
                className="inline-flex items-center gap-1 rounded-md bg-warn/12 px-2 py-0.5 text-[11px] font-semibold text-warn"
              >
                <Icon className="h-3 w-3" aria-hidden /> {label}
              </span>
            ))}
          </div>
        )}
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
  const [tab, setTab] = useState("rules");

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
          tab === "rules" &&
          rules?.length > 0 && (
            <Button size="sm" icon={atLimit ? Crown : Plus} onClick={openNew}>
              Правило
            </Button>
          )
        }
      />

      <Segmented
        value={tab}
        onChange={setTab}
        options={[
          { value: "rules", label: "Правила" },
          { value: "snippets", label: "Фразы" },
          { value: "ai", label: "ИИ" },
        ]}
      />

      {tab === "snippets" && <SnippetsPanel accountId={accountId} />}
      {tab === "ai" && <AiPanel accountId={accountId} />}

      {tab === "rules" && <ErrorNote>{error}</ErrorNote>}

      {tab !== "rules" ? null : rules === null ? (
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
          <RuleTester accountId={accountId} rules={rules} />
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
