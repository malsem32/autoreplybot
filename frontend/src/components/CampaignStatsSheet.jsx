import { AlertTriangle, CheckCircle2, CircleSlash, Download, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { haptic } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";
import Button from "./ui/Button.jsx";
import { EmptyState, ErrorNote, Pill, Skeleton } from "./ui/Feedback.jsx";
import Sheet from "./ui/Sheet.jsx";

function formatTime(iso) {
  if (!iso) return "ещё не отправлялось";
  return new Date(iso).toLocaleString("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Pro: delivery statistics per target chat, with a way to bring back chats
 * the autopilot switched off after repeated failures. */
export default function CampaignStatsSheet({ open, onClose, accountId, campaign, onChanged }) {
  const { toast } = useApp();
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [restoring, setRestoring] = useState("");
  const [exporting, setExporting] = useState(false);

  async function exportCsv() {
    setExporting(true);
    try {
      const { rows } = await api.exportCampaign(accountId, campaign.id);
      haptic.success();
      toast(`Файл (${rows} строк) отправлен в чат с ботом`);
    } catch (err) {
      toast(err.message, "danger");
    } finally {
      setExporting(false);
    }
  }

  useEffect(() => {
    if (!open || !campaign) return;
    setStats(null);
    setError("");
    api
      .getCampaignStats(accountId, campaign.id)
      .then(setStats)
      .catch((err) => setError(err.message));
  }, [open, accountId, campaign]);

  async function restore(target) {
    setRestoring(target);
    try {
      const updated = await api.updateCampaign(accountId, campaign.id, {
        disabled_targets: campaign.disabled_targets.filter((t) => t !== target),
      });
      onChanged(updated);
      setStats((s) => ({
        ...s,
        targets: s.targets.map((t) => (t.target === target ? { ...t, disabled: false } : t)),
      }));
      haptic.success();
      toast("Чат снова в рассылке");
    } catch (err) {
      toast(err.message, "danger");
    } finally {
      setRestoring("");
    }
  }

  const total = stats ? stats.sent + stats.failed : 0;
  const rate = total ? Math.round((stats.sent / total) * 100) : 0;

  return (
    <Sheet open={open} onClose={onClose} title={campaign ? `Статистика: ${campaign.title}` : ""}>
      <div className="space-y-4 pt-1">
        <ErrorNote>{error}</ErrorNote>
        {!stats && !error && (
          <>
            <Skeleton className="h-20" />
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </>
        )}
        {stats && total === 0 && (
          <EmptyState
            title="Данных пока нет"
            text="Статистика появится после первой отправки в эти чаты."
          />
        )}
        {stats && total > 0 && (
          <div className="rounded-tile bg-raised/50 p-4">
            <div className="flex items-end justify-between">
              <div>
                <p className="font-display text-[28px] font-semibold leading-none">{rate}%</p>
                <p className="mt-1.5 text-[13px] text-muted">доставляемость</p>
              </div>
              <p className="text-right text-[13px] leading-relaxed text-muted">
                <span className="font-semibold text-go">{stats.sent}</span> доставлено
                <br />
                <span className="font-semibold text-danger">{stats.failed}</span> с ошибкой
              </p>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-danger/25">
              <div className="h-full rounded-full bg-go" style={{ width: `${rate}%` }} />
            </div>
            <Button
              size="sm"
              variant="secondary"
              icon={Download}
              className="mt-3 w-full"
              loading={exporting}
              onClick={exportCsv}
            >
              Выгрузить журнал в CSV
            </Button>
          </div>
        )}
        {stats && (
          <ul className="space-y-2">
            {stats.targets.map((t) => {
              const Icon = t.disabled
                ? CircleSlash
                : t.last_status === "success"
                  ? CheckCircle2
                  : t.last_status
                    ? AlertTriangle
                    : CheckCircle2;
              const tone = t.disabled
                ? "text-faint"
                : t.last_status === "success"
                  ? "text-go"
                  : t.last_status
                    ? "text-warn"
                    : "text-faint";
              return (
                <li key={t.target} className="rounded-tile bg-raised/50 p-3">
                  <div className="flex items-start gap-3">
                    <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${tone}`} aria-hidden />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-[15px] font-semibold">{t.target}</span>
                        {t.disabled && <Pill tone="muted">отключён</Pill>}
                      </div>
                      <p className="mt-0.5 text-[13px] text-muted">
                        {t.sent} доставлено · {t.failed} ошибок · {formatTime(t.last_sent_at)}
                      </p>
                      {t.last_status && t.last_status !== "success" && t.last_error && (
                        <p className="mt-1 break-words text-[12px] leading-snug text-faint">
                          {t.last_error}
                        </p>
                      )}
                    </div>
                  </div>
                  {t.disabled && (
                    <Button
                      size="sm"
                      variant="secondary"
                      icon={RotateCcw}
                      className="mt-2 w-full"
                      loading={restoring === t.target}
                      onClick={() => restore(t.target)}
                    >
                      Вернуть в рассылку
                    </Button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </Sheet>
  );
}
