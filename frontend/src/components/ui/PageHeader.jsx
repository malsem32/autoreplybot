export default function PageHeader({ icon, title, action }) {
  return (
    <div className="flex items-center justify-between">
      <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
        {icon && <span className="text-2xl leading-none">{icon}</span>}
        {title}
      </h1>
      {action}
    </div>
  );
}
