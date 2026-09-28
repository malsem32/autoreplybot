import { useEffect, useState } from "react";
import PageTitle from "../components/PageTitle.jsx";
import Button from "../components/ui/Button.jsx";
import { ErrorNote, Skeleton } from "../components/ui/Feedback.jsx";
import { Field, Input } from "../components/ui/Input.jsx";
import useBackButton from "../hooks/useBackButton.js";
import { api } from "../api/client.js";
import { haptic } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";

function Metric({ value, label, tone = "text-ink" }) {
  return (
    <div className="rounded-tile bg-surface p-4">
      <p className={`font-display text-[26px] font-semibold leading-none tabular-nums ${tone}`}>
        {value}
      </p>
      <p className="mt-2 text-[13px] leading-snug text-muted">{label}</p>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section>
      <h2 className="mb-2 px-1 text-[13px] font-medium text-muted">{title}</h2>
      <div className="grid grid-cols-2 gap-2">{children}</div>
    </section>
  );
}

function ProSettings() {
  const { refreshPro, toast } = useApp();
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .adminGetPro()
      .then(setForm)
      .catch((err) => setError(err.message));
  }, []);

  async function save(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      setForm(
        await api.adminUpdatePro({
          stars_price: Number(form.stars_price),
          duration_days: Number(form.duration_days),
          referral_bonus_days: Number(form.referral_bonus_days),
        }),
      );
      haptic.success();
      toast("Настройки Pro сохранены");
      refreshPro();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (!form) return error ? <ErrorNote>{error}</ErrorNote> : <Skeleton className="h-48" />;

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  return (
    <form onSubmit={save} className="space-y-4 rounded-[18px] bg-surface p-4">
      <h2 className="font-display text-base font-semibold">Подписка Pro и рефералы</h2>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Цена, Stars" htmlFor="p-price">
          <Input
            id="p-price"
            type="number"
            min="1"
            inputMode="numeric"
            value={form.stars_price}
            onChange={set("stars_price")}
          />
        </Field>
        <Field label="Срок, дней" htmlFor="p-days">
          <Input
            id="p-days"
            type="number"
            min="1"
            inputMode="numeric"
            value={form.duration_days}
            onChange={set("duration_days")}
          />
        </Field>
      </div>
      <Field label="Бонус за приглашение, дней" hint="обоим, 0 — выключить" htmlFor="p-ref">
        <Input
          id="p-ref"
          type="number"
          min="0"
          inputMode="numeric"
          value={form.referral_bonus_days}
          onChange={set("referral_bonus_days")}
        />
      </Field>
      <ErrorNote>{error}</ErrorNote>
      <Button type="submit" className="w-full" loading={saving}>
        Сохранить
      </Button>
    </form>
  );
}

export default function StatsPage() {
  useBackButton("/profile");
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .adminStats()
      .then(setStats)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="space-y-5 p-4">
      <PageTitle title="Статистика" />
      <ErrorNote>{error}</ErrorNote>
      {!stats && !error && <Skeleton className="h-64" />}
      {stats && (
        <>
          <Section title="Пользователи">
            <Metric value={stats.users_total} label="всего" />
            <Metric value={stats.users_new_7d} label="новых за 7 дней" tone="text-sky" />
            <Metric value={stats.accounts_total} label="аккаунтов подключено" />
            <Metric value={stats.accounts_active} label="с включённым автопилотом" tone="text-go" />
          </Section>
          <Section title="Рассылки">
            <Metric value={stats.campaigns_active} label="идут" tone="text-go" />
            <Metric value={stats.campaigns_paused} label="на паузе" tone="text-warn" />
            <Metric value={stats.campaigns_finished} label="завершены" />
          </Section>
          <Section title="Сообщения за 24 часа">
            <Metric value={stats.messages_sent_24h} label="доставлено" tone="text-go" />
            <Metric value={stats.messages_failed_24h} label="с ошибкой" tone="text-danger" />
          </Section>
        </>
      )}
      <ProSettings />
    </div>
  );
}
