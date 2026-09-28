import { motion } from "framer-motion";
import { useRef } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Nav, { tabIndex } from "./components/Nav.jsx";
import PaywallSheet from "./components/pro/PaywallSheet.jsx";
import Toasts from "./components/Toasts.jsx";
import { Skeleton } from "./components/ui/Feedback.jsx";
import AutoresponderPage from "./pages/AutoresponderPage.jsx";
import BroadcastPage from "./pages/BroadcastPage.jsx";
import HomePage from "./pages/HomePage.jsx";
import LeadsPage from "./pages/LeadsPage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import ProxiesPage from "./pages/ProxiesPage.jsx";
import StatsPage from "./pages/StatsPage.jsx";
import { AppProvider, useApp } from "./state/AppContext.jsx";

/** The real check is on the backend (AGENTS.md 4.6); this only avoids
 * showing admin screens to people who'd get 403s everywhere. */
function AdminOnly({ isAdmin, page }) {
  if (isAdmin === null) return <Skeleton className="m-4 h-64" />;
  return isAdmin ? page : <Navigate to="/" replace />;
}

function AnimatedRoutes() {
  const location = useLocation();
  const { isAdmin } = useApp();
  const index = tabIndex(location.pathname);
  const prev = useRef(index);
  const direction = index === prev.current ? 0 : index > prev.current ? 1 : -1;
  prev.current = index;

  // Enter-only transition. An exit animation would keep the previous page
  // mounted (and tappable) on top of the new one until it finished — on a
  // slow phone that swallowed taps meant for the new page.
  return (
    <motion.main
      key={location.pathname}
      initial={{ opacity: 0, x: direction * 16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2, ease: [0.2, 0.7, 0.2, 1] }}
      className="mx-auto max-w-lg"
    >
      <Routes location={location}>
        <Route path="/" element={<HomePage />} />
        <Route path="/autoresponder" element={<AutoresponderPage />} />
        <Route path="/leads" element={<LeadsPage />} />
        <Route path="/broadcast" element={<BroadcastPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/admin/stats" element={<AdminOnly isAdmin={isAdmin} page={<StatsPage />} />} />
        <Route
          path="/admin/proxies"
          element={<AdminOnly isAdmin={isAdmin} page={<ProxiesPage />} />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </motion.main>
  );
}

export default function App() {
  return (
    <AppProvider>
      {/* Fullscreen: keeps scrolled content from showing through the status
          bar and Telegram's floating buttons. Zero-height otherwise. */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-x-0 top-0 z-30 bg-bg"
        style={{ height: "var(--inset-top)" }}
      />
      <div
        className="overflow-x-hidden"
        style={{
          minHeight: "var(--app-height)",
          paddingTop: "var(--inset-top)",
          paddingBottom: "calc(76px + var(--inset-bottom))",
        }}
      >
        <AnimatedRoutes />
      </div>
      <Nav />
      <PaywallSheet />
      <Toasts />
    </AppProvider>
  );
}
