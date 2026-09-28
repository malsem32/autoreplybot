import { AnimatePresence, motion } from "framer-motion";
import {
  BarChart3,
  BellOff,
  Crown,
  FileBarChart,
  History,
  LinkIcon,
  Pause,
  Play,
  Plus,
  Send,
  ShieldCheck,
  Trash2,
  Unplug,
  Users,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import CampaignLogsSheet from "../components/CampaignLogsSheet.jsx";
import CampaignStatsSheet from "../components/CampaignStatsSheet.jsx";
import OptionRow from "../components/pro/OptionRow.jsx";
import ChipsInput from "../components/composer/ChipsInput.jsx";
import ChoiceChips from "../components/composer/ChoiceChips.jsx";
import MessagePreview from "../components/composer/MessagePreview.jsx";
import PhotoPicker from "../components/composer/PhotoPicker.jsx";
import { photoRefs, photosFromUrls } from "../components/composer/photos.js";
import RichTextEditor from "../components/composer/RichTextEditor.jsx";
import NeedAccount from "../components/NeedAccount.jsx";
import PageTitle from "../components/PageTitle.jsx";
import Button from "../components/ui/Button.jsx";
import { EmptyState, ErrorNote, Pill, Skeleton } from "../components/ui/Feedback.jsx";
import { Field, Input, Label } from "../components/ui/Input.jsx";
import { ListGroup } from "../components/ui/List.jsx";
import Segmented from "../components/ui/Segmented.jsx";
import Sheet from "../components/ui/Sheet.jsx";
import plural from "../lib/plural.js";
import { confirmDialog, haptic } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";

const INTERVALS = [
  { value: 30, label: "30 мин" },
  { value: 60, label: "1 час" },
  { value: 180, label: "3 часа" },
  { value: 360, label: "6 часов" },
  { value: 720, label: "12 часов" },
  { value: 1440, label: "Сутки" },
];

const STATUS = {
  active: { tone: "go", label: "Идёт" },
  paused: { tone: "warn", label: "Пауза" },
  finished: { tone: "muted", label: "Завершена" },
};

function toLocalInput(iso) {
  const d = iso ? new Date(iso) : new Date(Date.now() + 15 * 60 * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function intervalLabel(minutes) {
  const preset = INTERVALS.find((i) => i.value === minutes);
  if (preset) return preset.label.toLowerCase();
  if (minutes % 60 === 0) return `${minutes / 60} ч`;
  return `${minutes} мин`;
}

const emptyForm = () => ({
  title: "",
  text: "",
  photos: [],
  targets: [],
  scheduleType: "recurring",
  interval: 60,
  customInterval: "",
  scheduledAt: toLocalInput(null),
  tagRandomUsers: false,
  disableNotification: false,
  protectContent: false,
  disableLinkPreview: false,
  autoDisableFailing: false,
  notifyReport: false,
});

function campaignToForm(c) {
  const preset = INTERVALS.some((i) => i.value === c.interval_minutes);
  return {
    title: c.title,
    text: c.text_template,
    photos: photosFromUrls(c.photo_urls),
    targets: c.target_chats,
    scheduleType: c.schedule_type,
    interval: preset ? c.interval_minutes : "custom",
    customInterval: preset ? "" : String(c.interval_minutes),
    scheduledAt: toLocalInput(c.scheduled_at),
    tagRandomUsers: c.tag_random_users,
    disableNotification: c.disable_notification,
    protectContent: c.protect_content,
    disableLinkPreview: c.disable_link_preview,
    autoDisableFailing: c.auto_disable_failing,
    notifyReport: c.notify_report,
  };
}

function formToPayload(form) {
  const payload = {
    title: form.title.trim(),
    text_template: form.text,
    photos: photoRefs(form.photos),
    target_chats: form.targets,
    schedule_type: form.scheduleType,
    tag_random_users: form.tagRandomUsers,
    disable_notification: form.disableNotification,
    protect_content: form.protectContent,
    disable_link_preview: form.disableLinkPreview,
    auto_disable_failing: form.autoDisableFailing,
    notify_report: form.notifyReport,
  };
  if (form.scheduleType === "recurring") {
    payload.interval_minutes =
      form.interval === "custom" ? Math.max(1, Number(form.customInterval) || 60) : form.interval;
  } else {
    payload.scheduled_at = new Date(form.scheduledAt).toISOString();
  }
  return payload;
}

function CampaignSheet({ open, campaign, onClose, onSave, onDelete }) {
  const { pro } = useApp();
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const hasPro = Boolean(pro?.has_access);

  useEffect(() => {
    if (open) {
      setForm(campaign ? campaignToForm(campaign) : emptyForm());
      setError("");
    }
  }, [open, campaign]);

  const set = (patch) => setForm((f) => ({ ...f, ...patch }));
  const invalid = !form.title.trim() || !form.text.trim() || form.targets.length === 0;
  const signature = pro?.bot_username ? `Отправлено через @${pro.bot_username}` : "";

  async function save() {
    setError("");
    setSaving(true);
    try {
      const payload = formToPayload(form);
      if (!hasPro) {
        // Pro options saved while a subscription was active are dropped on
        // edit after it expires, instead of blocking the whole save.
        payload.tag_random_users = false;
        payload.protect_content = false;
        payload.auto_disable_failing = false;
        payload.notify_report = false;
      }
      await onSave(payload);
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
      title={campaign ? "Рассылка" : "Новая рассылка"}
      footer={
        <div className="flex gap-2">
          {campaign && (
            <Button
              variant="danger"
              icon={Trash2}
              onClick={() => onDelete(campaign)}
              aria-label="Удалить рассылку"
            />
          )}
          <Button className="flex-1" icon={Send} loading={saving} disabled={invalid} onClick={save}>
            {campaign ? "Сохранить" : "Запустить рассылку"}
          </Button>
        </div>
      }
    >
      <div className="space-y-5 pt-1">
        <Field label="Название" hint="видно только вам" htmlFor="c-title">
          <Input
            id="c-title"
            value={form.title}
            onChange={(e) => set({ title: e.target.value })}
            placeholder="Акция выходного дня"
            maxLength={255}
          />
        </Field>

        <Field label="Сообщение" htmlFor="c-text">
          <RichTextEditor
            id="c-text"
            value={form.text}
            onChange={(text) => set({ text })}
            limit={form.photos.length ? 1024 : 4096}
            placeholder="{Привет|Добрый день}! Только до воскресенья — скидка 20% на всё."
          />
          {form.photos.length > 0 && (
            <p className="mt-1.5 text-xs text-faint">
              Подпись к фото — до 1024 символов. Более длинный текст придёт отдельным сообщением
              сразу после фото.
            </p>
          )}
        </Field>

        <Field label="Фото">
          <PhotoPicker value={form.photos} onChange={(photos) => set({ photos })} />
        </Field>

        <Field label="Куда отправлять" hint="Enter или запятая" htmlFor="c-targets">
          <ChipsInput
            id="c-targets"
            value={form.targets}
            onChange={(targets) => set({ targets })}
            placeholder="@my_channel, t.me/+AbCdEf, -100123…"
          />
          <p className="mt-1.5 text-xs leading-snug text-faint">
            Юзернейм, ссылка t.me или ID чата. По ссылке-приглашению аккаунт сначала вступит в чат.
            Между чатами — пауза 20–45 секунд, чтобы Telegram не ограничил аккаунт.
          </p>
        </Field>

        <div className="space-y-3">
          <Label>Когда отправлять</Label>
          <Segmented
            value={form.scheduleType}
            onChange={(scheduleType) => set({ scheduleType })}
            options={[
              { value: "recurring", label: "Регулярно" },
              { value: "once", label: "Один раз" },
            ]}
          />
          <AnimatePresence mode="wait" initial={false}>
            {form.scheduleType === "recurring" ? (
              <motion.div
                key="rec"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-3"
              >
                <ChoiceChips
                  value={form.interval}
                  onChange={(interval) => set({ interval })}
                  options={[...INTERVALS, { value: "custom", label: "Свой" }]}
                />
                {form.interval === "custom" && (
                  <Input
                    type="number"
                    min="1"
                    inputMode="numeric"
                    value={form.customInterval}
                    onChange={(e) => set({ customInterval: e.target.value })}
                    placeholder="Интервал в минутах"
                    aria-label="Интервал в минутах"
                  />
                )}
              </motion.div>
            ) : (
              <motion.div
                key="once"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <Input
                  type="datetime-local"
                  value={form.scheduledAt}
                  onChange={(e) => set({ scheduledAt: e.target.value })}
                  aria-label="Дата и время отправки"
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <ListGroup title="Параметры">
          <OptionRow
            icon={BellOff}
            title="Без звука"
            subtitle="Получатели не услышат уведомление"
            checked={form.disableNotification}
            onChange={(v) => set({ disableNotification: v })}
          />
          <OptionRow
            icon={LinkIcon}
            title="Без превью ссылок"
            subtitle="Не показывать карточку сайта под текстом"
            checked={form.disableLinkPreview}
            onChange={(v) => set({ disableLinkPreview: v })}
          />
          <OptionRow
            icon={ShieldCheck}
            title="Запрет пересылки"
            subtitle="Сообщение нельзя переслать или сохранить"
            checked={form.protectContent}
            onChange={(v) => set({ protectContent: v })}
            proOnly
          />
          <OptionRow
            icon={Users}
            title="Теги участников"
            subtitle="Незаметно упомянуть 5 случайных участников чата"
            checked={form.tagRandomUsers}
            onChange={(v) => set({ tagRandomUsers: v })}
            proOnly
          />
          <OptionRow
            icon={Unplug}
            title="Отключать недоступные чаты"
            subtitle="Пропускать чат после 3 неудачных отправок подряд"
            checked={form.autoDisableFailing}
            onChange={(v) => set({ autoDisableFailing: v })}
            proOnly
          />
          <OptionRow
            icon={FileBarChart}
            title="Отчёт в бот"
            subtitle="Итог каждой рассылки придёт вам сообщением"
            checked={form.notifyReport}
            onChange={(v) => set({ notifyReport: v })}
            proOnly
          />
        </ListGroup>

        {(form.text || form.photos.length > 0) && (
          <div>
            <Label>Предпросмотр</Label>
            <MessagePreview text={form.text} photos={form.photos} signature={signature} />
            <p className="mt-1.5 text-xs text-faint">
              Подпись о сервисе добавляется автоматически.
            </p>
          </div>
        )}

        <ErrorNote>{error}</ErrorNote>
      </div>
    </Sheet>
  );
}

function CampaignCard({ campaign, onOpen, onToggle, onLogs, onStats }) {
  const status = STATUS[campaign.status] || STATUS.finished;
  const cover = campaign.photo_urls[0];
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -40 }}
      className="overflow-hidden rounded-[18px] bg-surface"
    >
      <button
        type="button"
        onClick={() => onOpen(campaign)}
        className="flex w-full gap-3 p-4 text-left"
      >
        {cover && (
          <div className="relative h-16 w-16 shrink-0 overflow-hidden rounded-xl">
            <img src={cover} alt="" className="h-full w-full object-cover" />
            {campaign.photo_urls.length > 1 && (
              <span className="absolute bottom-1 right-1 rounded-md bg-black/60 px-1.5 text-[10px] font-bold text-white">
                +{campaign.photo_urls.length - 1}
              </span>
            )}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <h3 className="truncate text-[16px] font-semibold">{campaign.title}</h3>
            <Pill tone={status.tone} dot>
              {status.label}
            </Pill>
          </div>
          <p className="mt-1 line-clamp-2 text-[14px] leading-snug text-muted">
            {campaign.text_template.replace(/<[^>]+>/g, "")}
          </p>
          <p className="mt-1.5 text-xs text-faint">
            {campaign.schedule_type === "once"
              ? `Один раз, ${new Date(campaign.scheduled_at).toLocaleString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}`
              : `Каждые ${intervalLabel(campaign.interval_minutes)}`}
            {` · ${campaign.target_chats.length} ${plural(campaign.target_chats.length, "чат", "чата", "чатов")}`}
            {campaign.disabled_targets.length > 0 &&
              ` · ${campaign.disabled_targets.length} отключено`}
          </p>
        </div>
      </button>
      <div className="flex border-t border-line/50">
        {campaign.status !== "finished" && (
          <button
            type="button"
            onClick={() => onToggle(campaign)}
            className="flex flex-1 items-center justify-center gap-2 py-3 text-sm font-semibold text-sky active:bg-raised/60"
          >
            {campaign.status === "active" ? (
              <Pause className="h-4 w-4" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {campaign.status === "active" ? "Пауза" : "Запустить"}
          </button>
        )}
        <button
          type="button"
          onClick={() => onLogs(campaign)}
          className="flex flex-1 items-center justify-center gap-2 border-l border-line/50 py-3 text-sm font-semibold text-muted active:bg-raised/60 first:border-l-0"
        >
          <History className="h-4 w-4" /> Журнал
        </button>
        <button
          type="button"
          onClick={() => onStats(campaign)}
          className="flex flex-1 items-center justify-center gap-2 border-l border-line/50 py-3 text-sm font-semibold text-muted active:bg-raised/60"
        >
          <BarChart3 className="h-4 w-4" /> Статистика
        </button>
      </div>
    </motion.article>
  );
}

export default function BroadcastPage() {
  const { activeAccount, pro, openPaywall, toast } = useApp();
  const [campaigns, setCampaigns] = useState(null);
  const [error, setError] = useState("");
  const [sheet, setSheet] = useState({ open: false, campaign: null });
  const [logs, setLogs] = useState({ open: false, campaign: null });
  const [stats, setStats] = useState({ open: false, campaign: null });
  const accountId = activeAccount?.id;

  useEffect(() => {
    if (!accountId) return;
    setCampaigns(null);
    api
      .listCampaigns(accountId)
      .then(setCampaigns)
      .catch((err) => {
        setError(err.message);
        setCampaigns([]);
      });
  }, [accountId]);

  if (!activeAccount) return <NeedAccount title="Рассылки" />;

  const limit = pro && !pro.has_access ? pro.free_max_campaigns : null;
  const atLimit = limit != null && campaigns && campaigns.length >= limit;

  function openNew() {
    if (atLimit) {
      openPaywall(`Без Pro — до ${limit} рассылок на аккаунт`);
      return;
    }
    setSheet({ open: true, campaign: null });
  }

  const replace = (updated) =>
    setCampaigns((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));

  async function save(payload) {
    if (sheet.campaign) {
      replace(await api.updateCampaign(accountId, sheet.campaign.id, payload));
      toast("Рассылка сохранена");
    } else {
      const created = await api.createCampaign(accountId, payload);
      setCampaigns((prev) => [...prev, created]);
      toast("Рассылка запущена");
    }
    setSheet({ open: false, campaign: null });
  }

  async function remove(campaign) {
    if (!(await confirmDialog(`Удалить рассылку «${campaign.title}» вместе с журналом?`))) return;
    try {
      await api.deleteCampaign(accountId, campaign.id);
      setCampaigns((prev) => prev.filter((c) => c.id !== campaign.id));
      setSheet({ open: false, campaign: null });
      toast("Рассылка удалена");
    } catch (err) {
      toast(err.message, "danger");
    }
  }

  async function toggle(campaign) {
    try {
      const updated =
        campaign.status === "active"
          ? await api.pauseCampaign(accountId, campaign.id)
          : await api.resumeCampaign(accountId, campaign.id);
      replace(updated);
      haptic.select();
    } catch (err) {
      toast(err.message, "danger");
    }
  }

  return (
    <div className="space-y-4 p-4">
      <PageTitle
        title="Рассылки"
        subtitle="По вашим чатам и каналам, с паузами против блокировок"
        action={
          campaigns?.length > 0 && (
            <Button size="sm" icon={atLimit ? Crown : Plus} onClick={openNew}>
              Рассылка
            </Button>
          )
        }
      />
      <ErrorNote>{error}</ErrorNote>

      {campaigns === null ? (
        <div className="space-y-3">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      ) : campaigns.length === 0 ? (
        <EmptyState
          icon={Send}
          title="Запустите первую рассылку"
          text="Сообщение с фото и форматированием — в ваши чаты по расписанию."
          action={
            <Button icon={Plus} onClick={openNew}>
              Создать рассылку
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          <AnimatePresence initial={false}>
            {campaigns.map((c) => (
              <CampaignCard
                key={c.id}
                campaign={c}
                onOpen={(campaign) => setSheet({ open: true, campaign })}
                onToggle={toggle}
                onLogs={(campaign) => setLogs({ open: true, campaign })}
                onStats={(campaign) =>
                  pro?.has_access
                    ? setStats({ open: true, campaign })
                    : openPaywall("Статистика по каждому чату доступна в Pro")
                }
              />
            ))}
          </AnimatePresence>
          {limit != null && (
            <p className="px-1 text-[13px] text-faint">
              {campaigns.length} из {limit} рассылок на бесплатном тарифе.{" "}
              <button
                type="button"
                className="font-semibold text-sky"
                onClick={() => openPaywall()}
              >
                Безлимит в Pro
              </button>
            </p>
          )}
        </div>
      )}

      <CampaignSheet
        open={sheet.open}
        campaign={sheet.campaign}
        onClose={() => setSheet({ open: false, campaign: null })}
        onSave={save}
        onDelete={remove}
      />
      <CampaignLogsSheet
        open={logs.open}
        campaign={logs.campaign}
        accountId={accountId}
        onClose={() => setLogs((l) => ({ ...l, open: false }))}
      />
      <CampaignStatsSheet
        open={stats.open}
        campaign={stats.campaign}
        accountId={accountId}
        onClose={() => setStats((s) => ({ ...s, open: false }))}
        onChanged={replace}
      />
    </div>
  );
}
