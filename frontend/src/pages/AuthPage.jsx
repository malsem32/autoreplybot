import { useState } from "react";
import { api } from "../api/client.js";

const STEP = { PHONE: "phone", CODE: "code", PASSWORD: "password", DONE: "done" };

export default function AuthPage({ onConnected }) {
  const [step, setStep] = useState(STEP.PHONE);
  const [phone, setPhone] = useState("");
  const [phoneCodeHash, setPhoneCodeHash] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [account, setAccount] = useState(null);

  async function handleSendCode(e) {
    e.preventDefault();
    setError("");
    try {
      const { phone_code_hash } = await api.sendCode(phone);
      setPhoneCodeHash(phone_code_hash);
      setStep(STEP.CODE);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSignIn(e) {
    e.preventDefault();
    setError("");
    try {
      const acc = await api.signIn(phone, phoneCodeHash, code);
      setAccount(acc);
      onConnected?.(acc);
      setStep(STEP.DONE);
    } catch (err) {
      if (err.message.includes("2fa_required")) {
        setStep(STEP.PASSWORD);
      } else {
        setError(err.message);
      }
    }
  }

  async function handleCheckPassword(e) {
    e.preventDefault();
    setError("");
    try {
      const acc = await api.checkPassword(phone, password);
      setAccount(acc);
      onConnected?.(acc);
      setStep(STEP.DONE);
    } catch (err) {
      setError(err.message);
    }
  }

  if (step === STEP.DONE && account) {
    return (
      <div className="p-4">
        <h1 className="text-lg font-semibold mb-2">Аккаунт подключён</h1>
        <p className="text-slate-400">
          {account.first_name} {account.username ? `(@${account.username})` : ""} — {account.phone}
        </p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-lg font-semibold">Подключить аккаунт</h1>

      {step === STEP.PHONE && (
        <form onSubmit={handleSendCode} className="space-y-3">
          <input
            className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2"
            placeholder="+79991234567"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            required
          />
          <button className="w-full rounded-lg bg-blue-600 py-2 font-medium" type="submit">
            Получить код
          </button>
        </form>
      )}

      {step === STEP.CODE && (
        <form onSubmit={handleSignIn} className="space-y-3">
          <input
            className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2"
            placeholder="Код из Telegram"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
          />
          <button className="w-full rounded-lg bg-blue-600 py-2 font-medium" type="submit">
            Подтвердить
          </button>
        </form>
      )}

      {step === STEP.PASSWORD && (
        <form onSubmit={handleCheckPassword} className="space-y-3">
          <input
            className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2"
            placeholder="Пароль двухфакторной защиты"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button className="w-full rounded-lg bg-blue-600 py-2 font-medium" type="submit">
            Войти
          </button>
        </form>
      )}

      {error && <p className="text-red-400 text-sm">{error}</p>}
    </div>
  );
}
