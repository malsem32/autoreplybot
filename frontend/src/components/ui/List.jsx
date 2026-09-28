import { ChevronRight } from "lucide-react";

/** Telegram-style inset grouped list. Rows are separated by inset hairlines. */
export function ListGroup({ title, footer, children, className = "" }) {
  return (
    <section className={className}>
      {title && <h3 className="mb-2 px-1 text-[13px] font-medium text-muted">{title}</h3>}
      <div className="overflow-hidden rounded-[18px] bg-surface">
        <div className="divide-y divide-line/50">{children}</div>
      </div>
      {footer && <p className="mt-2 px-1 text-[13px] leading-snug text-faint">{footer}</p>}
    </section>
  );
}

export function ListRow({
  icon: Icon,
  iconClass = "bg-sky/15 text-sky",
  title,
  subtitle,
  right,
  onClick,
  chevron,
}) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag
      type={onClick ? "button" : undefined}
      onClick={onClick}
      className={`flex w-full items-center gap-3 px-4 py-3 text-left ${onClick ? "active:bg-raised/60 transition-colors" : ""}`}
    >
      {Icon && (
        <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-[10px] ${iconClass}`}>
          <Icon className="h-[18px] w-[18px]" aria-hidden />
        </span>
      )}
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[15px] font-medium">{title}</span>
        {subtitle && (
          <span className="mt-0.5 block text-[13px] leading-snug text-muted">{subtitle}</span>
        )}
      </span>
      {right}
      {chevron && <ChevronRight className="h-4 w-4 shrink-0 text-faint" aria-hidden />}
    </Tag>
  );
}
