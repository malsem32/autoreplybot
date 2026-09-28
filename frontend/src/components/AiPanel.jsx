import { Crown, Send, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { haptic } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";
import ChoiceChips from "./composer/ChoiceChips.jsx";
import Button from "./ui/Button.jsx";
import { EmptyState, ErrorNote, Skeleton } from "./ui/Feedback.jsx";
import { Field, Input, Label, Textarea } from "./ui/Input.jsx";

const TONES = [
  { value: "friendly", label: "Дружелюбно" },
  { value: "formal", label: "Официально" },
  { value: "short", label: "Коротко" },
];

const KNOWLEDGE_PLACEHOLDER = `Чем занимаюсь: доставка цветов по Казани.
Цены: букет из 15 роз — 3500 ₽, доставка 300 ₽, от 5000 ₽ бесплатно.
Время работы: ежедневно 9:00–21:00.
Оплата: карта, СБП. Заказ — за 2 часа.`;

/** AI replies (Pro): the knowledge base the assistant answers from, its
 * tone, and a live preview. Rules opt in with "Отвечать с помощью ИИ". */
export default function AiPanel({ accountId }) {
  const { pro, openPaywall, toast } = useApp();
  const hasPro = Boolean(pro?.has_access);
  const [settings, setSettings] = useState(null);
  const [knowledge, setKnowledge] = useState("");
  const [tone, setTone] = useState("friendly");
  const [saving, setSaving] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setSettings(null);
    api
      .getAi(accountId)
      .then((s) => {
        setSettings(s);
        setKnowledge(s.knowledge);
        setTone(s.tone);
      })
      .catch((err) => setError(err.message));
  }, [accountId]);

  if (!settings) return error ? <ErrorNote>{error}</ErrorNote> : <Skeleton className="h-64" />;

  if (!settings.available) {
    return (
      <EmptyState
        icon={Sparkles}
        title="ИИ-ответы скоро появятся"
        text="Администратор ещё не подключил ИИ на сервере. Как только подключит — здесь можно будет научить автопилот отвечать по вашему прайсу."
      />
    );
  }

  const dirty = knowledge !== settings.knowledge || tone !== settings.tone;

  async function save() {
    setSaving(true);
    try {
      const next = await api.saveAi(accountId, { knowledge, tone });
      setSettings(next);
      haptic.success();
      toast("Сохранено");
    } catch (err) {
      toast(err.message, "danger");
    } finally {
      setSaving(false);
    }
  }

  async function ask() {
    if (!hasPro) {
      openPaywall("ИИ-ответы — функция Pro");
      return;
    }
    if (dirty) await save();
    setAsking(true);
    setAnswer(null);
    setError("");
    try {
      const res = await api.previewAi(accountId, question);
      setAnswer(res.answer ?? "");
      setSettings((s) => ({ ...s, used_today: res.used_today }));
    } catch (err) {
      setError(err.message);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="relative overflow-hidden rounded-[18px] bg-surface p-4">
        <div
          className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-sky/20 blur-3xl"
          aria-hidden
        />
        <p className="relative flex items-center gap-2 text-[15px] font-semibold">
          <Sparkles className="h-4 w-4 text-sky" aria-hidden /> ИИ-ассистент
          {!hasPro && <Crown className="h-3.5 w-3.5 text-warn" aria-label="Pro" />}
        </p>
        <p className="relative mt-1.5 text-[14px] leading-snug text-muted">
          Отвечает клиентам своими словами, опираясь только на то, что вы напишете ниже. Включите
          «Отвечать с помощью ИИ» в нужном правиле — текст правила останется запасным ответом.
        </p>
      </div>

      <Field label="Что знает ассистент" hint={`${knowledge.length} / 4000`} htmlFor="ai-knowledge">
        <Textarea
          id="ai-knowledge"
          value={knowledge}
          maxLength={4000}
          onChange={(e) => setKnowledge(e.target.value)}
          placeholder={KNOWLEDGE_PLACEHOLDER}
          className="min-h-[160px]"
        />
      </Field>

      <div>
        <Label>Тон ответов</Label>
        <ChoiceChips value={tone} onChange={setTone} options={TONES} />
      </div>

      <Button
        variant="secondary"
        className="w-full"
        loading={saving}
        disabled={!dirty}
        onClick={save}
      >
        Сохранить
      </Button>

      <div className="rounded-[18px] bg-surface p-4">
        <Label>Проверить ответ</Label>
        <div className="flex gap-2">
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Сколько стоит доставка?"
            maxLength={1000}
            onKeyDown={(e) => e.key === "Enter" && question.trim() && ask()}
          />
          <Button
            icon={Send}
            loading={asking}
            disabled={!question.trim()}
            onClick={ask}
            aria-label="Спросить"
            className="shrink-0 px-4"
          />
        </div>
        {answer !== null && (
          <div className="mt-3 rounded-2xl rounded-bl-md bg-raised px-3.5 py-2.5 text-[15px] leading-snug">
            {answer || (
              <span className="text-muted">ИИ не ответил — клиент получил бы текст правила.</span>
            )}
          </div>
        )}
        <ErrorNote>{error}</ErrorNote>
        <p className="mt-2 text-xs text-faint">
          Сегодня использовано {settings.used_today} из {settings.daily_limit} ответов ИИ. Сообщения
          клиентов передаются ИИ-сервису для составления ответа.
        </p>
      </div>
    </div>
  );
}
