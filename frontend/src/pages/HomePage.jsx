import { motion } from "framer-motion";
import { Crown, Gift, Inbox, MessageCircleReply, Plus, Send } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import AccountSwitcher from "../components/AccountSwitcher.jsx";
import Horizon from "../components/Horizon.jsx";
import AddAccountSheet from "../components/login/AddAccountSheet.jsx";
import Button from "../components/ui/Button.jsx";
import { ErrorNote, Skeleton } from "../components/ui/Feedback.jsx";
import { ListGroup, ListRow } from "../components/ui/List.jsx";
import Switch from "../components/ui/Switch.jsx";
import plural from "../lib/plural.js";
import { haptic } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";

function Welcome({ onAdd }) {
  return (
    <div className="flex min-h-[78vh] flex-col items-center justify-center px-2 text-center">
      <motion.div
        initial={{ scale: 0.85, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 160, damping: 18 }}
      >
        <Horizon engaged={false} size={196} />
      </motion.div>
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="mt-8"
      >
        <h1 className="font-display text-[26px] font-semibold leading-tight tracking-tight">
          Автопилот для вашего Telegram
        </h1>
        <p className="mx-auto mt-3 max-w-[32ch] text-[15px] leading-relaxed text-muted">
          Отвечает клиентам, пока вы заняты, и отправляет рассылки по вашим чатам с соблюдением
          лимитов Telegram.
        </p>
        <Button className="mt-7 w-full max-w-xs" icon={Plus} onClick={onAdd}>
          Подключить аккаунт
        </Button>
        <p className="mt-3 text-[13px] text-faint">Займёт пару минут: номер и код из Telegram</p>
      </motion.div>
    </div>
  );
}

export default function HomePage() {
  const { accounts, accountsError, activeAccount, upsertAccount, pro, toast } = useApp();
  const navigate = useNavigate();
  const [adding, setAdding] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [counts, setCounts] = useState(null);
  const [newLeads, setNewLeads] = useState(null);

  useEffect(() => {
    if (!activeAccount || !pro?.has_access) return;
    let cancelled = false;
    api
      .listLeads(activeAccount.id, "new")
      .then((data) => !cancelled && setNewLeads(data.counts.new))
      .catch(() => !cancelled && setNewLeads(0));
    return () => {
      cancelled = true;
    };
  }, [activeAccount, pro?.has_access]);

  useEffect(() => {
    if (!activeAccount) return;
    let cancelled = false;
    setCounts(null);
    Promise.all([api.listRules(activeAccount.id), api.listCampaigns(activeAccount.id)])
      .then(([rules, campaigns]) => {
        if (cancelled) return;
        setCounts({
          rules: rules.filter((r) => r.is_enabled).length,
          rulesTotal: rules.length,
          campaigns: campaigns.filter((c) => c.status === "active").length,
          campaignsTotal: campaigns.length,
        });
      })
      .catch(
        () => !cancelled && setCounts({ rules: 0, rulesTotal: 0, campaigns: 0, campaignsTotal: 0 }),
      );
    return () => {
      cancelled = true;
    };
  }, [activeAccount]);

  async function toggleEngaged(next) {
    setToggling(true);
    try {
      const updated = await api.updateAccount(activeAccount.id, { is_active: next });
      upsertAccount(updated);
      if (next) haptic.success();
      else haptic.warning();
    } catch (err) {
      toast(err.message, "danger");
    } finally {
      setToggling(false);
    }
  }

  if (accounts === null) {
    return (
      <div className="space-y-4 p-4 pt-6">
        <Skeleton className="mx-auto h-52 w-52 !rounded-full" />
        <Skeleton className="h-20" />
        <Skeleton className="h-36" />
      </div>
    );
  }

  if (!activeAccount) {
    return (
      <div className="p-4">
        <ErrorNote>{accountsError}</ErrorNote>
        <Welcome onAdd={() => setAdding(true)} />
        <AddAccountSheet open={adding} onClose={() => setAdding(false)} />
      </div>
    );
  }

  const engaged = activeAccount.is_active;

  return (
    <div className="space-y-6 p-4">
      <header className="flex items-center justify-between">
        <AccountSwitcher />
        {pro?.has_access ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-warn/15 px-3 py-1.5 text-xs font-bold text-warn">
            <Crown className="h-3.5 w-3.5" /> Pro
          </span>
        ) : (
          <button
            type="button"
            onClick={() => navigate("/profile")}
            className="inline-flex items-center gap-1.5 rounded-full bg-surface px-3 py-1.5 text-xs font-semibold text-muted"
          >
            <Crown className="h-3.5 w-3.5 text-warn" /> Получить Pro
          </button>
        )}
      </header>

      <section className="flex flex-col items-center pt-2 text-center">
        <Horizon engaged={engaged} />
        <motion.h1
          key={String(engaged)}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-7 font-display text-[24px] font-semibold tracking-tight"
        >
          {engaged ? "Автопилот включён" : "Автопилот на паузе"}
        </motion.h1>
        <p className="mt-2 max-w-[34ch] text-[14px] leading-relaxed text-muted">
          {engaged
            ? "Автоответы и рассылки этого аккаунта работают, даже когда вы не в сети."
            : "Автоответы и рассылки остановлены. Включите, когда будете готовы."}
        </p>
        <div className="mt-5 flex w-full items-center justify-between rounded-[18px] bg-surface px-4 py-3.5">
          <span className="text-[15px] font-semibold">{engaged ? "Работает" : "Остановлен"}</span>
          <Switch
            checked={engaged}
            onChange={toggleEngaged}
            disabled={toggling}
            label="Включить автопилот"
          />
        </div>
      </section>

      <ListGroup title="Что делает автопилот">
        <ListRow
          icon={MessageCircleReply}
          title="Автоответчик"
          subtitle={
            counts
              ? counts.rulesTotal
                ? counts.rules
                  ? `${counts.rules} ${plural(counts.rules, "правило активно", "правила активны", "правил активно")}`
                  : "Все правила выключены"
                : "Правил пока нет — добавьте первое"
              : "Загрузка…"
          }
          chevron
          onClick={() => navigate("/autoresponder")}
        />
        <ListRow
          icon={Send}
          iconClass="bg-go/15 text-go"
          title="Рассылки"
          subtitle={
            counts
              ? counts.campaignsTotal
                ? counts.campaigns
                  ? `${counts.campaigns} ${plural(counts.campaigns, "рассылка идёт", "рассылки идут", "рассылок идёт")}`
                  : "Все рассылки на паузе или завершены"
                : "Рассылок пока нет — создайте первую"
              : "Загрузка…"
          }
          chevron
          onClick={() => navigate("/broadcast")}
        />
        <ListRow
          icon={Inbox}
          iconClass="bg-warn/15 text-warn"
          title="Обращения"
          subtitle={
            !pro?.has_access
              ? "Мини-CRM всех, кто вам написал — в Pro"
              : newLeads === null
                ? "Загрузка…"
                : newLeads
                  ? `${newLeads} ${plural(newLeads, "новое ждёт ответа", "новых ждут ответа", "новых ждут ответа")}`
                  : "Новых нет — всё разобрано"
          }
          right={
            newLeads > 0 ? (
              <span className="grid h-6 min-w-6 place-items-center rounded-full bg-sky px-1.5 text-xs font-bold text-onsky">
                {newLeads}
              </span>
            ) : null
          }
          chevron
          onClick={() => navigate("/leads")}
        />
        <ListRow
          icon={Gift}
          iconClass="bg-warn/15 text-warn"
          title="Пригласить друга"
          subtitle="Вы оба получите дни Pro бесплатно"
          chevron
          onClick={() => navigate("/profile")}
        />
      </ListGroup>
    </div>
  );
}
