/** Page header: the action sits on the title's line, the subtitle gets the
 * full width below — so neither squeezes the other on narrow phones. */
export default function PageTitle({ title, subtitle, action }) {
  return (
    <header className="pt-2">
      <div className="flex min-h-9 items-center justify-between gap-3">
        <h1 className="min-w-0 truncate font-display text-[22px] font-semibold tracking-tight">
          {title}
        </h1>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      {subtitle && <p className="mt-1 text-[14px] leading-snug text-muted">{subtitle}</p>}
    </header>
  );
}
