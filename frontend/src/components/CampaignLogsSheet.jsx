import { CheckCircle2, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { EmptyState, ErrorNote, Skeleton } from "./ui/Feedback.jsx";
import Sheet from "./ui/Sheet.jsx";

function formatTime(iso) {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function CampaignLogsSheet({ open, onClose, accountId, campaign }) {
  const [logs, setLogs] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !campaign) return;
    setLogs(null);
    setError("");
    api
      .listCampaignLogs(accountId, campaign.id)
      .then(setLogs)
      .catch((err) => setError(err.message));
  }, [open, accountId, campaign]);

  const sent = logs?.filter((l) => l.status === "success").length ?? 0;
  const failed = logs?.filter((l) => l.status !== "success").length ?? 0;

  return (
    <Sheet open={open} onClose={onClose} title={campaign ? `Журнал: ${campaign.title}` : "Журнал"}>
      <div className="space-y-3 pt-1">
        <ErrorNote>{error}</ErrorNote>
        {!logs && !error && (
          <>
            <Skeleton className="h-14" />
            <Skeleton className="h-14" />
          </>
        )}
        {logs && logs.length === 0 && (
          <EmptyState
            title="Отправок пока не было"
            text="Первая отправка появится здесь в течение минуты после запуска."
          />
        )}
        {logs && logs.length > 0 && (
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-tile bg-go/10 p-3">
              <p className="font-display text-2xl font-semibold text-go">{sent}</p>
              <p className="text-[13px] text-muted">доставлено</p>
            </div>
            <div className="rounded-tile bg-danger/10 p-3">
              <p className="font-display text-2xl font-semibold text-danger">{failed}</p>
              <p className="text-[13px] text-muted">с ошибкой</p>
            </div>
          </div>
        )}
        <ul className="space-y-1.5">
          {logs?.map((log) => (
            <li key={log.id} className="flex gap-3 rounded-tile bg-raised/50 p-3">
              {log.status === "success" ? (
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-go" aria-label="Доставлено" />
              ) : (
                <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-danger" aria-label="Ошибка" />
              )}
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="truncate text-sm font-medium">
                    {log.chat_id ? `Чат ${log.chat_id}` : "Чат не найден"}
                  </span>
                  <span className="shrink-0 text-xs text-faint">{formatTime(log.sent_at)}</span>
                </div>
                {log.error_message && (
                  <p className="mt-0.5 break-words text-[13px] leading-snug text-muted">
                    {log.error_message}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </Sheet>
  );
}
