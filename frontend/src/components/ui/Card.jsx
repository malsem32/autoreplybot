export default function Card({ className = "", ...props }) {
  return (
    <div
      className={`rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl shadow-black/20 p-4 ${className}`}
      {...props}
    />
  );
}
