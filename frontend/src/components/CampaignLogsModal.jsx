import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import Button from "./ui/Button.jsx";
import Card from "./ui/Card.jsx";

export default function CampaignLogsModal({ accountId, campaignId, onClose }) {
  const [logs, setLogs] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .listCampaignLogs(accountId, campaignId)
      .then(setLogs)
      .catch((err) => setError(err.message));
  }, [accountId, campaignId]);

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 p-4">
      <Card className="w-full max-w-md max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold">Логи отправки</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200"
            aria-label="Закрыть"
          >
            ✕
          </button>
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}
        {!error && !logs && <p className="text-sm text-slate-400">Загрузка…</p>}
        {logs && logs.length === 0 && (
          <p className="text-sm text-slate-500">Пока ничего не отправлялось.</p>
        )}

        <div className="overflow-y-auto space-y-2">
          {logs?.map((log) => (
            <div
              key={log.id}
              className="rounded-lg bg-slate-950 border border-slate-800 p-2.5 text-sm"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-slate-400">{log.chat_id}</span>
                <span
                  className={
                    log.status === "success"
                      ? "text-emerald-400 text-xs font-medium"
                      : "text-red-400 text-xs font-medium"
                  }
                >
                  {log.status === "success" ? "Отправлено" : "Ошибка"}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {new Date(log.sent_at).toLocaleString("ru-RU")}
              </p>
              {log.error_message && (
                <p className="text-xs text-red-400 mt-1 break-words">{log.error_message}</p>
              )}
            </div>
          ))}
        </div>

        <Button variant="secondary" className="mt-3" onClick={onClose}>
          Закрыть
        </Button>
      </Card>
    </div>
  );
}
