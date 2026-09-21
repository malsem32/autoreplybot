import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import Badge from "../components/ui/Badge.jsx";
import Button from "../components/ui/Button.jsx";
import Card from "../components/ui/Card.jsx";
import { Input, Label, Select } from "../components/ui/Input.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";

const emptyForm = {
  protocol: "socks5",
  host: "",
  port: "",
  username: "",
  password: "",
};

function statusColor(status) {
  if (status === "alive") return "text-emerald-400";
  if (status === "dead") return "text-red-400";
  return "text-slate-500";
}

function statusLabel(status) {
  if (status === "alive") return "Живой";
  if (status === "dead") return "Мёртвый";
  return "Не проверялся";
}

function ProxyForm({ onSubmit, onCancel }) {
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await onSubmit({
        protocol: form.protocol,
        host: form.host,
        port: Number(form.port),
        username: form.username || null,
        password: form.password || null,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label>Протокол</Label>
          <Select
            value={form.protocol}
            onChange={(e) => setForm({ ...form, protocol: e.target.value })}
          >
            <option value="socks5">SOCKS5</option>
            <option value="http">HTTP</option>
          </Select>
        </div>
        <div>
          <Label>Порт</Label>
          <Input
            type="number"
            value={form.port}
            onChange={(e) => setForm({ ...form, port: e.target.value })}
            required
          />
        </div>
      </div>
      <div>
        <Label>Хост</Label>
        <Input
          placeholder="pool.proxy.market"
          value={form.host}
          onChange={(e) => setForm({ ...form, host: e.target.value })}
          required
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label>Логин (необязательно)</Label>
          <Input
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
          />
        </div>
        <div>
          <Label>Пароль (необязательно)</Label>
          <Input
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </div>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <div className="flex gap-2">
        <Button type="submit" disabled={saving} className="flex-1">
          {saving ? "Сохранение…" : "Добавить"}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel}>
          Отмена
        </Button>
      </div>
    </form>
  );
}

function ProxyCard({ proxy, onChanged, onDeleted }) {
  const [error, setError] = useState("");

  async function handleToggleActive() {
    setError("");
    try {
      const updated = await api.updateProxy(proxy.id, { is_active: !proxy.is_active });
      onChanged(updated);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete() {
    setError("");
    try {
      await api.deleteProxy(proxy.id);
      onDeleted(proxy.id);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <Card className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="font-medium font-mono text-sm">
            {proxy.protocol}://{proxy.host}:{proxy.port}
          </p>
          <p className="text-xs text-slate-500 mt-0.5">
            {proxy.username ? `логин: ${proxy.username}` : "без авторизации"}
          </p>
        </div>
        <Badge status={proxy.is_active ? "active" : "paused"} />
      </div>

      <div className="flex items-center gap-2 text-xs">
        <span className={`font-medium ${statusColor(proxy.last_status)}`}>
          ● {statusLabel(proxy.last_status)}
        </span>
        {proxy.last_latency_ms != null && (
          <span className="text-slate-500">{proxy.last_latency_ms} мс</span>
        )}
        {proxy.last_checked_at && (
          <span className="text-slate-600">
            {new Date(proxy.last_checked_at).toLocaleString("ru-RU")}
          </span>
        )}
      </div>

      {error && <p className="text-red-400 text-xs">{error}</p>}

      <div className="flex gap-2 pt-1">
        <Button variant="secondary" onClick={handleToggleActive}>
          {proxy.is_active ? "Отключить" : "Включить"}
        </Button>
        <Button variant="danger" onClick={handleDelete}>
          Удалить
        </Button>
      </div>
    </Card>
  );
}

export default function ProxiesPage() {
  const [proxies, setProxies] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .listProxies()
      .then(setProxies)
      .catch((err) => setError(err.message));
  }, []);

  async function handleCreate(payload) {
    const proxy = await api.createProxy(payload);
    setProxies((prev) => [...prev, proxy]);
    setShowForm(false);
  }

  function handleChanged(updated) {
    setProxies((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  }

  function handleDeleted(id) {
    setProxies((prev) => prev.filter((p) => p.id !== id));
  }

  async function handleCheckAll() {
    setError("");
    setChecking(true);
    try {
      const updated = await api.checkAllProxies();
      setProxies(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="p-4 space-y-4">
      <PageHeader
        icon="🌐"
        title="Прокси"
        action={
          <div className="flex gap-2">
            {proxies.length > 0 && (
              <Button variant="secondary" onClick={handleCheckAll} disabled={checking}>
                {checking ? "Проверка…" : "Проверить все"}
              </Button>
            )}
            {!showForm && <Button onClick={() => setShowForm(true)}>+ Прокси</Button>}
          </div>
        }
      />

      <p className="text-xs text-slate-500">
        Используются только для запроса кода при подключении аккаунта — снижает риск, что
        Telegram сочтёт IP сервера подозрительным и заблокирует отправку SMS.
      </p>

      {showForm && (
        <Card>
          <ProxyForm onSubmit={handleCreate} onCancel={() => setShowForm(false)} />
        </Card>
      )}

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <div className="space-y-3">
        {proxies.map((p) => (
          <ProxyCard key={p.id} proxy={p} onChanged={handleChanged} onDeleted={handleDeleted} />
        ))}
        {proxies.length === 0 && !showForm && (
          <p className="text-sm text-slate-500">Прокси пока не добавлены.</p>
        )}
      </div>
    </div>
  );
}
