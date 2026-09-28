import { motion } from "framer-motion";
import { Check, Crown, Star } from "lucide-react";
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

/** Buys Pro with Telegram Stars via an invoice opened inside Telegram. */
export function useBuyPro() {
  const { refreshPro, toast } = useApp();
  const [buying, setBuying] = useState(false);
  const [error, setError] = useState("");

  async function buy() {
    setError("");
    setBuying(true);
    try {
      const { invoice_link: link } = await api.createProInvoice();
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

  return { buy, buying, error };
}

export function ProFeatures({ features }) {
  return (
    <ul className="space-y-2.5">
      {features.map((f, i) => (
        <motion.li
          key={f}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.05 * i }}
          className="flex items-start gap-3 text-[15px]"
        >
          <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-warn/20 text-warn">
            <Check className="h-3.5 w-3.5" strokeWidth={3} />
          </span>
          {f}
        </motion.li>
      ))}
    </ul>
  );
}

export default function PaywallSheet() {
  const { paywall, closePaywall, pro, refreshPro } = useApp();
  const { buy, buying, error } = useBuyPro();

  useEffect(() => {
    if (paywall.open && !pro) refreshPro();
  }, [paywall.open, pro, refreshPro]);

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
          <Button
            variant="pro"
            className="w-full"
            loading={buying}
            onClick={async () => (await buy()) && closePaywall()}
          >
            <Star className="h-4 w-4 fill-current" />
            {pro ? `Подключить за ${pro.stars_price} Stars` : "Подключить"}
          </Button>
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
                  ? `${pro.duration_days} дней за ${pro.stars_price} ⭐️. Продление добавляет дни к текущему сроку.`
                  : "Загрузка условий…"}
            </p>
          </div>
        </div>
        {pro && <ProFeatures features={pro.features} />}
        <ErrorNote>{error}</ErrorNote>
        <p className="text-center text-xs text-faint">
          Оплата в Telegram Stars. Купить можно и в чате с ботом командой /pro.
        </p>
      </div>
    </Sheet>
  );
}
