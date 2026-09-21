import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { api } from "./api/client.js";
import Nav from "./components/Nav.jsx";
import AccountsPage from "./pages/AccountsPage.jsx";
import AutoresponderPage from "./pages/AutoresponderPage.jsx";
import BroadcastPage from "./pages/BroadcastPage.jsx";
import ProxiesPage from "./pages/ProxiesPage.jsx";
import StatsPage from "./pages/StatsPage.jsx";

export default function App() {
  const [accounts, setAccounts] = useState([]);
  const [activeAccountId, setActiveAccountId] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    api
      .listAccounts()
      .then((list) => {
        setAccounts(list);
        if (list.length > 0) setActiveAccountId(list[0].id);
      })
      .catch(() => {});

    // Probing /api/admin/stats is how the Mini App learns whether the
    // current Telegram user_id is in ADMIN_TELEGRAM_IDS (backend-enforced,
    // see AGENTS.md 4.6) — a 403 just means "not an admin", not an error.
    api
      .adminStats()
      .then(() => setIsAdmin(true))
      .catch(() => {});
  }, []);

  function handleAccountAdded(account) {
    setAccounts((prev) => [...prev, account]);
    setActiveAccountId(account.id);
  }

  return (
    <div className="min-h-screen pb-16">
      <Routes>
        <Route
          path="/"
          element={
            <AccountsPage
              accounts={accounts}
              activeAccountId={activeAccountId}
              onSelect={setActiveAccountId}
              onAdded={handleAccountAdded}
            />
          }
        />
        <Route
          path="/autoresponder"
          element={<AutoresponderPage accountId={activeAccountId} />}
        />
        <Route path="/broadcast" element={<BroadcastPage accountId={activeAccountId} />} />
        {isAdmin && <Route path="/stats" element={<StatsPage />} />}
        {isAdmin && <Route path="/proxies" element={<ProxiesPage />} />}
      </Routes>
      <Nav isAdmin={isAdmin} />
    </div>
  );
}
