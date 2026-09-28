import { LifeBuoy, MessageCircle, Send } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client.js";
import { haptic, openTelegramLink } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";
import Button from "./ui/Button.jsx";
import { ErrorNote } from "./ui/Feedback.jsx";
import { Field, Textarea } from "./ui/Input.jsx";
import { ListGroup, ListRow } from "./ui/List.jsx";
import Sheet from "./ui/Sheet.jsx";

/** «Помощь»: the message goes to the admins through the bot; their answer
 * arrives in the user's chat with the bot. */
export default function HelpCard() {
  const { pro, toast } = useApp();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const bot = pro?.bot_username;

  async function send() {
    setSending(true);
    setError("");
    try {
      await api.contactSupport(text.trim());
      haptic.success();
      toast("Отправлено! Ответ придёт в чат с ботом");
      setText("");
      setOpen(false);
    } catch (err) {
      haptic.error();
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <ListGroup>
        <ListRow
          icon={LifeBuoy}
          iconClass="bg-go/15 text-go"
          title="Помощь"
          subtitle="Что-то не работает? Напишите нам"
          chevron
          onClick={() => {
            setError("");
            setOpen(true);
          }}
        />
      </ListGroup>
      <Sheet
        open={open}
        onClose={() => setOpen(false)}
        title="Помощь"
        footer={
          <Button
            className="w-full"
            icon={Send}
            loading={sending}
            disabled={text.trim().length < 3}
            onClick={send}
          >
            Отправить
          </Button>
        }
      >
        <div className="space-y-4 pt-1">
          <p className="text-[14px] leading-snug text-muted">
            Опишите, что делали и что пошло не так. Ответ придёт в чат с ботом — обычно в течение
            дня.
          </p>
          <Field label="Сообщение" htmlFor="help-text">
            <Textarea
              id="help-text"
              value={text}
              maxLength={2000}
              onChange={(e) => setText(e.target.value)}
              placeholder="Например: не приходит код при входе в аккаунт…"
              className="min-h-[130px]"
            />
          </Field>
          <ErrorNote>{error}</ErrorNote>
          {bot && (
            <button
              type="button"
              onClick={() => openTelegramLink(`https://t.me/${bot}?start=help`)}
              className="flex items-center gap-2 text-[14px] font-semibold text-sky"
            >
              <MessageCircle className="h-4 w-4" aria-hidden />
              Нужен скриншот? Напишите в чате с ботом
            </button>
          )}
        </div>
      </Sheet>
    </>
  );
}
