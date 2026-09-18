import { useState } from "react";
import { Route, Routes } from "react-router-dom";
import Nav from "./components/Nav.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import AutoresponderPage from "./pages/AutoresponderPage.jsx";
import BroadcastPage from "./pages/BroadcastPage.jsx";

export default function App() {
  const [accountId, setAccountId] = useState(null);

  return (
    <div className="min-h-screen pb-16">
      <Routes>
        <Route path="/" element={<AuthPage onConnected={(acc) => setAccountId(acc.id)} />} />
        <Route path="/autoresponder" element={<AutoresponderPage accountId={accountId} />} />
        <Route path="/broadcast" element={<BroadcastPage accountId={accountId} />} />
      </Routes>
      <Nav />
    </div>
  );
}
