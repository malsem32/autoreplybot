import { motion } from "framer-motion";
import { KeyRound, RefreshCw } from "lucide-react";
import QRCode from "qrcode";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api/client.js";
import { haptic } from "../../lib/telegram.js";
import Button from "../ui/Button.jsx";
import { ErrorNote } from "../ui/Feedback.jsx";
import { Field, Input } from "../ui/Input.jsx";

const POLL_INTERVAL_MS = 2000;
const QR_SIZE = 216;

/** Telegram QR login: shows a `tg://login?token=…` code that the backend
 * refreshes before it expires, and polls until it's confirmed on a phone.
 * Accounts with two-step verification finish with the password. */
export default function QrLogin({ onSuccess }) {
  const canvasRef = useRef(null);
  const requestRef = useRef(null);
  const doneRef = useRef(false);
  const [phase, setPhase] = useState("loading"); // loading | scan | password | error
  const [error, setError] = useState("");
  const [expiresAt, setExpiresAt] = useState(0);
  const [now, setNow] = useState(Date.now());
  const [hint, setHint] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [attempt, setAttempt] = useState(0);

  const draw = useCallback(async (url, expiresIn) => {
    if (canvasRef.current) {
      await QRCode.toCanvas(canvasRef.current, url, {
        width: QR_SIZE,
        margin: 1,
        errorCorrectionLevel: "M",
        // Always dark-on-white: scanners need contrast whatever the theme.
        color: { dark: "#0B1633", light: "#FFFFFF" },
      });
    }
    if (expiresIn != null) setExpiresAt(Date.now() + expiresIn * 1000);
  }, []);

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer = null;
    doneRef.current = false;

    async function poll() {
      if (cancelled || !requestRef.current) return;
      try {
        const res = await api.qrPoll(requestRef.current);
        if (cancelled) return;
        if (res.status === "success") {
          doneRef.current = true;
          haptic.success();
          onSuccess(res.account);
          return;
        }
        if (res.status === "password_required") {
          setHint(res.password_hint || "");
          setPhase("password");
          return;
        }
        if (res.status === "restart") {
          setAttempt((a) => a + 1);
          return;
        }
        if (res.qr_url) await draw(res.qr_url, res.expires_in);
        timer = setTimeout(poll, POLL_INTERVAL_MS);
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setPhase("error");
        }
      }
    }

    (async () => {
      setPhase("loading");
      setError("");
      try {
        const res = await api.qrStart();
        if (cancelled) {
          api.qrCancel(res.request_id).catch(() => {});
          return;
        }
        requestRef.current = res.request_id;
        setPhase("scan");
        // wait a frame so the canvas is mounted
        requestAnimationFrame(() => draw(res.qr_url, res.expires_in));
        timer = setTimeout(poll, POLL_INTERVAL_MS);
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setPhase("error");
        }
      }
    })();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      if (requestRef.current && !doneRef.current) {
        api.qrCancel(requestRef.current).catch(() => {});
      }
      requestRef.current = null;
    };
  }, [attempt, draw, onSuccess]);

  async function submitPassword(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await api.qrPassword(requestRef.current, password);
      doneRef.current = true;
      haptic.success();
      onSuccess(res.account);
    } catch (err) {
      haptic.error();
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (phase === "password") {
    return (
      <form onSubmit={submitPassword} className="space-y-4">
        <div className="flex items-start gap-3 rounded-tile bg-warn/10 p-3.5">
          <KeyRound className="mt-0.5 h-5 w-5 shrink-0 text-warn" aria-hidden />
          <p className="text-[13px] leading-snug text-muted">
            QR-код подтверждён. Осталось ввести облачный пароль Telegram.
            {hint && (
              <>
                {" "}
                Подсказка: <span className="font-medium text-ink">{hint}</span>
              </>
            )}
          </p>
        </div>
        <Field label="Облачный пароль" htmlFor="qr-password">
          <Input
            id="qr-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
          />
        </Field>
        <ErrorNote>{error}</ErrorNote>
        <Button type="submit" className="w-full" loading={submitting} disabled={!password}>
          Войти
        </Button>
      </form>
    );
  }

  const left = Math.max(0, expiresAt - now);
  const seconds = Math.ceil(left / 1000);
  const progress = expiresAt ? Math.min(1, left / 30_000) : 1;

  return (
    <div className="flex flex-col items-center gap-4 py-1">
      <motion.div
        initial={{ scale: 0.94, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="relative rounded-[22px] bg-white p-3 shadow-[0_18px_40px_-18px_rgb(var(--sky)/0.6)]"
      >
        <canvas ref={canvasRef} width={QR_SIZE} height={QR_SIZE} className="block" />
        {phase === "loading" && (
          <div className="absolute inset-3 grid place-items-center rounded-xl bg-white">
            <RefreshCw className="h-7 w-7 animate-spin text-[#0B1633]" aria-label="Загрузка" />
          </div>
        )}
        {phase === "error" && (
          <div className="absolute inset-3 grid place-items-center rounded-xl bg-white/95">
            <Button size="sm" icon={RefreshCw} onClick={() => setAttempt((a) => a + 1)}>
              Обновить код
            </Button>
          </div>
        )}
      </motion.div>

      {phase === "scan" && expiresAt > 0 && (
        <div className="w-full max-w-[240px]">
          <div className="h-1 overflow-hidden rounded-full bg-line">
            <div
              className="h-full rounded-full bg-sky transition-[width] duration-500 ease-linear"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
          <p className="mt-1.5 text-center text-xs text-faint">
            {seconds > 3 ? `Код обновится через ${seconds} сек.` : "Обновляем код…"}
          </p>
        </div>
      )}

      <ol className="w-full space-y-2 text-[14px] leading-snug text-muted">
        {[
          "Откройте Telegram на другом устройстве, где вы уже вошли",
          "Настройки → Устройства → Подключить устройство",
          "Наведите камеру на этот код",
        ].map((text, i) => (
          <li key={text} className="flex gap-3">
            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-sky/15 text-xs font-bold text-sky">
              {i + 1}
            </span>
            <span className="pt-0.5">{text}</span>
          </li>
        ))}
      </ol>
      <ErrorNote>{error}</ErrorNote>
    </div>
  );
}
