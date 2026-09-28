import { Crown } from "lucide-react";
import { useApp } from "../../state/AppContext.jsx";
import { ListRow } from "../ui/List.jsx";
import Switch from "../ui/Switch.jsx";

/** A switch row; Pro-only options show a crown and open the paywall
 * instead of toggling while the user has no Pro. */
export default function OptionRow({ icon, title, subtitle, checked, onChange, proOnly, children }) {
  const { pro, openPaywall } = useApp();
  const locked = proOnly && !pro?.has_access;
  return (
    <div>
      <ListRow
        icon={icon}
        iconClass={proOnly ? "bg-warn/15 text-warn" : "bg-sky/15 text-sky"}
        title={
          <span className="inline-flex items-center gap-1.5">
            {title}
            {proOnly && <Crown className="h-3.5 w-3.5 text-warn" aria-label="Pro" />}
          </span>
        }
        subtitle={subtitle}
        right={
          <Switch
            checked={Boolean(checked) && !locked}
            onChange={(v) => (locked ? openPaywall(`«${title}» — функция Pro`) : onChange(v))}
            label={title}
          />
        }
      />
      {checked && !locked && children && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}
