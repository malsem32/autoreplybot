import { useEffect, useState } from "react";
import AdminUsers from "../components/admin/AdminUsers.jsx";
import BarChart from "../components/admin/BarChart.jsx";
import PageTitle from "../components/PageTitle.jsx";
import Button from "../components/ui/Button.jsx";
import { ErrorNote, Skeleton } from "../components/ui/Feedback.jsx";
import { Field, Input } from "../components/ui/Input.jsx";
import Segmented from "../components/ui/Segmented.jsx";
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
          quarter_stars_price: Number(form.quarter_stars_price),
          year_stars_price: Number(form.year_stars_price),
          trial_days: Number(form.trial_days),
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
        <Field label="Базовый тариф, Stars" htmlFor="p-price">
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
        <Field label="3 месяца, Stars" hint="0 — скрыть" htmlFor="p-q">
          <Input
            id="p-q"
            type="number"
            min="0"
            inputMode="numeric"
            value={form.quarter_stars_price}
            onChange={set("quarter_stars_price")}
          />
        </Field>
        <Field label="Год, Stars" hint="0 — скрыть" htmlFor="p-y">
          <Input
            id="p-y"
            type="number"
            min="0"
            inputMode="numeric"
            value={form.year_stars_price}
            onChange={set("year_stars_price")}
          />
        </Field>
      </div>
      <Field label="Пробный период, дней" hint="один раз, 0 — выключить" htmlFor="p-trial">
        <Input
          id="p-trial"
          type="number"
          min="0"
          max="30"
          inputMode="numeric"
          value={form.trial_days}
          onChange={set("trial_days")}
        />
      </Field>
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

function Overview() {
  const [stats, setStats] = useState(null);
  const [series, setSeries] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.adminStats(), api.adminTimeseries()])
      .then(([s, t]) => {
        setStats(s);
        setSeries(t);
      })
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <ErrorNote>{error}</ErrorNote>;
  if (!stats || !series) return <Skeleton className="h-64" />;

  const stars = (v) => `${v.toLocaleString("ru-RU")} ⭐`;
  return (
    <div className="space-y-5">
      <Section title="Главное">
        <Metric
          value={stats.users_total}
          label={`пользователей · +${stats.users_new_7d} за неделю`}
        />
        <Metric value={stats.pro_active} label="с активным Pro" tone="text-warn" />
        <Metric
          value={stats.accounts_total}
          label={`аккаунтов · ${stats.accounts_active} работают`}
          tone="text-go"
        />
        <Metric
          value={stars(series.stars_30d)}
          label={`выручка за 30 дней · ${series.payments_30d} оплат`}
        />
      </Section>

      <div className="space-y-3">
        <BarChart
          title="Новые пользователи"
          days={series.days}
          series={[{ key: "u", label: "Новые", values: series.users, color: "rgb(var(--sky))" }]}
        />
        <BarChart
          title="Выручка"
          days={series.days}
          format={stars}
          note={`за 30 дней · всего за всё время ${stars(series.stars_total)}`}
          series={[{ key: "s", label: "Stars", values: series.stars, color: "rgb(var(--warn))" }]}
        />
        <BarChart
          title="Автоответы"
          days={series.days}
          series={[
            { key: "a", label: "Ответы", values: series.autoreplies, color: "rgb(var(--sky))" },
          ]}
        />
        <BarChart
          title="Сообщения рассылок"
          days={series.days}
          series={[
            { key: "ok", label: "Доставлено", values: series.sent, color: "rgb(var(--go))" },
            { key: "err", label: "Ошибка", values: series.failed, color: "rgb(var(--danger))" },
          ]}
        />
      </div>

      <Section title="Рассылки сейчас">
        <Metric value={stats.campaigns_active} label="идут" tone="text-go" />
        <Metric value={stats.campaigns_paused} label="на паузе" tone="text-warn" />
        <Metric value={stats.campaigns_finished} label="завершены" />
        <Metric
          value={stats.flood_waits_24h}
          label={`FloodWait за сутки · ${Math.round(stats.flood_wait_seconds_24h / 60)} мин ожидания`}
          tone={stats.flood_waits_24h ? "text-warn" : "text-ink"}
        />
      </Section>
    </div>
  );
}

export default function StatsPage() {
  useBackButton("/profile");
  const [tab, setTab] = useState("overview");

  return (
    <div className="space-y-4 p-4">
      <PageTitle title="Админка" subtitle="Видно только администраторам" />
      <Segmented
        value={tab}
        onChange={setTab}
        options={[
          { value: "overview", label: "Обзор" },
          { value: "users", label: "Люди" },
          { value: "prices", label: "Цены" },
        ]}
      />
      {tab === "overview" && <Overview />}
      {tab === "users" && <AdminUsers />}
      {tab === "prices" && <ProSettings />}
    </div>
  );
}
