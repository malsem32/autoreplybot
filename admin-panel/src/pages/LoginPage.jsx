import { useState } from "react";
import { api, setToken } from "../api/client.js";

export default function LoginPage({ onLoggedIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      const { access_token: accessToken } = await api.login(username, password);
      setToken(accessToken);
      onLoggedIn();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-3 p-6">
        <h1 className="text-xl font-semibold mb-4">Автопилот — Admin</h1>
        <input
          className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2"
          placeholder="Логин"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <input
          className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2"
          placeholder="Пароль"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button className="w-full rounded-lg bg-blue-600 py-2 font-medium" type="submit">
          Войти
        </button>
        {error && <p className="text-red-400 text-sm">{error}</p>}
      </form>
    </div>
  );
}
