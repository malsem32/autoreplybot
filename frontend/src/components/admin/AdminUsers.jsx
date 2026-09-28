import { Crown, Gift, Search, Smartphone, UserX } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client.js";
import plural from "../../lib/plural.js";
import { confirmDialog, haptic, openTelegramLink } from "../../lib/telegram.js";
import { useApp } from "../../state/AppContext.jsx";
import Button from "../ui/Button.jsx";
import { EmptyState, ErrorNote, Pill, Skeleton } from "../ui/Feedback.jsx";
import { Input } from "../ui/Input.jsx";
import Segmented from "../ui/Segmented.jsx";
import Sheet from "../ui/Sheet.jsx";

function fmtDate(iso, withTime = false) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("ru-RU", {
    day: "numeric",
    month: "short",
    year: "2-digit",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  });
}

function seen(iso) {
  if (!iso) return "не заходил";
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 15) return "онлайн недавно";
  if (minutes < 60 * 24) return `был ${Math.round(minutes / 60) || 1} ч назад`;
  return `был ${fmtDate(iso)}`;
}

function displayName(u) {
  return u.first_name || (u.username ? `@${u.username}` : `id ${u.telegram_id}`);
}

const GIFTS = [7, 30, 365];
const ACTIONS = { pro_grant: "Выдан Pro", pro_revoke: "Отозван Pro" };

function UserSheet({ userId, onClose, onChanged }) {
  const { toast } = useApp();
  const [user, setUser] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [customDays, setCustomDays] = useState("");

  useEffect(() => {
    if (!userId) return;
    setUser(null);
    setError("");
    api
      .adminUser(userId)
      .then(setUser)
      .catch((err) => setError(err.message));
  }, [userId]);

  async function gift(days) {
    if (!days || days < 1) return;
    setBusy(`g${days}`);
    try {
      const next = await api.adminGrantPro(userId, days);
      setUser(next);
      onChanged(next);
      haptic.success();
      toast(`Pro +${days} дн. выдан — пользователь получил уведомление`);
      setCustomDays("");
    } catch (err) {
      toast(err.message, "danger");
    } finally {
      setBusy("");
    }
  }

  async function revoke() {
    if (!(await confirmDialog("Отключить Pro у этого пользователя прямо сейчас?"))) return;
    setBusy("revoke");
    try {
      const next = await api.adminRevokePro(userId);
      setUser(next);
      onChanged(next);
      haptic.warning();
      toast("Pro отключён");
    } catch (err) {
      toast(err.message, "danger");
    } finally {
      setBusy("");
    }
  }

  return (
    <Sheet
      open={Boolean(userId)}
      onClose={onClose}
      title={user ? displayName(user) : "Пользователь"}
    >
      <div className="space-y-4 pt-1">
        <ErrorNote>{error}</ErrorNote>
        {!user && !error && <Skeleton className="h-48" />}
        {user && (
          <>
            <div className="rounded-tile bg-raised/50 p-3.5 text-[13px] leading-relaxed text-muted">
              <p>
                id <span className="font-mono text-ink">{user.telegram_id}</span>
                {user.username && (
                  <>
                    {" · "}
                    <button
                      type="button"
                      className="font-semibold text-sky"
                      onClick={() => openTelegramLink(`https://t.me/${user.username}`)}
                    >
                      @{user.username}
                    </button>
                  </>
                )}
              </p>
              <p>
                С нами с {fmtDate(user.created_at)} · {seen(user.last_seen_at)}
              </p>
              <p>
                Пригласил: {user.referrals} · пришёл по ссылке:{" "}
                {user.referred_by_telegram_id ? `id ${user.referred_by_telegram_id}` : "нет"}
                {user.trial_used_at ? " · пробный период использован" : ""}
              </p>
            </div>

            <section className="rounded-tile bg-surface p-3.5 ring-1 ring-line/60">
              <div className="flex items-center justify-between gap-2">
                <p className="flex items-center gap-2 text-[15px] font-semibold">
                  <Crown className="h-4 w-4 text-warn" aria-hidden /> Pro
                </p>
                {user.has_pro ? (
                  <Pill tone="warn" dot>
                    до {fmtDate(user.pro_expires_at)}
                  </Pill>
                ) : (
                  <Pill tone="muted">нет</Pill>
                )}
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2">
                {GIFTS.map((d) => (
                  <Button
                    key={d}
                    size="sm"
                    variant="secondary"
                    loading={busy === `g${d}`}
                    onClick={() => gift(d)}
                  >
                    +{d} дн.
                  </Button>
                ))}
              </div>
              <div className="mt-2 flex gap-2">
                <Input
                  type="number"
                  min="1"
                  max="3650"
                  inputMode="numeric"
                  placeholder="Своё число дней"
                  value={customDays}
                  onChange={(e) => setCustomDays(e.target.value)}
                />
                <Button
                  icon={Gift}
                  variant="pro"
                  className="shrink-0 px-4"
                  disabled={!Number(customDays)}
                  loading={busy === `g${Number(customDays)}`}
                  onClick={() => gift(Number(customDays))}
                  aria-label="Выдать"
                />
              </div>
              {user.has_pro && (
                <Button
                  variant="danger"
                  size="sm"
                  icon={UserX}
                  className="mt-2 w-full"
                  loading={busy === "revoke"}
                  onClick={revoke}
                >
                  Отключить Pro
                </Button>
              )}
            </section>

            <section>
              <h3 className="mb-2 px-1 text-[13px] font-medium text-muted">
                Аккаунты Telegram · {user.account_list.length}
              </h3>
              {user.account_list.length === 0 ? (
                <p className="px-1 text-[13px] text-faint">Ещё не подключил ни одного.</p>
              ) : (
                <ul className="space-y-2">
                  {user.account_list.map((a) => (
                    <li key={a.id} className="rounded-tile bg-raised/50 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="flex min-w-0 items-center gap-2 text-[14px] font-semibold">
                          <Smartphone className="h-4 w-4 shrink-0 text-sky" aria-hidden />
                          <span className="truncate">
                            {a.first_name || (a.username ? `@${a.username}` : "Без имени")}
                          </span>
                        </p>
                        <Pill tone={a.is_active ? "go" : "muted"} dot>
                          {a.is_active ? "работает" : "выключен"}
                        </Pill>
                      </div>
                      <p className="mt-1 text-[12px] leading-relaxed text-muted">
                        <span className="font-mono">{a.phone}</span>
                        {a.username ? ` · @${a.username}` : ""} · с {fmtDate(a.created_at)}
                      </p>
                      <p className="text-[12px] text-faint">
                        {a.rules} {plural(a.rules, "правило", "правила", "правил")} · {a.campaigns}{" "}
                        {plural(a.campaigns, "рассылка", "рассылки", "рассылок")} · {a.leads}{" "}
                        {plural(a.leads, "клиент", "клиента", "клиентов")} · {a.autoreplies_7d}{" "}
                        ответов за 7 дн.
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {user.payments.length > 0 && (
              <section>
                <h3 className="mb-2 px-1 text-[13px] font-medium text-muted">Оплаты</h3>
                <ul className="divide-y divide-line/50 rounded-tile bg-raised/50 text-[13px]">
                  {user.payments.map((p) => (
                    <li key={p.created_at} className="flex justify-between px-3 py-2">
                      <span className="text-muted">
                        {fmtDate(p.created_at, true)} · {p.days} дн.
                      </span>
                      <span className="font-semibold tabular-nums">{p.stars} ⭐</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {user.audit.length > 0 && (
              <section>
                <h3 className="mb-2 px-1 text-[13px] font-medium text-muted">Действия админов</h3>
                <ul className="space-y-1 px-1 text-[12px] text-faint">
                  {user.audit.map((e) => (
                    <li key={`${e.created_at}${e.action}`}>
                      {fmtDate(e.created_at, true)} · {ACTIONS[e.action] || e.action} {e.details} ·
                      админ {e.admin_telegram_id}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
      </div>
    </Sheet>
  );
}

/** Admin: find users, see their connected accounts, gift or revoke Pro. */
export default function AdminUsers() {
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("all");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState(null);
  const timer = useRef(null);

  useEffect(() => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      api
        .adminUsers(q.trim(), filter)
        .then((d) => {
          setData(d);
          setError("");
        })
        .catch((err) => setError(err.message));
    }, 250);
    return () => clearTimeout(timer.current);
  }, [q, filter]);

  function patchRow(detail) {
    setData((d) =>
      d
        ? {
            ...d,
            users: d.users.map((u) =>
              u.id === detail.id
                ? { ...u, has_pro: detail.has_pro, pro_expires_at: detail.pro_expires_at }
                : u,
            ),
          }
        : d,
    );
  }

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Имя, @username или id"
          className="pl-10"
          autoCapitalize="none"
        />
      </div>
      <Segmented
        value={filter}
        onChange={setFilter}
        options={[
          { value: "all", label: "Все" },
          { value: "accounts", label: "С аккаунтами" },
          { value: "pro", label: "Pro" },
        ]}
      />
      <ErrorNote>{error}</ErrorNote>
      {data === null && !error ? (
        <Skeleton className="h-40" />
      ) : data?.users.length === 0 ? (
        <EmptyState icon={Search} title="Никого не нашли" text="Проверьте имя, @username или id." />
      ) : (
        data && (
          <>
            <p className="px-1 text-[12px] text-faint">
              Найдено: {data.total}
              {data.total > data.users.length ? ` · показаны первые ${data.users.length}` : ""}
            </p>
            <ul className="overflow-hidden rounded-[18px] bg-surface">
              {data.users.map((u) => (
                <li key={u.id} className="border-b border-line/50 last:border-0">
                  <button
                    type="button"
                    onClick={() => setOpenId(u.id)}
                    className="flex w-full items-center gap-3 px-4 py-3 text-left active:bg-raised/60"
                  >
                    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-gradient-to-br from-sky to-[#1E6FD9] font-display text-sm font-semibold text-white">
                      {displayName(u).replace("@", "").slice(0, 1).toUpperCase()}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-1.5">
                        <span className="truncate text-[15px] font-semibold">{displayName(u)}</span>
                        {u.has_pro && <Crown className="h-3.5 w-3.5 shrink-0 text-warn" />}
                      </span>
                      <span className="block truncate text-[12px] text-muted">
                        {u.accounts > 0
                          ? `${u.accounts} ${plural(u.accounts, "аккаунт", "аккаунта", "аккаунтов")}`
                          : "без аккаунтов"}{" "}
                        · {seen(u.last_seen_at)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )
      )}
      <UserSheet userId={openId} onClose={() => setOpenId(null)} onChanged={patchRow} />
    </div>
  );
}
