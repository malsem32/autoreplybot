const VARIANTS = {
  primary: "bg-blue-600 hover:bg-blue-500 text-white",
  secondary: "bg-slate-800 hover:bg-slate-700 text-slate-100",
  danger: "bg-red-600/90 hover:bg-red-600 text-white",
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
      className={`rounded-xl px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}
