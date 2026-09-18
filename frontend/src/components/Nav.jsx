import { NavLink } from "react-router-dom";

const linkClass = ({ isActive }) =>
  `flex-1 py-3 text-center text-sm ${isActive ? "text-blue-400 font-medium" : "text-slate-400"}`;

export default function Nav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 flex border-t border-slate-800 bg-slate-950">
      <NavLink to="/" end className={linkClass}>
        Аккаунт
      </NavLink>
      <NavLink to="/autoresponder" className={linkClass}>
        Автоответ
      </NavLink>
      <NavLink to="/broadcast" className={linkClass}>
        Рассылка
      </NavLink>
    </nav>
  );
}
