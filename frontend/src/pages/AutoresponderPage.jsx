import { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function AutoresponderPage({ accountId }) {
  const [rules, setRules] = useState([]);
  const [responseText, setResponseText] = useState("");
  const [triggerType, setTriggerType] = useState("all");
  const [keywords, setKeywords] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (accountId) {
      api.listRules(accountId).then(setRules).catch((err) => setError(err.message));
    }
  }, [accountId]);

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    try {
      const rule = await api.createRule(accountId, {
        is_enabled: true,
        trigger_type: triggerType,
        keywords: triggerType === "keywords" ? keywords.split(",").map((k) => k.trim()) : [],
        response_text: responseText,
        cooldown_seconds: 3600,
      });
      setRules((prev) => [...prev, rule]);
      setResponseText("");
      setKeywords("");
    } catch (err) {
      setError(err.message);
    }
  }

  if (!accountId) {
    return <p className="p-4 text-slate-400">Сначала подключите аккаунт на вкладке «Аккаунт».</p>;
  }

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-lg font-semibold">Автоответчик</h1>

      <form onSubmit={handleCreate} className="space-y-3">
        <select
          className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2"
          value={triggerType}
          onChange={(e) => setTriggerType(e.target.value)}
        >
          <option value="all">Отвечать на все сообщения</option>
          <option value="keywords">Только по ключевым словам</option>
        </select>

        {triggerType === "keywords" && (
          <input
            className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2"
            placeholder="цена, стоимость, купить"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
          />
        )}

        <textarea
          className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2"
          placeholder="Текст автоответа, поддерживает {вариант1|вариант2}"
          value={responseText}
          onChange={(e) => setResponseText(e.target.value)}
          required
        />

        <button className="w-full rounded-lg bg-blue-600 py-2 font-medium" type="submit">
          Добавить правило
        </button>
      </form>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <ul className="space-y-2">
        {rules.map((rule) => (
          <li key={rule.id} className="rounded-lg bg-slate-900 border border-slate-800 p-3">
            <p className="text-sm text-slate-400">
              {rule.trigger_type === "all" ? "Все сообщения" : rule.keywords.join(", ")}
            </p>
            <p>{rule.response_text}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
