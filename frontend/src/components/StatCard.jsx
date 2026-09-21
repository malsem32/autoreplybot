export default function StatCard({ label, value }) {
  return (
    <div className="rounded-xl bg-slate-900/80 border border-slate-800 shadow-lg shadow-black/20 p-4">
      <p className="text-xs text-slate-400 font-medium">{label}</p>
      <p className="text-3xl font-bold tracking-tight mt-1 bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
        {value}
      </p>
    </div>
  );
}
