export default function Card({ className = "", ...props }) {
  return (
    <div
      className={`rounded-2xl bg-slate-900 border border-slate-800 p-4 ${className}`}
      {...props}
    />
  );
}
