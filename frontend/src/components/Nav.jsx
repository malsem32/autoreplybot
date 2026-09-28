import { motion } from "framer-motion";
import { Gauge, Inbox, MessageCircleReply, Send, UserRound } from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";
import { haptic } from "../lib/telegram.js";

export const TABS = [
  { to: "/", label: "Главная", icon: Gauge },
  { to: "/autoresponder", label: "Автоответ", icon: MessageCircleReply },
  { to: "/leads", label: "Обращения", icon: Inbox },
  { to: "/broadcast", label: "Рассылки", icon: Send },
  { to: "/profile", label: "Профиль", icon: UserRound },
];

export function tabIndex(pathname) {
  if (pathname.startsWith("/admin")) return TABS.length - 1;
  const i = TABS.findIndex((t) => (t.to === "/" ? pathname === "/" : pathname.startsWith(t.to)));
  return i === -1 ? 0 : i;
}

export default function Nav() {
  const { pathname } = useLocation();
  const current = tabIndex(pathname);

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 border-t border-line/60 bg-bg/85 backdrop-blur-xl"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="mx-auto flex max-w-lg">
        {TABS.map((tab, i) => {
          const active = i === current;
          return (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.to === "/"}
              onClick={() => !active && haptic.select()}
              className={`relative flex flex-1 flex-col items-center gap-1 pb-2 pt-2.5 text-[10.5px] font-semibold transition-colors ${
                active ? "text-sky" : "text-faint"
              }`}
            >
              {active && (
                <motion.span
                  layoutId="nav-pill"
                  className="absolute top-1.5 h-8 w-12 rounded-full bg-sky/12"
                  transition={{ type: "spring", stiffness: 500, damping: 38 }}
                />
              )}
              <tab.icon
                className="relative h-[22px] w-[22px]"
                strokeWidth={active ? 2.3 : 1.9}
                aria-hidden
              />
              <span className="relative">{tab.label}</span>
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}
