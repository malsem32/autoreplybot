const VARIANTS = {
  primary:
    "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-lg shadow-blue-950/40",
  secondary: "bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700",
  danger: "bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-950/30",
  ghost: "bg-transparent hover:bg-slate-800 text-slate-300",
};

export default function Button({
  variant = "primary",
  className = "",
  type = "button",
  ...props
}) {
  return (
    <button
      type={type}
      className={`rounded-xl px-4 py-2.5 text-sm font-semibold tracking-tight transition-all active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none disabled:active:scale-100 ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}
