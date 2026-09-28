import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Crown, Download, Inbox, MessageCircle, Wrench } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client.js";
import NeedAccount from "../components/NeedAccount.jsx";
import PageTitle from "../components/PageTitle.jsx";
import Button from "../components/ui/Button.jsx";
import { EmptyState, ErrorNote, Pill, Skeleton } from "../components/ui/Feedback.jsx";
import { Field, Textarea } from "../components/ui/Input.jsx";
import Segmented from "../components/ui/Segmented.jsx";
import Sheet from "../components/ui/Sheet.jsx";
import plural from "../lib/plural.js";
import { haptic, openLink } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";

const STATUS = {
  new: { label: "Новое", tone: "sky" },
  in_work: { label: "В работе", tone: "warn" },
  done: { label: "Готово", tone: "go" },
};

function timeAgo(iso) {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return "только что";
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} ч назад`;
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}

function initial(name) {
  return (name || "?").trim().slice(0, 1).toUpperCase();
}

function LeadSheet({ lead, open, onClose, onSave }) {
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState("");

  useEffect(() => {
    if (open && lead) setNote(lead.note);
  }, [open, lead]);

  if (!lead) return null;

  async function save(patch, key) {
    setSaving(key);
    try {
      await onSave(lead, patch);
      haptic.success();
    } finally {
      setSaving("");
    }
  }

  return (
    <Sheet open={open} onClose={onClose} title={lead.name || "Обращение"}>
      <div className="space-y-5 pt-1">
        <div className="rounded-tile bg-raised/50 p-3.5">
          <p className="text-[13px] text-muted">
            {lead.username ? `@${lead.username} · ` : ""}
            {lead.messages_count}{" "}
            {plural(lead.messages_count, "сообщение", "сообщения", "сообщений")} · первое{" "}
            {timeAgo(lead.created_at)}
          </p>
          <p className="mt-2 text-[15px] leading-snug">{lead.last_text || "—"}</p>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {Object.entries(STATUS).map(([key, s]) => (
            <Button
              key={key}
              size="sm"
              variant={lead.status === key ? "primary" : "secondary"}
              loading={saving === key}
              onClick={() => save({ status: key }, key)}
            >
              {s.label}
            </Button>
          ))}
        </div>

        <Field label="Заметка" hint="видна только вам и команде" htmlFor="lead-note">
          <Textarea
            id="lead-note"
            value={note}
            maxLength={1000}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Что хотел клиент, о чём договорились…"
            className="min-h-[96px]"
          />
        </Field>
        <div className="flex gap-2">
          {lead.username && (
            <Button
              variant="secondary"
              icon={MessageCircle}
              onClick={() => openLink(`https://t.me/${lead.username}`)}
            >
              Написать
            </Button>
          )}
          <Button
            className="flex-1"
            loading={saving === "note"}
            disabled={note === lead.note}
            onClick={() => save({ note }, "note")}
          >
            Сохранить заметку
          </Button>
        </div>
      </div>
    </Sheet>
  );
}

function LeadCard({ lead, onOpen, onQuick }) {
  const status = STATUS[lead.status] || STATUS.new;
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
        onClick={() => onOpen(lead)}
        className="flex w-full gap-3 p-4 text-left"
      >
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-gradient-to-br from-sky to-[#1E6FD9] font-display text-base font-semibold text-white">
          {initial(lead.name)}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center justify-between gap-2">
            <span className="truncate text-[16px] font-semibold">{lead.name || "Без имени"}</span>
            <span className="shrink-0 text-xs text-faint">{timeAgo(lead.last_message_at)}</span>
          </span>
          <span className="mt-0.5 line-clamp-2 block text-[14px] leading-snug text-muted">
            {lead.last_text || "—"}
          </span>
          <span className="mt-2 flex items-center gap-2">
            <Pill tone={status.tone} dot>
              {status.label}
            </Pill>
            {lead.messages_count > 1 && (
              <span className="text-xs text-faint">
                {lead.messages_count}{" "}
                {plural(lead.messages_count, "сообщение", "сообщения", "сообщений")}
              </span>
            )}
            {lead.note && <span className="truncate text-xs text-faint">· {lead.note}</span>}
          </span>
        </span>
      </button>
      {lead.status !== "done" && (
        <div className="flex border-t border-line/50">
          {lead.status === "new" && (
            <button
              type="button"
              onClick={() => onQuick(lead, "in_work")}
              className="flex flex-1 items-center justify-center gap-2 py-2.5 text-sm font-semibold text-warn active:bg-raised/60"
            >
              <Wrench className="h-4 w-4" /> В работу
            </button>
          )}
          <button
            type="button"
            onClick={() => onQuick(lead, "done")}
            className="flex flex-1 items-center justify-center gap-2 border-l border-line/50 py-2.5 text-sm font-semibold text-go first:border-l-0 active:bg-raised/60"
          >
            <CheckCircle2 className="h-4 w-4" /> Готово
          </button>
        </div>
      )}
    </motion.article>
  );
}

function ProTeaser() {
  const { openPaywall } = useApp();
  return (
    <EmptyState
      icon={Inbox}
      title="Все обращения в одном месте"
      text="Каждый, кто написал вам в личку, попадает сюда: статусы «новое / в работе / готово», заметки, выгрузка в таблицу. Менять статус можно прямо из уведомления в боте."
      action={
        <Button variant="pro" icon={Crown} onClick={() => openPaywall("Обращения — функция Pro")}>
          Открыть в Pro
        </Button>
      }
    />
  );
}

export default function LeadsPage() {
  const { activeAccount, pro, toast } = useApp();
  const [filter, setFilter] = useState("new");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [exporting, setExporting] = useState(false);
  const accountId = activeAccount?.id;
  const hasPro = Boolean(pro?.has_access);

  const load = useCallback(() => {
    if (!accountId || !hasPro) return;
    api
      .listLeads(accountId, filter === "all" ? null : filter)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [accountId, filter, hasPro]);

  useEffect(() => {
    setData(null);
    setError("");
    load();
  }, [load]);

  if (!activeAccount) return <NeedAccount title="Обращения" />;

  async function update(lead, patch) {
    try {
      const updated = await api.updateLead(accountId, lead.id, patch);
      setSelected((s) => (s && s.id === updated.id ? updated : s));
      load();
    } catch (err) {
      toast(err.message, "danger");
    }
  }

  async function exportCsv() {
    setExporting(true);
    try {
      const { rows } = await api.exportLeads(accountId);
      haptic.success();
      toast(`Файл (${rows} строк) отправлен в чат с ботом`);
    } catch (err) {
      toast(err.message, "danger");
    } finally {
      setExporting(false);
    }
  }

  const counts = data?.counts || {};
  const total = (counts.new || 0) + (counts.in_work || 0) + (counts.done || 0);

  return (
    <div className="space-y-4 p-4">
      <PageTitle
        title="Обращения"
        subtitle="Все, кто написал вам в личку"
        action={
          hasPro &&
          total > 0 && (
            <Button
              size="sm"
              variant="secondary"
              icon={Download}
              loading={exporting}
              onClick={exportCsv}
              aria-label="Выгрузить в CSV"
            >
              CSV
            </Button>
          )
        }
      />
      {!hasPro ? (
        <ProTeaser />
      ) : (
        <>
          <Segmented
            value={filter}
            onChange={setFilter}
            options={[
              { value: "new", label: `Новые${counts.new ? ` ${counts.new}` : ""}` },
              { value: "in_work", label: `В работе${counts.in_work ? ` ${counts.in_work}` : ""}` },
              { value: "done", label: "Готово" },
              { value: "all", label: "Все" },
            ]}
          />
          <ErrorNote>{error}</ErrorNote>
          {data === null && !error ? (
            <div className="space-y-3">
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
            </div>
          ) : data?.leads.length === 0 ? (
            <EmptyState
              icon={Inbox}
              title={total === 0 ? "Пока никто не писал" : "Здесь пусто"}
              text={
                total === 0
                  ? "Как только кто-то напишет вам в личку, обращение появится здесь."
                  : "В этом статусе обращений нет."
              }
            />
          ) : (
            <div className="space-y-2.5">
              <AnimatePresence initial={false}>
                {data?.leads.map((lead) => (
                  <LeadCard
                    key={lead.id}
                    lead={lead}
                    onOpen={setSelected}
                    onQuick={(l, status) => {
                      haptic.select();
                      update(l, { status });
                    }}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}
        </>
      )}
      <LeadSheet
        lead={selected}
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        onSave={update}
      />
    </div>
  );
}
