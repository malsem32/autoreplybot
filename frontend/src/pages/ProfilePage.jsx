import { AnimatePresence, motion } from "framer-motion";
import { BarChart3, ChevronDown, Copy, Crown, Gift, Globe, Share2, Star } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import DigestToggle from "../components/DigestToggle.jsx";
import HelpCard from "../components/HelpCard.jsx";
import PageTitle from "../components/PageTitle.jsx";
import TeamCard from "../components/TeamCard.jsx";
import {
  defaultPlan,
  formatDate,
  PlanPicker,
  ProFeatures,
  useBuyPro,
} from "../components/pro/PaywallSheet.jsx";
import Button from "../components/ui/Button.jsx";
import { ErrorNote, Skeleton } from "../components/ui/Feedback.jsx";
import { ListGroup, ListRow } from "../components/ui/List.jsx";
import plural from "../lib/plural.js";
import { copyText, haptic, shareLink } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";

function ProCard() {
  const { pro } = useApp();
  const { buy, trial, buying, error } = useBuyPro();
  const [plan, setPlan] = useState("year");
  const [showFeatures, setShowFeatures] = useState(false);

  useEffect(() => {
    if (pro) setPlan(defaultPlan(pro));
  }, [pro]);

  if (!pro) return <Skeleton className="h-64 !rounded-[22px]" />;
  const selected = pro.plans?.find((p) => p.id === plan);
  const featureCount = pro.feature_groups.reduce((n, g) => n + g.items.length, 0);

  return (
    <section className="relative overflow-hidden rounded-[22px] bg-surface p-5">
      <div
        className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-[radial-gradient(closest-side,rgb(var(--warn)/0.22),transparent)]"
        aria-hidden
      />
      <div className="relative">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-warn text-[#2A1A00]">
            <Crown className="h-6 w-6" />
          </span>
          <div>
            <h2 className="font-display text-[18px] font-semibold">Автопилот Pro</h2>
            <p className="text-[13px] text-muted">
              {pro.has_access
                ? pro.is_admin
                  ? "Бессрочно, как администратору"
                  : `Активен до ${formatDate(pro.expires_at)}`
                : "Расписание, умные автоответы, статистика и безлимит"}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setShowFeatures((v) => !v)}
          aria-expanded={showFeatures}
          className="mt-4 flex w-full items-center justify-between rounded-tile bg-raised/50 px-3.5 py-3 text-left text-[14px] font-semibold"
        >
          Что входит в Pro
          <span className="flex items-center gap-1.5 text-[13px] font-medium text-muted">
            {featureCount} {plural(featureCount, "функция", "функции", "функций")}
            <ChevronDown
              className={`h-4 w-4 transition-transform ${showFeatures ? "rotate-180" : ""}`}
              aria-hidden
            />
          </span>
        </button>
        <AnimatePresence initial={false}>
          {showFeatures && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="pt-4">
                <ProFeatures groups={pro.feature_groups} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        {!pro.is_admin && pro.plans?.length > 0 && (
          <div className="mt-6">
            <PlanPicker plans={pro.plans} value={plan} onChange={setPlan} />
          </div>
        )}
        {!pro.is_admin && selected && (
          <Button variant="pro" className="mt-4 w-full" loading={buying} onClick={() => buy(plan)}>
            {pro.has_access ? `Продлить за ${selected.stars}` : `Подключить за ${selected.stars}`}
            <Star className="h-4 w-4 fill-current" />
          </Button>
        )}
        {pro.trial_available && (
          <Button
            variant="ghost"
            className="mt-2 w-full"
            icon={Gift}
            disabled={buying}
            onClick={trial}
          >
            Попробовать {pro.trial_days} дн. бесплатно
          </Button>
        )}
        <div className="mt-3">
          <ErrorNote>{error}</ErrorNote>
        </div>
      </div>
    </section>
  );
}

function ReferralCard() {
  const { toast } = useApp();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getReferrals()
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <ErrorNote>{error}</ErrorNote>;
  if (!data) return <Skeleton className="h-56 !rounded-[22px]" />;

  async function copy() {
    if (await copyText(data.link)) {
      haptic.success();
      toast("Ссылка скопирована");
    }
  }

  return (
    <section className="rounded-[22px] bg-surface p-5">
      <div className="flex items-center gap-3">
        <span className="grid h-11 w-11 place-items-center rounded-xl bg-go/15 text-go">
          <Gift className="h-6 w-6" />
        </span>
        <div>
          <h2 className="font-display text-[18px] font-semibold">Пригласите друга</h2>
          <p className="text-[13px] leading-snug text-muted">
            Когда друг оформит Pro, вы оба получите +{data.bonus_days} дн. Pro
          </p>
        </div>
      </div>

      <button
        type="button"
        onClick={copy}
        className="mt-4 flex w-full items-center gap-2 rounded-tile bg-raised/60 px-3.5 py-3 text-left"
      >
        <span className="min-w-0 flex-1 truncate text-[14px] font-medium text-sky">
          {data.link.replace("https://", "")}
        </span>
        <Copy className="h-4 w-4 shrink-0 text-muted" aria-label="Скопировать" />
      </button>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <Button variant="secondary" icon={Copy} onClick={copy}>
          Копировать
        </Button>
        <Button
          icon={Share2}
          onClick={() =>
            shareLink(
              data.link,
              "Автопилот отвечает клиентам в Telegram, пока я занят, и делает рассылки. Попробуй:",
            )
          }
        >
          Поделиться
        </Button>
      </div>

      <dl className="mt-5 grid grid-cols-3 divide-x divide-line/60 text-center">
        {[
          [data.invited_count, "приглашено"],
          [data.paid_count, "оформили Pro"],
          [data.days_earned, "дней получено"],
        ].map(([value, label]) => (
          <motion.div key={label} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <dt className="sr-only">{label}</dt>
            <dd className="font-display text-[22px] font-semibold">{value}</dd>
            <p className="text-xs text-muted">{label}</p>
          </motion.div>
        ))}
      </dl>
    </section>
  );
}

export default function ProfilePage() {
  const { isAdmin } = useApp();
  const navigate = useNavigate();

  return (
    <div className="space-y-4 p-4">
      <PageTitle title="Профиль" />
      <ProCard />
      <TeamCard />
      <DigestToggle />
      <ReferralCard />
      <HelpCard />
      {isAdmin && (
        <ListGroup title="Администрирование">
          <ListRow
            icon={BarChart3}
            title="Статистика и цены"
            subtitle="Пользователи, рассылки, стоимость Pro"
            chevron
            onClick={() => navigate("/admin/stats")}
          />
          <ListRow
            icon={Globe}
            title="Прокси"
            subtitle="Для отправки кодов входа"
            chevron
            onClick={() => navigate("/admin/proxies")}
          />
        </ListGroup>
      )}
    </div>
  );
}
