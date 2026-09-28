import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  Eye,
  EyeOff,
  KeyRound,
  MessageSquareText,
  Phone,
  Smartphone,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client.js";
import { haptic } from "../../lib/telegram.js";
import Button from "../ui/Button.jsx";
import { ErrorNote } from "../ui/Feedback.jsx";
import { Field, Input } from "../ui/Input.jsx";

const STEP = { PHONE: "phone", CODE: "code", PASSWORD: "password" };
const CODE_LENGTH = 5;

/** Where Telegram delivered the code — the #1 source of "the code never
 * came": by default it goes to the Telegram app itself, not SMS. */
const DELIVERY = {
  app: {
    icon: MessageSquareText,
    title: "Код отправлен в Telegram",
    text: "Сверните мини-приложение и откройте чат «Telegram» с синей галочкой — код там. Затем вернитесь сюда.",
  },
  sms: {
    icon: Smartphone,
    title: "Код отправлен по SMS",
    text: "Проверьте сообщения на телефоне.",
  },
  call: { icon: Phone, title: "Вам позвонят", text: "Робот продиктует код." },
  flash_call: {
    icon: Phone,
    title: "Сейчас будет звонок",
    text: "Код — последние цифры номера, с которого звонят.",
  },
  missed_call: {
    icon: Phone,
    title: "Сейчас будет звонок",
    text: "Код — последние цифры номера, с которого звонят.",
  },
  fragment_sms: {
    icon: Smartphone,
    title: "Код отправлен в Fragment",
    text: "Откройте fragment.com.",
  },
  email_code: {
    icon: MessageSquareText,
    title: "Код отправлен на e-mail",
    text: "Проверьте почту.",
  },
  firebase_sms: { icon: Smartphone, title: "Код отправлен по SMS", text: "Проверьте сообщения." },
};

const NEXT_LABEL = {
  sms: "Отправить по SMS",
  call: "Позвонить мне",
  flash_call: "Позвонить мне",
  missed_call: "Позвонить мне",
  fragment_sms: "Отправить в Fragment",
};

function formatPhone(digits) {
  if (!digits) return "";
  return `+${digits}`;
}

function CodeCells({ value, onChange, onComplete, disabled }) {
  const inputRef = useRef(null);
  useEffect(() => inputRef.current?.focus(), []);

  return (
    <div className="relative" onClick={() => inputRef.current?.focus()}>
      <input
        ref={inputRef}
        value={value}
        disabled={disabled}
        inputMode="numeric"
        autoComplete="one-time-code"
        aria-label="Код из Telegram"
        maxLength={8}
        onChange={(e) => {
          const next = e.target.value.replace(/\D/g, "").slice(0, 8);
          onChange(next);
          if (next.length === CODE_LENGTH) onComplete(next);
        }}
        className="absolute inset-0 h-full w-full cursor-text opacity-0"
      />
      <div className="flex justify-center gap-2" aria-hidden>
        {Array.from({ length: Math.max(CODE_LENGTH, value.length) }).map((_, i) => {
          const char = value[i];
          const focused = i === value.length;
          return (
            <motion.div
              key={i}
              animate={char ? { scale: [1, 1.08, 1] } : { scale: 1 }}
              transition={{ duration: 0.18 }}
              className={`grid h-14 w-12 place-items-center rounded-tile border-2 font-display text-2xl font-semibold transition-colors ${
                char
                  ? "border-sky bg-sky/10"
                  : focused
                    ? "border-sky/60 bg-raised/60"
                    : "border-line bg-raised/40"
              }`}
            >
              {char || ""}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

function ResendTimer({ seconds, nextType, onResend, loading }) {
  const [left, setLeft] = useState(seconds || 0);
  useEffect(() => {
    setLeft(seconds || 0);
    if (!seconds) return undefined;
    const id = setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [seconds, nextType]);

  if (!nextType || !NEXT_LABEL[nextType]) return null;
  if (left > 0) {
    return (
      <p className="text-center text-[13px] text-muted">
        {NEXT_LABEL[nextType]} можно через {left} сек.
      </p>
    );
  }
  return (
    <div className="flex justify-center">
      <Button variant="ghost" size="sm" loading={loading} onClick={onResend}>
        Не пришёл код? {NEXT_LABEL[nextType]}
      </Button>
    </div>
  );
}

export default function CodeLogin({ onSuccess }) {
  const [step, setStep] = useState(STEP.PHONE);
  const [phoneInput, setPhoneInput] = useState("+");
  const [sent, setSent] = useState(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [hint, setHint] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  async function run(fn) {
    setError("");
    setLoading(true);
    try {
      await fn();
    } catch (err) {
      haptic.error();
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleResult(result) {
    if (result.status === "password_required") {
      setHint(result.password_hint || "");
      setStep(STEP.PASSWORD);
      return;
    }
    haptic.success();
    onSuccess(result.account);
  }

  const sendCode = (e) => {
    e?.preventDefault();
    return run(async () => {
      const res = await api.sendCode(phoneInput);
      setSent(res);
      setCode("");
      setStep(STEP.CODE);
    });
  };

  const signIn = (value = code) =>
    run(async () => {
      try {
        handleResult(await api.signIn(sent.phone, sent.phone_code_hash, value));
      } catch (err) {
        setCode("");
        throw err;
      }
    });

  const checkPassword = (e) => {
    e.preventDefault();
    return run(async () => handleResult(await api.checkPassword(sent.phone, password)));
  };

  async function resend() {
    setError("");
    setResending(true);
    try {
      setSent(await api.resendCode(sent.phone, sent.phone_code_hash));
      setCode("");
      haptic.success();
    } catch (err) {
      setError(err.message);
    } finally {
      setResending(false);
    }
  }

  function changeNumber() {
    if (sent) api.cancelLogin(sent.phone).catch(() => {});
    setSent(null);
    setCode("");
    setPassword("");
    setError("");
    setStep(STEP.PHONE);
  }

  const delivery = DELIVERY[sent?.code_type] || DELIVERY.app;

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={step}
        initial={{ opacity: 0, x: 24 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -24 }}
        transition={{ duration: 0.2 }}
        className="space-y-4"
      >
        {step === STEP.PHONE && (
          <form onSubmit={sendCode} className="space-y-4">
            <Field label="Номер телефона" htmlFor="phone" hint="в международном формате">
              <Input
                id="phone"
                type="tel"
                inputMode="tel"
                autoComplete="tel"
                placeholder="+7 999 123-45-67"
                value={phoneInput}
                onChange={(e) => setPhoneInput(e.target.value.replace(/[^\d+\s()-]/g, ""))}
                autoFocus
                className="font-display text-lg tracking-wide"
              />
            </Field>
            <ErrorNote>{error}</ErrorNote>
            <Button
              type="submit"
              className="w-full"
              loading={loading}
              disabled={phoneInput.replace(/\D/g, "").length < 7}
            >
              Получить код
            </Button>
            <p className="text-center text-[12px] leading-relaxed text-faint">
              Сессия хранится на сервере в зашифрованном виде. Отключить её можно в любой момент в
              Telegram → Настройки → Устройства.
            </p>
          </form>
        )}

        {step === STEP.CODE && sent && (
          <div className="space-y-5">
            <div className="flex items-start gap-3 rounded-tile bg-sky/10 p-3.5">
              <delivery.icon className="mt-0.5 h-5 w-5 shrink-0 text-sky" aria-hidden />
              <div>
                <p className="text-[15px] font-semibold">{delivery.title}</p>
                <p className="mt-0.5 text-[13px] leading-snug text-muted">{delivery.text}</p>
                <p className="mt-1 text-[13px] text-muted">
                  Номер: <span className="font-medium text-ink">{formatPhone(sent.phone)}</span>
                </p>
              </div>
            </div>

            <CodeCells
              key={sent.phone_code_hash}
              value={code}
              onChange={setCode}
              onComplete={signIn}
              disabled={loading}
            />
            <ErrorNote>{error}</ErrorNote>

            <Button
              className="w-full"
              loading={loading}
              disabled={code.length < 4}
              onClick={() => signIn()}
            >
              Войти
            </Button>

            <ResendTimer
              seconds={sent.timeout}
              nextType={sent.next_type}
              onResend={resend}
              loading={resending}
            />
            <p className="text-center text-[12px] leading-relaxed text-faint">
              Не пересылайте код никому — даже себе в «Избранное». Telegram заблокирует вход, если
              увидит код в сообщении.
            </p>
            <div className="flex justify-center">
              <Button variant="ghost" size="sm" icon={ArrowLeft} onClick={changeNumber}>
                Изменить номер
              </Button>
            </div>
          </div>
        )}

        {step === STEP.PASSWORD && (
          <form onSubmit={checkPassword} className="space-y-4">
            <div className="flex items-start gap-3 rounded-tile bg-warn/10 p-3.5">
              <KeyRound className="mt-0.5 h-5 w-5 shrink-0 text-warn" aria-hidden />
              <div>
                <p className="text-[15px] font-semibold">Включена двухэтапная проверка</p>
                <p className="mt-0.5 text-[13px] leading-snug text-muted">
                  Введите облачный пароль, который вы задали в Telegram.
                  {hint && (
                    <>
                      {" "}
                      Подсказка: <span className="font-medium text-ink">{hint}</span>
                    </>
                  )}
                </p>
              </div>
            </div>
            <Field label="Облачный пароль" htmlFor="password">
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoFocus
                  className="pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-2 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-lg text-muted"
                  aria-label={showPassword ? "Скрыть пароль" : "Показать пароль"}
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </Field>
            <ErrorNote>{error}</ErrorNote>
            <Button type="submit" className="w-full" loading={loading} disabled={!password}>
              Войти
            </Button>
            <div className="flex justify-center">
              <Button variant="ghost" size="sm" icon={ArrowLeft} onClick={changeNumber}>
                Начать заново
              </Button>
            </div>
          </form>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
