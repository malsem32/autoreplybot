import { AnimatePresence, motion } from "framer-motion";
import { Globe, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import PageTitle from "../components/PageTitle.jsx";
import Button from "../components/ui/Button.jsx";
import { EmptyState, ErrorNote, Pill, Skeleton } from "../components/ui/Feedback.jsx";
import { Field, Input } from "../components/ui/Input.jsx";
import Segmented from "../components/ui/Segmented.jsx";
import Sheet from "../components/ui/Sheet.jsx";
import Switch from "../components/ui/Switch.jsx";
import useBackButton from "../hooks/useBackButton.js";
import { confirmDialog } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";

const emptyForm = { protocol: "socks5", host: "", port: "", username: "", password: "" };

const LIVENESS = {
  alive: { tone: "go", label: "отвечает" },
  dead: { tone: "danger", label: "не отвечает" },
};

function ProxySheet({ open, onClose, onCreate }) {
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm(emptyForm);
      setError("");
    }
  }, [open]);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function save() {
    setError("");
    setSaving(true);
    try {
      await onCreate({
        protocol: form.protocol,
        host: form.host.trim(),
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
    <Sheet
      open={open}
      onClose={onClose}
      title="Новый прокси"
      footer={
        <Button
          className="w-full"
          loading={saving}
          disabled={!form.host || !form.port}
          onClick={save}
        >
          Добавить прокси
        </Button>
      }
    >
      <div className="space-y-4 pt-1">
        <Segmented
          value={form.protocol}
          onChange={(protocol) => setForm({ ...form, protocol })}
          options={[
            { value: "socks5", label: "SOCKS5" },
            { value: "http", label: "HTTP" },
          ]}
        />
        <div className="grid grid-cols-[1fr_7rem] gap-3">
          <Field label="Хост" htmlFor="px-host">
            <Input
              id="px-host"
              value={form.host}
              onChange={set("host")}
              placeholder="proxy.example.com"
              autoCapitalize="off"
            />
          </Field>
          <Field label="Порт" htmlFor="px-port">
            <Input
              id="px-port"
              type="number"
              inputMode="numeric"
              value={form.port}
              onChange={set("port")}
            />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Логин" hint="если нужен" htmlFor="px-user">
            <Input
              id="px-user"
              value={form.username}
              onChange={set("username")}
              autoCapitalize="off"
            />
          </Field>
          <Field label="Пароль" htmlFor="px-pass">
            <Input id="px-pass" type="password" value={form.password} onChange={set("password")} />
          </Field>
        </div>
        <ErrorNote>{error}</ErrorNote>
      </div>
    </Sheet>
  );
}

export default function ProxiesPage() {
  useBackButton("/profile");
  const { toast } = useApp();
  const [proxies, setProxies] = useState(null);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    api
      .listProxies()
      .then(setProxies)
      .catch((err) => {
        setError(err.message);
        setProxies([]);
      });
  }, []);

  const replace = (p) => setProxies((prev) => prev.map((x) => (x.id === p.id ? p : x)));

  async function create(payload) {
    const proxy = await api.createProxy(payload);
    setProxies((prev) => [...prev, proxy]);
    setAdding(false);
    toast("Прокси добавлен");
  }

  async function toggle(proxy, isActive) {
    try {
      replace(await api.updateProxy(proxy.id, { is_active: isActive }));
    } catch (err) {
      toast(err.message, "danger");
    }
  }

  async function remove(proxy) {
    if (!(await confirmDialog(`Удалить прокси ${proxy.host}:${proxy.port}?`))) return;
    try {
      await api.deleteProxy(proxy.id);
      setProxies((prev) => prev.filter((p) => p.id !== proxy.id));
    } catch (err) {
      toast(err.message, "danger");
    }
  }

  async function checkAll() {
    setChecking(true);
    try {
      setProxies(await api.checkAllProxies());
      toast("Проверка завершена");
    } catch (err) {
      toast(err.message, "danger");
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="space-y-4 p-4">
      <PageTitle
        title="Прокси"
        subtitle="Через них уходят запросы кода входа — Telegram реже задерживает SMS"
        action={
          proxies?.length > 0 && (
            <Button size="sm" icon={Plus} onClick={() => setAdding(true)}>
              Прокси
            </Button>
          )
        }
      />
      <ErrorNote>{error}</ErrorNote>
      {proxies === null ? (
        <Skeleton className="h-24" />
      ) : proxies.length === 0 ? (
        <EmptyState
          icon={Globe}
          title="Прокси не добавлены"
          text="Без прокси коды входа запрашиваются напрямую с сервера — это тоже работает."
          action={
            <Button icon={Plus} onClick={() => setAdding(true)}>
              Добавить прокси
            </Button>
          }
        />
      ) : (
        <>
          <Button
            variant="secondary"
            className="w-full"
            icon={RefreshCw}
            loading={checking}
            onClick={checkAll}
          >
            Проверить все
          </Button>
          <div className="space-y-2.5">
            <AnimatePresence initial={false}>
              {proxies.map((p) => {
                const live = LIVENESS[p.last_status];
                return (
                  <motion.div
                    key={p.id}
                    layout
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0, x: -40 }}
                    className="flex items-center gap-3 rounded-[18px] bg-surface p-4"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[15px] font-semibold">
                        {p.host}:{p.port}
                      </p>
                      <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                        <Pill tone="sky">{p.protocol.toUpperCase()}</Pill>
                        <Pill tone={live?.tone || "muted"} dot>
                          {live?.label || "не проверялся"}
                          {p.last_latency_ms != null && ` · ${p.last_latency_ms} мс`}
                        </Pill>
                      </div>
                    </div>
                    <Switch
                      checked={p.is_active}
                      onChange={(v) => toggle(p, v)}
                      label="Прокси включён"
                    />
                    <button
                      type="button"
                      onClick={() => remove(p)}
                      className="grid h-9 w-9 place-items-center rounded-lg text-faint hover:text-danger"
                      aria-label="Удалить прокси"
                    >
                      <Trash2 className="h-[18px] w-[18px]" />
                    </button>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        </>
      )}
      <ProxySheet open={adding} onClose={() => setAdding(false)} onCreate={create} />
    </div>
  );
}
