import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import CampaignLogsModal from "../components/CampaignLogsModal.jsx";
import PhotoPicker from "../components/PhotoPicker.jsx";
import Badge from "../components/ui/Badge.jsx";
import Button from "../components/ui/Button.jsx";
import Card from "../components/ui/Card.jsx";
import { Input, Label, Select, Textarea } from "../components/ui/Input.jsx";
import PageHeader from "../components/ui/PageHeader.jsx";

const emptyForm = {
  title: "",
  textTemplate: "",
  chatIds: "",
  scheduleType: "recurring",
  intervalMinutes: 60,
  scheduledAt: "",
  photo: null,
};

function toLocalDatetimeInput(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function CampaignForm({ initial, onSubmit, onCancel, submitLabel }) {
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
        <Label>Название кампании</Label>
        <Input
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          required
        />
      </div>

      <div>
        <Label>Текст сообщения</Label>
        <Textarea
          placeholder="{Привет|Добрый день}! Есть отличное предложение…"
          value={form.textTemplate}
          onChange={(e) => setForm({ ...form, textTemplate: e.target.value })}
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
        <Label>Чаты — через запятую (ID, @юзернейм или ссылка t.me/…)</Label>
        <Input
          placeholder="-1001234567890, @my_channel, https://t.me/+AbCdEf"
          value={form.chatIds}
          onChange={(e) => setForm({ ...form, chatIds: e.target.value })}
          required
        />
      </div>

      <div>
        <Label>Расписание</Label>
        <Select
          value={form.scheduleType}
          onChange={(e) => setForm({ ...form, scheduleType: e.target.value })}
        >
          <option value="recurring">Повторять с интервалом</option>
          <option value="once">Отправить один раз в указанное время</option>
        </Select>
      </div>

      {form.scheduleType === "recurring" ? (
        <div>
          <Label>Интервал, минут</Label>
          <Input
            type="number"
            min="1"
            value={form.intervalMinutes}
            onChange={(e) => setForm({ ...form, intervalMinutes: e.target.value })}
          />
        </div>
      ) : (
        <div>
          <Label>Дата и время отправки</Label>
          <Input
            type="datetime-local"
            value={form.scheduledAt}
            onChange={(e) => setForm({ ...form, scheduledAt: e.target.value })}
            required
          />
        </div>
      )}

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
  const payload = {
    title: form.title,
    text_template: form.textTemplate,
    photo_path: form.photo?.path,
    target_chats: form.chatIds
      .split(",")
      .map((id) => id.trim())
      .filter(Boolean),
    schedule_type: form.scheduleType,
  };
  if (form.scheduleType === "recurring") {
    payload.interval_minutes = Number(form.intervalMinutes);
  } else {
    payload.scheduled_at = new Date(form.scheduledAt).toISOString();
  }
  return payload;
}

function campaignToForm(c) {
  return {
    title: c.title,
    textTemplate: c.text_template,
    chatIds: c.target_chats.join(", "),
    scheduleType: c.schedule_type,
    intervalMinutes: c.interval_minutes,
    scheduledAt: toLocalDatetimeInput(c.scheduled_at),
    photo: c.photo_url ? { path: null, previewUrl: c.photo_url } : null,
  };
}

function CampaignCard({ campaign, accountId, onChanged }) {
  const [editing, setEditing] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [error, setError] = useState("");

  async function handleUpdate(form) {
    const payload = formToPayload(form);
    if (!payload.photo_path) delete payload.photo_path;
    if (!form.photo) payload.remove_photo = true;
    const updated = await api.updateCampaign(accountId, campaign.id, payload);
    onChanged(updated);
    setEditing(false);
  }

  async function handleDelete() {
    setError("");
    try {
      await api.deleteCampaign(accountId, campaign.id);
      onChanged(null, campaign.id);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleToggleStatus() {
    setError("");
    try {
      const updated =
        campaign.status === "active"
          ? await api.pauseCampaign(accountId, campaign.id)
          : await api.resumeCampaign(accountId, campaign.id);
      onChanged(updated);
    } catch (err) {
      setError(err.message);
    }
  }

  if (editing) {
    return (
      <Card>
        <CampaignForm
          initial={campaignToForm(campaign)}
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
          <div className="flex items-center gap-2">
            <p className="font-medium">{campaign.title}</p>
            <Badge status={campaign.status} />
          </div>
          <p className="text-sm text-slate-400 mt-1">{campaign.text_template}</p>
          <p className="text-xs text-slate-500 mt-1">
            {campaign.schedule_type === "once"
              ? `Одноразово: ${new Date(campaign.scheduled_at).toLocaleString("ru-RU")}`
              : `Каждые ${campaign.interval_minutes} мин`}
            {" · "}
            {campaign.target_chats.length} чат(ов)
          </p>
        </div>
        {campaign.photo_url && (
          <img
            src={campaign.photo_url}
            alt=""
            className="h-14 w-14 rounded-lg object-cover border border-slate-700 shrink-0"
          />
        )}
      </div>

      {error && <p className="text-red-400 text-xs">{error}</p>}

      <div className="flex gap-2 pt-1 flex-wrap">
        <Button variant="secondary" onClick={() => setEditing(true)}>
          Изменить
        </Button>
        {campaign.status !== "finished" && (
          <Button variant="secondary" onClick={handleToggleStatus}>
            {campaign.status === "active" ? "Пауза" : "Запустить"}
          </Button>
        )}
        <Button variant="secondary" onClick={() => setShowLogs(true)}>
          Логи
        </Button>
        <Button variant="danger" onClick={handleDelete}>
          Удалить
        </Button>
      </div>

      {showLogs && (
        <CampaignLogsModal
          accountId={accountId}
          campaignId={campaign.id}
          onClose={() => setShowLogs(false)}
        />
      )}
    </Card>
  );
}

export default function BroadcastPage({ accountId }) {
  const [campaigns, setCampaigns] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (accountId) {
      api
        .listCampaigns(accountId)
        .then(setCampaigns)
        .catch((err) => setError(err.message));
    }
  }, [accountId]);

  async function handleCreate(form) {
    const campaign = await api.createCampaign(accountId, formToPayload(form));
    setCampaigns((prev) => [...prev, campaign]);
    setShowForm(false);
  }

  function handleChanged(updated, deletedId) {
    if (deletedId) {
      setCampaigns((prev) => prev.filter((c) => c.id !== deletedId));
    } else {
      setCampaigns((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    }
  }

  if (!accountId) {
    return <p className="p-4 text-slate-400">Сначала подключите аккаунт на вкладке «Аккаунты».</p>;
  }

  return (
    <div className="p-4 space-y-4">
      <PageHeader
        icon="📣"
        title="Рассылки"
        action={!showForm && <Button onClick={() => setShowForm(true)}>+ Кампания</Button>}
      />

      {showForm && (
        <Card>
          <CampaignForm
            initial={emptyForm}
            submitLabel="Создать"
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
          />
        </Card>
      )}

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <div className="space-y-3">
        {campaigns.map((c) => (
          <CampaignCard key={c.id} campaign={c} accountId={accountId} onChanged={handleChanged} />
        ))}
        {campaigns.length === 0 && !showForm && (
          <p className="text-sm text-slate-500">Кампаний пока нет — создайте первую.</p>
        )}
      </div>
    </div>
  );
}
