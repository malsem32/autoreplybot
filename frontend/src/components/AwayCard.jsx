import { AnimatePresence, motion } from "framer-motion";
import { Palmtree } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { haptic } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";
import Button from "./ui/Button.jsx";
import { ErrorNote } from "./ui/Feedback.jsx";
import { Field, Input, Textarea } from "./ui/Input.jsx";
import Sheet from "./ui/Sheet.jsx";

const DEFAULT_TEXT =
  "Здравствуйте! Я в отпуске до {дата} и отвечаю с задержкой. Вернусь — обязательно напишу 🙌";

function browserTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Moscow";
  } catch {
    return "Europe/Moscow";
  }
}

function toDateInput(date) {
  const d = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return d.toISOString().slice(0, 10);
}

function formatDay(iso) {
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
}

/** Vacation mode in one tap: until the chosen day every private message
 * gets the away text; it switches itself off when the day comes. */
export default function AwayCard({ accountId }) {
  const { toast } = useApp();
  const [state, setState] = useState(null);
  const [open, setOpen] = useState(false);
  const [day, setDay] = useState("");
  const [text, setText] = useState(DEFAULT_TEXT);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setState(null);
    api
      .getAway(accountId)
      .then(setState)
      .catch(() => setState(null));
  }, [accountId]);

  function openSheet() {
    const week = new Date(Date.now() + 7 * 24 * 3600 * 1000);
    setDay(state?.active && state.until ? toDateInput(new Date(state.until)) : toDateInput(week));
    setText(state?.text || DEFAULT_TEXT);
    setError("");
    setOpen(true);
  }

  async function save() {
    setSaving(true);
    setError("");
    try {
      // Back on the chosen day: the mode ends at the start of that day.
      const until = new Date(`${day}T00:00:00`);
      const next = await api.setAway(accountId, {
        until: until.toISOString(),
        text,
        timezone: browserTimezone(),
      });
      setState(next);
      setOpen(false);
      haptic.success();
      toast(`Режим отпуска до ${formatDay(next.until)}`);
    } catch (err) {
      setError(err.message);
      haptic.error();
    } finally {
      setSaving(false);
    }
  }

  async function stop() {
    try {
      setState(await api.stopAway(accountId));
      haptic.success();
      toast("С возвращением! Режим отпуска выключен");
    } catch (err) {
      toast(err.message, "danger");
    }
  }

  const active = Boolean(state?.active);
  const minDay = toDateInput(new Date(Date.now() + 24 * 3600 * 1000));

  return (
    <>
      <AnimatePresence initial={false} mode="wait">
        {active ? (
          <motion.section
            key="on"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-3 rounded-[18px] bg-warn/12 p-4 ring-1 ring-warn/30"
          >
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-warn text-[#2A1A00]">
              <Palmtree className="h-5 w-5" />
            </span>
            <button type="button" onClick={openSheet} className="min-w-0 flex-1 text-left">
              <p className="text-[15px] font-semibold">В отпуске до {formatDay(state.until)}</p>
              <p className="truncate text-[13px] text-muted">{state.preview}</p>
            </button>
            <Button size="sm" variant="secondary" onClick={stop}>
              Выключить
            </Button>
          </motion.section>
        ) : (
          <motion.button
            key="off"
            type="button"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={openSheet}
            className="flex w-full items-center gap-3 rounded-[18px] bg-surface p-4 text-left"
          >
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-warn/15 text-warn">
              <Palmtree className="h-5 w-5" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[15px] font-semibold">Режим отпуска</span>
              <span className="block text-[13px] text-muted">
                Уезжаете? Всем ответим, что вы вернётесь
              </span>
            </span>
          </motion.button>
        )}
      </AnimatePresence>

      <Sheet
        open={open}
        onClose={() => setOpen(false)}
        title="Режим отпуска"
        footer={
          <Button
            className="w-full"
            loading={saving}
            disabled={!day || !text.trim()}
            onClick={save}
          >
            {active ? "Сохранить" : "Включить"}
          </Button>
        }
      >
        <div className="space-y-4 pt-1">
          <p className="text-[14px] leading-snug text-muted">
            Пока вы в отпуске, на личные сообщения приходит этот ответ вместо правил — не чаще раза
            в 12 часов одному человеку. В день возвращения режим выключится сам.
          </p>
          <Field label="Вернусь" htmlFor="away-day">
            <Input
              id="away-day"
              type="date"
              min={minDay}
              value={day}
              onChange={(e) => setDay(e.target.value)}
            />
          </Field>
          <Field label="Ответ" hint="{дата} заменится на день возвращения" htmlFor="away-text">
            <Textarea
              id="away-text"
              value={text}
              maxLength={1000}
              onChange={(e) => setText(e.target.value)}
              className="min-h-[110px]"
            />
          </Field>
          <ErrorNote>{error}</ErrorNote>
        </div>
      </Sheet>
    </>
  );
}
