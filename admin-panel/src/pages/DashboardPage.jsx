import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import StatCard from "../components/StatCard.jsx";

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.stats().then(setStats).catch((err) => setError(err.message));
  }, []);

  if (error) return <p className="p-6 text-red-400">{error}</p>;
  if (!stats) return <p className="p-6 text-slate-400">Загрузка…</p>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">Статистика</h1>

      <div>
        <h2 className="text-sm uppercase text-slate-500 mb-2">Пользователи</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Всего пользователей" value={stats.users_total} />
          <StatCard label="Новых за 7 дней" value={stats.users_new_7d} />
          <StatCard label="Подключено аккаунтов" value={stats.accounts_total} />
          <StatCard label="Активных аккаунтов" value={stats.accounts_active} />
        </div>
      </div>

      <div>
        <h2 className="text-sm uppercase text-slate-500 mb-2">Рассылки</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Активные кампании" value={stats.campaigns_active} />
          <StatCard label="На паузе" value={stats.campaigns_paused} />
          <StatCard label="Завершённые" value={stats.campaigns_finished} />
        </div>
      </div>

      <div>
        <h2 className="text-sm uppercase text-slate-500 mb-2">Сообщения (24ч)</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Отправлено успешно" value={stats.messages_sent_24h} />
          <StatCard label="Ошибок отправки" value={stats.messages_failed_24h} />
        </div>
      </div>
    </div>
  );
}
