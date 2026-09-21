import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import StatCard from "../components/StatCard.jsx";
import Button from "../components/ui/Button.jsx";
import Card from "../components/ui/Card.jsx";
import { Input, Label } from "../components/ui/Input.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";

function TagFeatureSettings() {
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [justSaved, setJustSaved] = useState(false);

  useEffect(() => {
    api.adminGetTagFeature().then(setSettings).catch((err) => setError(err.message));
  }, []);

  async function handleSave(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const updated = await api.adminUpdateTagFeature({
        stars_price: Number(settings.stars_price),
        duration_days: Number(settings.duration_days),
      });
      setSettings(updated);
      setJustSaved(true);
      setTimeout(() => setJustSaved(false), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h2 className="text-sm uppercase text-slate-500 mb-2">Теги случайных участников</h2>
      <Card>
        {!settings ? (
          <p className="text-sm text-slate-400">Загрузка…</p>
        ) : (
          <form onSubmit={handleSave} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Цена, ⭐ Stars</Label>
                <Input
                  type="number"
                  min="1"
                  value={settings.stars_price}
                  onChange={(e) => setSettings({ ...settings, stars_price: e.target.value })}
                />
              </div>
              <div>
                <Label>Срок действия, дней</Label>
                <Input
                  type="number"
                  min="1"
                  value={settings.duration_days}
                  onChange={(e) => setSettings({ ...settings, duration_days: e.target.value })}
                />
              </div>
            </div>
            <p className="text-xs text-slate-500">
              Администраторы (`ADMIN_TELEGRAM_IDS`) пользуются функцией бесплатно и бессрочно —
              эти настройки касаются только платного доступа остальных пользователей.
            </p>
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={saving}>
                {saving ? "Сохранение…" : "Сохранить"}
              </Button>
              {justSaved && <span className="text-xs text-green-400">Сохранено</span>}
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}

export default function StatsPage() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.adminStats().then(setStats).catch((err) => setError(err.message));
  }, []);

  if (error) return <p className="p-4 text-red-400">{error}</p>;
  if (!stats) return <p className="p-4 text-slate-400">Загрузка…</p>;

  return (
    <div className="p-4 space-y-6">
      <PageHeader icon="📊" title="Статистика" />

      <TagFeatureSettings />

      <div>
        <h2 className="text-sm uppercase text-slate-500 mb-2">Пользователи</h2>
        <div className="grid grid-cols-2 gap-3">
          <StatCard label="Всего пользователей" value={stats.users_total} />
          <StatCard label="Новых за 7 дней" value={stats.users_new_7d} />
          <StatCard label="Подключено аккаунтов" value={stats.accounts_total} />
          <StatCard label="Активных аккаунтов" value={stats.accounts_active} />
        </div>
      </div>

      <div>
        <h2 className="text-sm uppercase text-slate-500 mb-2">Рассылки</h2>
        <div className="grid grid-cols-2 gap-3">
          <StatCard label="Активные кампании" value={stats.campaigns_active} />
          <StatCard label="На паузе" value={stats.campaigns_paused} />
          <StatCard label="Завершённые" value={stats.campaigns_finished} />
        </div>
      </div>

      <div>
        <h2 className="text-sm uppercase text-slate-500 mb-2">Сообщения (24ч)</h2>
        <div className="grid grid-cols-2 gap-3">
          <StatCard label="Отправлено успешно" value={stats.messages_sent_24h} />
          <StatCard label="Ошибок отправки" value={stats.messages_failed_24h} />
        </div>
      </div>
    </div>
  );
}
