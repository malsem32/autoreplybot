import { motion } from "framer-motion";
import { BarChart3, Copy, Crown, Gift, Globe, Share2, Star } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import PageTitle from "../components/PageTitle.jsx";
import { formatDate, ProFeatures, useBuyPro } from "../components/pro/PaywallSheet.jsx";
import Button from "../components/ui/Button.jsx";
import { ErrorNote, Skeleton } from "../components/ui/Feedback.jsx";
import { ListGroup, ListRow } from "../components/ui/List.jsx";
import { copyText, haptic, shareLink } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";

function ProCard() {
  const { pro } = useApp();
  const { buy, buying, error } = useBuyPro();

  if (!pro) return <Skeleton className="h-64 !rounded-[22px]" />;

  return (
    <section className="relative overflow-hidden rounded-[22px] bg-surface p-5">
      <div
        className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-warn/20 blur-3xl"
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
                : `${pro.duration_days} дней · ${pro.stars_price} Stars`}
            </p>
          </div>
        </div>
        <div className="mt-5">
          <ProFeatures features={pro.features} />
        </div>
        {!pro.is_admin && (
          <Button variant="pro" className="mt-5 w-full" loading={buying} onClick={buy}>
            <Star className="h-4 w-4 fill-current" />
            {pro.has_access
              ? `Продлить на ${pro.duration_days} дней`
              : `Подключить за ${pro.stars_price} Stars`}
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
      <ReferralCard />
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
