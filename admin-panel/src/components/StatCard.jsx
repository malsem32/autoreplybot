export default function StatCard({ label, value }) {
  return (
    <div className="rounded-lg bg-slate-900 border border-slate-800 p-4">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="text-2xl font-semibold mt-1">{value}</p>
    </div>
  );
}
