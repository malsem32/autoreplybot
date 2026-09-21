import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import PhotoPicker from "../components/PhotoPicker.jsx";
import Button from "../components/ui/Button.jsx";
import Card from "../components/ui/Card.jsx";
import { Input, Label, Select, Textarea } from "../components/ui/Input.jsx";

const emptyForm = {
  triggerType: "all",
  keywords: "",
  responseText: "",
  cooldownHours: 1,
  photo: null, // { path, previewUrl } | null
};

function RuleForm({ initial, onSubmit, onCancel, submitLabel }) {
  const [form, setForm] = useState(initial);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await onSubmit(form);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <Label>Когда отвечать</Label>
        <Select
          value={form.triggerType}
          onChange={(e) => setForm({ ...form, triggerType: e.target.value })}
        >
          <option value="all">На все сообщения</option>
          <option value="keywords">Только по ключевым словам</option>
        </Select>
      </div>

      {form.triggerType === "keywords" && (
        <div>
          <Label>Ключевые слова, через запятую</Label>
          <Input
            placeholder="цена, стоимость, купить"
            value={form.keywords}
            onChange={(e) => setForm({ ...form, keywords: e.target.value })}
          />
        </div>
      )}

      <div>
        <Label>Текст ответа</Label>
        <Textarea
          placeholder="Спасибо за сообщение! {Отвечу|Свяжусь} с вами в ближайшее время."
          value={form.responseText}
          onChange={(e) => setForm({ ...form, responseText: e.target.value })}
          required
        />
      </div>

      <div>
        <Label>Фото (необязательно)</Label>
        <PhotoPicker
          previewUrl={form.photo?.previewUrl}
          onChange={(photo) => setForm({ ...form, photo })}
        />
      </div>

      <div>
        <Label>Пауза перед повторным ответом одному человеку, часов</Label>
        <Input
          type="number"
          min="1"
          value={form.cooldownHours}
          onChange={(e) => setForm({ ...form, cooldownHours: e.target.value })}
        />
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <div className="flex gap-2">
        <Button type="submit" disabled={saving} className="flex-1">
          {saving ? "Сохранение…" : submitLabel}
        </Button>
        {onCancel && (
          <Button type="button" variant="secondary" onClick={onCancel}>
            Отмена
          </Button>
        )}
      </div>
    </form>
  );
}

function formToPayload(form) {
  return {
    is_enabled: true,
    trigger_type: form.triggerType,
    keywords:
      form.triggerType === "keywords"
        ? form.keywords
            .split(",")
            .map((k) => k.trim())
            .filter(Boolean)
        : [],
    response_text: form.responseText,
    photo_path: form.photo?.path,
    cooldown_seconds: Math.max(1, Number(form.cooldownHours)) * 3600,
  };
}

function ruleToForm(rule) {
  return {
    triggerType: rule.trigger_type,
    keywords: rule.keywords.join(", "),
    responseText: rule.response_text,
    cooldownHours: Math.round(rule.cooldown_seconds / 3600) || 1,
    photo: rule.photo_url ? { path: null, previewUrl: rule.photo_url } : null,
  };
}

function RuleCard({ rule, accountId, onChanged }) {
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");

  async function handleUpdate(form) {
    const payload = formToPayload(form);
    if (!payload.photo_path) delete payload.photo_path;
    if (!form.photo) payload.remove_photo = true;
    const updated = await api.updateRule(accountId, rule.id, payload);
    onChanged(updated);
    setEditing(false);
  }

  async function handleDelete() {
    setError("");
    try {
      await api.deleteRule(accountId, rule.id);
      onChanged(null, rule.id);
    } catch (err) {
      setError(err.message);
    }
  }

  if (editing) {
    return (
      <Card>
        <RuleForm
          initial={ruleToForm(rule)}
          submitLabel="Сохранить"
          onSubmit={handleUpdate}
          onCancel={() => setEditing(false)}
        />
      </Card>
    );
  }

  return (
    <Card className="space-y-2">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <p className="text-xs text-slate-500 mb-1">
            {rule.trigger_type === "all" ? "Все сообщения" : rule.keywords.join(", ")}
          </p>
          <p className="text-sm">{rule.response_text}</p>
        </div>
        {rule.photo_url && (
          <img
            src={rule.photo_url}
            alt=""
            className="h-14 w-14 rounded-lg object-cover border border-slate-700 shrink-0"
          />
        )}
      </div>
      <p className="text-xs text-slate-500">
        Пауза: {Math.round(rule.cooldown_seconds / 3600)} ч
      </p>
      {error && <p className="text-red-400 text-xs">{error}</p>}
      <div className="flex gap-2 pt-1">
        <Button variant="secondary" onClick={() => setEditing(true)}>
          Изменить
        </Button>
        <Button variant="danger" onClick={handleDelete}>
          Удалить
        </Button>
      </div>
    </Card>
  );
}

export default function AutoresponderPage({ accountId }) {
  const [rules, setRules] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (accountId) {
      api
        .listRules(accountId)
        .then(setRules)
        .catch((err) => setError(err.message));
    }
  }, [accountId]);

  async function handleCreate(form) {
    const rule = await api.createRule(accountId, formToPayload(form));
    setRules((prev) => [...prev, rule]);
    setShowForm(false);
  }

  function handleChanged(updated, deletedId) {
    if (deletedId) {
      setRules((prev) => prev.filter((r) => r.id !== deletedId));
    } else {
      setRules((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    }
  }

  if (!accountId) {
    return <p className="p-4 text-slate-400">Сначала подключите аккаунт на вкладке «Аккаунты».</p>;
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Автоответчик</h1>
        {!showForm && <Button onClick={() => setShowForm(true)}>+ Правило</Button>}
      </div>

      {showForm && (
        <Card>
          <RuleForm
            initial={emptyForm}
            submitLabel="Добавить"
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
          />
        </Card>
      )}

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <div className="space-y-3">
        {rules.map((rule) => (
          <RuleCard key={rule.id} rule={rule} accountId={accountId} onChanged={handleChanged} />
        ))}
        {rules.length === 0 && !showForm && (
          <p className="text-sm text-slate-500">Правил пока нет — добавьте первое.</p>
        )}
      </div>
    </div>
  );
}
