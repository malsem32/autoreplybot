import { useState } from "react";
import { api } from "../api/client.js";
import QrLogin from "../components/QrLogin.jsx";
import Button from "../components/ui/Button.jsx";
import Card from "../components/ui/Card.jsx";
import { Input, Label } from "../components/ui/Input.jsx";

const STEP = { PHONE: "phone", CODE: "code", PASSWORD: "password" };
const MODE = { CODE: "code", QR: "qr" };

function AccountCard({ account, isActive, onSelect }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full text-left ${isActive ? "" : "opacity-70 hover:opacity-100"}`}
    >
      <Card className={isActive ? "border-blue-500" : ""}>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">
              {account.first_name || "Без имени"}
              {account.username ? ` · @${account.username}` : ""}
            </p>
            <p className="text-sm text-slate-400">{account.phone || "номер скрыт"}</p>
          </div>
          {isActive && (
            <span className="text-xs px-2 py-1 rounded-full bg-blue-500/15 text-blue-400 font-medium">
              Активен
            </span>
          )}
        </div>
      </Card>
    </button>
  );
}

function AddAccountForm({ onAdded }) {
  const [mode, setMode] = useState(MODE.CODE);
  const [step, setStep] = useState(STEP.PHONE);
  const [phone, setPhone] = useState("");
  const [phoneCodeHash, setPhoneCodeHash] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSendCode(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { phone_code_hash } = await api.sendCode(phone);
      setPhoneCodeHash(phone_code_hash);
      setStep(STEP.CODE);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSignIn(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const acc = await api.signIn(phone, phoneCodeHash, code);
      onAdded(acc);
    } catch (err) {
      if (err.message.includes("2fa_required")) {
        setStep(STEP.PASSWORD);
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleCheckPassword(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const acc = await api.checkPassword(phone, password);
      onAdded(acc);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="space-y-4">
      <div className="flex rounded-xl bg-slate-800 p-1">
        <button
          type="button"
          onClick={() => setMode(MODE.CODE)}
          className={`flex-1 py-1.5 rounded-lg text-sm font-medium ${mode === MODE.CODE ? "bg-slate-950" : "text-slate-400"}`}
        >
          По коду
        </button>
        <button
          type="button"
          onClick={() => setMode(MODE.QR)}
          className={`flex-1 py-1.5 rounded-lg text-sm font-medium ${mode === MODE.QR ? "bg-slate-950" : "text-slate-400"}`}
        >
          По QR
        </button>
      </div>

      {mode === MODE.QR && <QrLogin onSuccess={onAdded} />}

      {mode === MODE.CODE && step === STEP.PHONE && (
        <form onSubmit={handleSendCode} className="space-y-3">
          <div>
            <Label htmlFor="phone">Номер телефона</Label>
            <Input
              id="phone"
              placeholder="+79991234567"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Отправка…" : "Получить код"}
          </Button>
        </form>
      )}

      {mode === MODE.CODE && step === STEP.CODE && (
        <form onSubmit={handleSignIn} className="space-y-3">
          <div>
            <Label htmlFor="code">Код из Telegram</Label>
            <Input
              id="code"
              placeholder="12345"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
              autoFocus
            />
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Проверка…" : "Подтвердить"}
          </Button>
        </form>
      )}

      {mode === MODE.CODE && step === STEP.PASSWORD && (
        <form onSubmit={handleCheckPassword} className="space-y-3">
          <div>
            <Label htmlFor="password">Пароль двухфакторной защиты</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoFocus
            />
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Вход…" : "Войти"}
          </Button>
        </form>
      )}

      {error && <p className="text-red-400 text-sm">{error}</p>}
    </Card>
  );
}

export default function AccountsPage({ accounts, activeAccountId, onSelect, onAdded }) {
  const [showAddForm, setShowAddForm] = useState(accounts.length === 0);

  function handleAdded(acc) {
    onAdded(acc);
    setShowAddForm(false);
  }

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-lg font-semibold">Аккаунты</h1>

      {accounts.length > 0 && (
        <div className="space-y-2">
          {accounts.map((acc) => (
            <AccountCard
              key={acc.id}
              account={acc}
              isActive={acc.id === activeAccountId}
              onSelect={() => onSelect(acc.id)}
            />
          ))}
        </div>
      )}

      {showAddForm ? (
        <AddAccountForm onAdded={handleAdded} />
      ) : (
        <Button variant="secondary" className="w-full" onClick={() => setShowAddForm(true)}>
          + Добавить аккаунт
        </Button>
      )}
    </div>
  );
}
