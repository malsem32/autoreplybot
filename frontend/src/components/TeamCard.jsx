import { AnimatePresence, motion } from "framer-motion";
import { Copy, Crown, Share2, UserMinus, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { confirmDialog, copyText, haptic, shareLink } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";
import { accountName } from "./AccountSwitcher.jsx";
import Button from "./ui/Button.jsx";
import { ErrorNote } from "./ui/Feedback.jsx";

/** Pro "Команда": share the active account with helpers by a single-use
 * invite link — they manage rules, broadcasts and leads without ever
 * getting the login code or the session. */
export default function TeamCard() {
  const { activeAccount, pro, openPaywall, toast } = useApp();
  const [team, setTeam] = useState(null);
  const [invite, setInvite] = useState(null);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const isOwner = activeAccount?.role !== "member";

  useEffect(() => {
    setInvite(null);
    setTeam(null);
    if (!activeAccount || !isOwner) return;
    api
      .getTeam(activeAccount.id)
      .then(setTeam)
      .catch((err) => setError(err.message));
  }, [activeAccount, isOwner]);

  if (!activeAccount || !isOwner) return null;

  async function createInvite() {
    if (!pro?.has_access) {
      openPaywall("Команда — функция Pro");
      return;
    }
    setCreating(true);
    setError("");
    try {
      setInvite(await api.createTeamInvite(activeAccount.id));
      haptic.success();
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  }

  async function remove(member) {
    if (!(await confirmDialog(`Убрать ${member.display_name} из команды?`))) return;
    try {
      await api.removeTeamMember(activeAccount.id, member.id);
      setTeam((t) => ({ ...t, members: t.members.filter((m) => m.id !== member.id) }));
      toast("Участник удалён");
    } catch (err) {
      toast(err.message, "danger");
    }
  }

  return (
    <section className="rounded-[22px] bg-surface p-5">
      <div className="flex items-center gap-3">
        <span className="grid h-11 w-11 place-items-center rounded-xl bg-sky/15 text-sky">
          <Users className="h-6 w-6" />
        </span>
        <div className="min-w-0">
          <h2 className="flex items-center gap-1.5 font-display text-[18px] font-semibold">
            Команда
            {!pro?.has_access && <Crown className="h-4 w-4 text-warn" aria-label="Pro" />}
          </h2>
          <p className="text-[13px] leading-snug text-muted">
            Помощники ведут «{accountName(activeAccount)}» без кода входа
          </p>
        </div>
      </div>

      {team?.members.length > 0 && (
        <ul className="mt-4 space-y-2">
          <AnimatePresence initial={false}>
            {team.members.map((m) => (
              <motion.li
                key={m.id}
                layout
                exit={{ opacity: 0, x: -30 }}
                className="flex items-center gap-3 rounded-tile bg-raised/50 px-3 py-2.5"
              >
                <span className="min-w-0 flex-1 truncate text-[15px] font-medium">
                  {m.display_name}
                </span>
                <button
                  type="button"
                  onClick={() => remove(m)}
                  className="grid h-8 w-8 place-items-center rounded-lg text-faint hover:text-danger"
                  aria-label={`Убрать ${m.display_name}`}
                >
                  <UserMinus className="h-4 w-4" />
                </button>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}

      {invite ? (
        <div className="mt-4 space-y-2">
          <p className="text-[13px] text-muted">
            Ссылка одноразовая и действует сутки. Помощник откроет её и нажмёт «Старт».
          </p>
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="secondary"
              icon={Copy}
              onClick={async () => {
                if (await copyText(invite.link)) toast("Ссылка скопирована");
              }}
            >
              Копировать
            </Button>
            <Button
              icon={Share2}
              onClick={() =>
                shareLink(invite.link, "Приглашаю в команду в Автопилоте — нажмите «Старт»:")
              }
            >
              Отправить
            </Button>
          </div>
        </div>
      ) : (
        <Button
          variant="secondary"
          className="mt-4 w-full"
          loading={creating}
          disabled={team && team.members.length >= team.max_members}
          onClick={createInvite}
        >
          {team && team.members.length >= team.max_members
            ? `Максимум ${team.max_members} участников`
            : "Пригласить помощника"}
        </Button>
      )}
      <div className="mt-2">
        <ErrorNote>{error}</ErrorNote>
      </div>
    </section>
  );
}
