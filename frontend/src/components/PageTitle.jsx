export default function PageTitle({ title, subtitle, action }) {
  return (
    <header className="flex items-end justify-between gap-3 pt-2">
      <div className="min-w-0">
        <h1 className="font-display text-[22px] font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-[14px] leading-snug text-muted">{subtitle}</p>}
      </div>
      {action}
    </header>
  );
}
