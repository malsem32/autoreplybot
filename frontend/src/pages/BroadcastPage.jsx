import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";
import PhotoPicker from "../components/PhotoPicker.jsx";
import Badge from "../components/ui/Badge.jsx";
import Button from "../components/ui/Button.jsx";
import Card from "../components/ui/Card.jsx";
import { Input, Label, Select, Textarea } from "../components/ui/Input.jsx";

// Zero-width space: a placeholder a user can drop into the message text.
// When "tag random users" is on, the broadcaster replaces each occurrence
// with mentions of 5 random members of that chat; otherwise it's stripped.
const TAG_PLACEHOLDER = "​";

const emptyForm = {
  title: "",
  textTemplate: "",
  chatIds: "",
  tagRandomUsers: false,
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
  const textareaRef = useRef(null);

  function insertTagPlaceholder() {
    const el = textareaRef.current;
    const pos = el ? el.selectionStart : form.textTemplate.length;
    const text = form.textTemplate;
    const next = text.slice(0, pos) + TAG_PLACEHOLDER + text.slice(pos);
    setForm({ ...form, textTemplate: next });
    requestAnimationFrame(() => {
      if (!el) return;
      el.focus();
      el.setSelectionRange(pos + 1, pos + 1);
    });
  }

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
          ref={textareaRef}
          placeholder="{Привет|Добрый день}! Есть отличное предложение…"
          value={form.textTemplate}
          onChange={(e) => setForm({ ...form, textTemplate: e.target.value })}
          required
        />
        <div className="flex items-center justify-between gap-2 mt-1.5">
          <Button type="button" variant="secondary" onClick={insertTagPlaceholder}>
            + Метка для тегов
          </Button>
          <Button
            type="button"
            variant={form.tagRandomUsers ? "primary" : "secondary"}
            onClick={() => setForm({ ...form, tagRandomUsers: !form.tagRandomUsers })}
          >
            Теги случайных участников: {form.tagRandomUsers ? "Вкл" : "Выкл"}
          </Button>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Вставьте метку в текст — при отправке она заменится на упоминание 5 случайных
          участников чата (если теги включены), иначе просто удалится.
        </p>
      </div>

      <div>
        <Label>Фото (необязательно)</Label>
        <PhotoPicker
          previewUrl={form.photo?.previewUrl}
          onChange={(photo) => setForm({ ...form, photo })}
        />
      </div>

      <div>
        <Label>ID чатов, через запятую</Label>
        <Input
          placeholder="-1001234567890, 123456789"
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
    target_chat_ids: form.chatIds
      .split(",")
      .map((id) => Number(id.trim()))
      .filter(Boolean),
    tag_random_users: form.tagRandomUsers,
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
    chatIds: c.target_chat_ids.join(", "),
    tagRandomUsers: c.tag_random_users,
    scheduleType: c.schedule_type,
    intervalMinutes: c.interval_minutes,
    scheduledAt: toLocalDatetimeInput(c.scheduled_at),
    photo: c.photo_url ? { path: null, previewUrl: c.photo_url } : null,
  };
}

function CampaignCard({ campaign, accountId, onChanged }) {
  const [editing, setEditing] = useState(false);
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
              ? `Once: ${new Date(campaign.scheduled_at).toLocaleString("ru-RU")}`
              : `Каждые ${campaign.interval_minutes} мин`}
            {" · "}
            {campaign.target_chat_ids.length} чат(ов)
            {campaign.tag_random_users && " · теги случайных участников"}
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

      <div className="flex gap-2 pt-1">
        <Button variant="secondary" onClick={() => setEditing(true)}>
          Изменить
        </Button>
        {campaign.status !== "finished" && (
          <Button variant="secondary" onClick={handleToggleStatus}>
            {campaign.status === "active" ? "Пауза" : "Запустить"}
          </Button>
        )}
        <Button variant="danger" onClick={handleDelete}>
          Удалить
        </Button>
      </div>
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
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Рассылки</h1>
        {!showForm && <Button onClick={() => setShowForm(true)}>+ Кампания</Button>}
      </div>

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
