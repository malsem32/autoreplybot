import { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function BroadcastPage({ accountId }) {
  const [campaigns, setCampaigns] = useState([]);
  const [title, setTitle] = useState("");
  const [textTemplate, setTextTemplate] = useState("");
  const [chatIds, setChatIds] = useState("");
  const [intervalMinutes, setIntervalMinutes] = useState(60);
  const [error, setError] = useState("");

  useEffect(() => {
    if (accountId) {
      api.listCampaigns(accountId).then(setCampaigns).catch((err) => setError(err.message));
    }
  }, [accountId]);

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    try {
      const campaign = await api.createCampaign(accountId, {
        title,
        text_template: textTemplate,
        target_chat_ids: chatIds
          .split(",")
          .map((id) => Number(id.trim()))
          .filter(Boolean),
        interval_minutes: Number(intervalMinutes),
      });
      setCampaigns((prev) => [...prev, campaign]);
      setTitle("");
      setTextTemplate("");
      setChatIds("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handlePause(campaignId) {
    try {
      const updated = await api.pauseCampaign(accountId, campaignId);
      setCampaigns((prev) => prev.map((c) => (c.id === campaignId ? updated : c)));
    } catch (err) {
      setError(err.message);
    }
  }

  if (!accountId) {
    return <p className="p-4 text-slate-400">Сначала подключите аккаунт на вкладке «Аккаунт».</p>;
  }

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-lg font-semibold">Рассылки</h1>

      <form onSubmit={handleCreate} className="space-y-3">
        <input
          className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2"
          placeholder="Название кампании"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <textarea
          className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2"
          placeholder="Текст, поддерживает {вариант1|вариант2}"
          value={textTemplate}
          onChange={(e) => setTextTemplate(e.target.value)}
          required
        />
        <input
          className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2"
          placeholder="ID чатов через запятую"
          value={chatIds}
          onChange={(e) => setChatIds(e.target.value)}
          required
        />
        <input
          className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2"
          type="number"
          min="1"
          value={intervalMinutes}
          onChange={(e) => setIntervalMinutes(e.target.value)}
        />
        <button className="w-full rounded-lg bg-blue-600 py-2 font-medium" type="submit">
          Создать кампанию
        </button>
      </form>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <ul className="space-y-2">
        {campaigns.map((c) => (
          <li key={c.id} className="rounded-lg bg-slate-900 border border-slate-800 p-3">
            <div className="flex items-center justify-between">
              <p className="font-medium">{c.title}</p>
              <span className="text-xs text-slate-400">{c.status}</span>
            </div>
            <p className="text-sm text-slate-400 mt-1">{c.text_template}</p>
            {c.status === "active" && (
              <button
                className="mt-2 text-sm text-blue-400"
                onClick={() => handlePause(c.id)}
                type="button"
              >
                Поставить на паузу
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
