import { ChevronDown, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client.js";
import { confirmDialog, haptic } from "../lib/telegram.js";
import { useApp } from "../state/AppContext.jsx";
import AddAccountSheet from "./login/AddAccountSheet.jsx";
import { Pill } from "./ui/Feedback.jsx";
import Sheet from "./ui/Sheet.jsx";

export function initials(account) {
  const source = account?.first_name || account?.username || account?.phone || "?";
  return source.trim().slice(0, 1).toUpperCase();
}

export function accountName(account) {
  return account?.first_name || (account?.username ? `@${account.username}` : null) || "Без имени";
}

export function Avatar({ account, size = "h-10 w-10 text-base" }) {
  return (
    <span
      className={`grid shrink-0 place-items-center rounded-full bg-gradient-to-br from-sky to-[#1E6FD9] font-display font-semibold text-white ${size}`}
    >
      {initials(account)}
    </span>
  );
}

export default function AccountSwitcher() {
  const { accounts, activeAccount, selectAccount, removeAccount, toast } = useApp();
  const [open, setOpen] = useState(false);
  const [adding, setAdding] = useState(false);

  async function handleDelete(account) {
    const member = account.role === "member";
    const ok = await confirmDialog(
      member
        ? `Выйти из команды аккаунта ${accountName(account)}?`
        : `Отключить ${accountName(account)}? Правила автоответа и рассылки этого аккаунта будут удалены.`,
    );
    if (!ok) return;
    try {
      if (member) await api.leaveTeam(account.id);
      else await api.deleteAccount(account.id);
      removeAccount(account.id);
      haptic.success();
      toast(member ? "Вы вышли из команды" : "Аккаунт отключён");
    } catch (err) {
      toast(err.message, "danger");
    }
  }

  if (!activeAccount) return null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-2.5 rounded-full bg-surface py-1.5 pl-1.5 pr-3 transition-colors active:bg-raised"
      >
        <Avatar account={activeAccount} size="h-8 w-8 text-sm" />
        <span className="max-w-[40vw] truncate text-sm font-semibold">
          {accountName(activeAccount)}
        </span>
        <ChevronDown className="h-4 w-4 text-muted" aria-hidden />
      </button>

      <Sheet open={open} onClose={() => setOpen(false)} title="Аккаунты">
        <div className="space-y-2 pt-1">
          {accounts.map((account) => {
            const active = account.id === activeAccount.id;
            return (
              <div
                key={account.id}
                className={`flex items-center gap-3 rounded-tile p-3 transition-colors ${active ? "bg-sky/10 ring-1 ring-sky/40" : "bg-raised/50"}`}
              >
                <button
                  type="button"
                  className="flex min-w-0 flex-1 items-center gap-3 text-left"
                  onClick={() => {
                    haptic.select();
                    selectAccount(account.id);
                    setOpen(false);
                  }}
                >
                  <Avatar account={account} />
                  <span className="min-w-0">
                    <span className="block truncate font-semibold">{accountName(account)}</span>
                    <span className="block truncate text-[13px] text-muted">
                      {account.username ? `@${account.username} · ` : ""}
                      {account.phone ? `+${account.phone}` : "номер скрыт"}
                    </span>
                  </span>
                </button>
                {account.role === "member" && <Pill tone="sky">команда</Pill>}
                <Pill tone={account.is_active ? "go" : "warn"} dot>
                  {account.is_active ? "Вкл" : "Пауза"}
                </Pill>
                <button
                  type="button"
                  onClick={() => handleDelete(account)}
                  title={account.role === "member" ? "Выйти из команды" : "Отключить аккаунт"}
                  className="grid h-9 w-9 place-items-center rounded-lg text-faint hover:text-danger"
                  aria-label={`Отключить ${accountName(account)}`}
                >
                  <Trash2 className="h-[18px] w-[18px]" />
                </button>
              </div>
            );
          })}
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              setAdding(true);
            }}
            className="flex w-full items-center gap-3 rounded-tile border border-dashed border-line p-3 text-sky"
          >
            <span className="grid h-10 w-10 place-items-center rounded-full bg-sky/12">
              <Plus className="h-5 w-5" />
            </span>
            <span className="font-semibold">Подключить ещё аккаунт</span>
          </button>
        </div>
      </Sheet>
      <AddAccountSheet open={adding} onClose={() => setAdding(false)} />
    </>
  );
}
