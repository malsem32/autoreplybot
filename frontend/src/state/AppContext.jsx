import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, onApiError } from "../api/client.js";

const AppContext = createContext(null);
const ACTIVE_KEY = "autopilot.activeAccount";

function readActive() {
  try {
    return Number(localStorage.getItem(ACTIVE_KEY)) || null;
  } catch {
    return null;
  }
}

export function AppProvider({ children }) {
  const [accounts, setAccounts] = useState(null); // null = loading
  const [accountsError, setAccountsError] = useState("");
  const [activeId, setActiveId] = useState(readActive);
  const [pro, setPro] = useState(null);
  const [isAdmin, setIsAdmin] = useState(null); // null = still checking
  const [toasts, setToasts] = useState([]);
  const [paywall, setPaywall] = useState({ open: false, reason: "" });

  const toast = useCallback((text, tone = "go") => {
    const id = Math.random().toString(36).slice(2);
    setToasts((t) => [...t, { id, text, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 2800);
  }, []);

  const openPaywall = useCallback((reason = "") => setPaywall({ open: true, reason }), []);
  const closePaywall = useCallback(() => setPaywall((p) => ({ ...p, open: false })), []);

  const refreshAccounts = useCallback(async () => {
    try {
      const list = await api.listAccounts();
      setAccounts(list);
      setAccountsError("");
      return list;
    } catch (err) {
      setAccountsError(err.message);
      setAccounts((prev) => prev ?? []);
      return [];
    }
  }, []);

  const refreshPro = useCallback(async () => {
    try {
      setPro(await api.getPro());
    } catch {
      /* non-critical: the paywall retries on open */
    }
  }, []);

  useEffect(() => {
    refreshAccounts();
    refreshPro();
    // A 403 simply means "not an admin" (checked on the backend, AGENTS.md 4.6).
    api
      .adminStats()
      .then(() => setIsAdmin(true))
      .catch(() => setIsAdmin(false));
  }, [refreshAccounts, refreshPro]);

  // Any 402 from the backend (a Pro-only action) opens the paywall.
  useEffect(
    () =>
      onApiError((err) => {
        if (err.status === 402) openPaywall(err.message);
      }),
    [openPaywall],
  );

  const activeAccount = useMemo(() => {
    if (!accounts?.length) return null;
    return accounts.find((a) => a.id === activeId) || accounts[0];
  }, [accounts, activeId]);

  const selectAccount = useCallback((id) => {
    setActiveId(id);
    try {
      localStorage.setItem(ACTIVE_KEY, String(id));
    } catch {
      /* storage may be unavailable */
    }
  }, []);

  const upsertAccount = useCallback(
    (account) => {
      setAccounts((prev) => {
        const list = prev || [];
        return list.some((a) => a.id === account.id)
          ? list.map((a) => (a.id === account.id ? account : a))
          : [...list, account];
      });
      selectAccount(account.id);
    },
    [selectAccount],
  );

  const removeAccount = useCallback((id) => {
    setAccounts((prev) => (prev || []).filter((a) => a.id !== id));
  }, []);

  const value = {
    accounts,
    accountsError,
    activeAccount,
    selectAccount,
    upsertAccount,
    removeAccount,
    refreshAccounts,
    pro,
    refreshPro,
    isAdmin,
    toast,
    toasts,
    paywall,
    openPaywall,
    closePaywall,
  };
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  return useContext(AppContext);
}
