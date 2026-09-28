import { motion } from "framer-motion";
import { Check, Crown, Gift, Star } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../../api/client.js";
import { haptic, openInvoice } from "../../lib/telegram.js";
import { useApp } from "../../state/AppContext.jsx";
import Button from "../ui/Button.jsx";
import { ErrorNote } from "../ui/Feedback.jsx";
import Sheet from "../ui/Sheet.jsx";

export function formatDate(iso) {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** Buys Pro with Telegram Stars via an invoice opened inside Telegram, or
 * starts the one-time free trial. */
export function useBuyPro() {
  const { refreshPro, toast } = useApp();
  const [buying, setBuying] = useState(false);
  const [error, setError] = useState("");

  async function buy(plan = "month") {
    setError("");
    setBuying(true);
    try {
      const { invoice_link: link } = await api.createProInvoice(plan);
      const status = await openInvoice(link);
      if (status === "paid") {
        haptic.success();
        // The bot activates Pro on successful_payment; give it a moment.
        await new Promise((r) => setTimeout(r, 1200));
        await refreshPro();
        toast("Pro активирован — спасибо!");
        return true;
      }
      if (status === "failed") setError("Оплата не прошла. Попробуйте ещё раз");
    } catch (err) {
      setError(err.message);
    } finally {
      setBuying(false);
    }
    return false;
  }

  async function trial() {
    setError("");
    setBuying(true);
    try {
      await api.startTrial();
      haptic.success();
      await refreshPro();
      toast("Пробный Pro включён");
      return true;
    } catch (err) {
      setError(err.message);
    } finally {
      setBuying(false);
    }
    return false;
  }

  return { buy, trial, buying, error };
}

export function ProFeatures({ groups }) {
  return (
    <div className="space-y-4">
      {groups.map((group, g) => (
        <section key={group.title}>
          <h3 className="mb-2 text-[13px] font-medium text-muted">{group.title}</h3>
          <ul className="space-y-2">
            {group.items.map((item, i) => (
              <motion.li
                key={item}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.03 * (g * 5 + i) }}
                className="flex items-start gap-3 text-[15px] leading-snug"
              >
                <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-warn/20 text-warn">
                  <Check className="h-3.5 w-3.5" strokeWidth={3} />
                </span>
                {item}
              </motion.li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

/** Plan cards: month / quarter / year, the longest one pre-selected. */
export function PlanPicker({ plans, value, onChange }) {
  return (
    <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Срок подписки">
      {plans.map((plan) => {
        const active = plan.id === value;
        return (
          <button
            key={plan.id}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => {
              haptic.select();
              onChange(plan.id);
            }}
            className={`relative rounded-tile border-2 px-2 pb-2.5 pt-3.5 text-center transition-colors ${
              active ? "border-warn bg-warn/10" : "border-line bg-raised/40"
            }`}
          >
            {plan.discount_percent > 0 && (
              <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-go px-2 py-0.5 text-[11px] font-bold text-onsky">
                −{plan.discount_percent}%
              </span>
            )}
            <span className="block text-[13px] font-semibold text-muted">{plan.title}</span>
            <span className="mt-1 flex items-center justify-center gap-1 font-display text-[18px] font-semibold">
              {plan.stars}
              <Star className="h-3.5 w-3.5 fill-warn text-warn" aria-label="Stars" />
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function defaultPlan(pro) {
  const plans = pro?.plans || [];
  return (plans.find((p) => p.id === "year") || plans[plans.length - 1] || { id: "month" }).id;
}

export default function PaywallSheet() {
  const { paywall, closePaywall, pro, refreshPro } = useApp();
  const { buy, trial, buying, error } = useBuyPro();
  const [plan, setPlan] = useState("year");

  useEffect(() => {
    if (paywall.open && !pro) refreshPro();
  }, [paywall.open, pro, refreshPro]);

  useEffect(() => {
    if (pro) setPlan(defaultPlan(pro));
  }, [pro]);

  const selected = pro?.plans?.find((p) => p.id === plan);

  return (
    <Sheet
      open={paywall.open}
      onClose={closePaywall}
      title="Автопилот Pro"
      footer={
        pro?.has_access ? (
          <Button className="w-full" variant="secondary" onClick={closePaywall}>
            Готово
          </Button>
        ) : (
          <div className="space-y-2">
            <Button
              variant="pro"
              className="w-full"
              loading={buying}
              onClick={async () => (await buy(plan)) && closePaywall()}
            >
              <Star className="h-4 w-4 fill-current" />
              {selected ? `Подключить за ${selected.stars} Stars` : "Подключить"}
            </Button>
            {pro?.trial_available && (
              <Button
                variant="ghost"
                className="w-full"
                icon={Gift}
                disabled={buying}
                onClick={async () => (await trial()) && closePaywall()}
              >
                Попробовать {pro.trial_days} дн. бесплатно
              </Button>
            )}
          </div>
        )
      }
    >
      <div className="space-y-5 pt-1">
        <div className="flex items-center gap-4 rounded-[20px] bg-gradient-to-br from-warn/25 to-warn/5 p-4">
          <span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-warn text-[#2A1A00] shadow-lg">
            <Crown className="h-7 w-7" />
          </span>
          <div>
            {paywall.reason && <p className="text-[15px] font-semibold">{paywall.reason}</p>}
            <p className="text-[13px] leading-snug text-muted">
              {pro?.has_access
                ? pro.is_admin
                  ? "У вас бессрочный доступ администратора."
                  : `Pro активен до ${formatDate(pro.expires_at)}.`
                : pro
                  ? "Автопилот, который работает умнее. Продление добавляет дни к текущему сроку."
                  : "Загрузка условий…"}
            </p>
          </div>
        </div>
        {pro && !pro.has_access && pro.plans?.length > 0 && (
          <PlanPicker plans={pro.plans} value={plan} onChange={setPlan} />
        )}
        {pro && <ProFeatures groups={pro.feature_groups} />}
        <ErrorNote>{error}</ErrorNote>
        <p className="text-center text-xs text-faint">
          Оплата в Telegram Stars. Купить можно и в чате с ботом командой /pro.
        </p>
      </div>
    </Sheet>
  );
}
