import { useState } from "react";
import { clearToken, getToken } from "./api/client.js";
import DashboardPage from "./pages/DashboardPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";

export default function App() {
  const [loggedIn, setLoggedIn] = useState(Boolean(getToken()));

  if (!loggedIn) {
    return <LoginPage onLoggedIn={() => setLoggedIn(true)} />;
  }

  return (
    <div>
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
        <span className="font-semibold">Автопилот — Admin</span>
        <button
          className="text-sm text-slate-400"
          onClick={() => {
            clearToken();
            setLoggedIn(false);
          }}
          type="button"
        >
          Выйти
        </button>
      </header>
      <DashboardPage />
    </div>
  );
}
