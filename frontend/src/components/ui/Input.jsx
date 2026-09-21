import { forwardRef } from "react";

export function Input({ className = "", ...props }) {
  return (
    <input
      className={`w-full rounded-xl bg-slate-900 border border-slate-700 px-3 py-2.5 text-sm placeholder:text-slate-500 focus:outline-none focus:border-blue-500 ${className}`}
      {...props}
    />
  );
}

export const Textarea = forwardRef(function Textarea({ className = "", ...props }, ref) {
  return (
    <textarea
      ref={ref}
      className={`w-full rounded-xl bg-slate-900 border border-slate-700 px-3 py-2.5 text-sm placeholder:text-slate-500 focus:outline-none focus:border-blue-500 min-h-[88px] resize-y ${className}`}
      {...props}
    />
  );
});

export function Select({ className = "", ...props }) {
  return (
    <select
      className={`w-full rounded-xl bg-slate-900 border border-slate-700 px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500 ${className}`}
      {...props}
    />
  );
}

export function Label({ className = "", ...props }) {
  return <label className={`block text-xs text-slate-400 mb-1.5 ${className}`} {...props} />;
}
