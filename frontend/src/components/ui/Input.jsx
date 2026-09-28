import { forwardRef } from "react";

export const Input = forwardRef(function Input({ className = "", ...props }, ref) {
  return <input ref={ref} className={`field ${className}`} {...props} />;
});

export const Textarea = forwardRef(function Textarea({ className = "", ...props }, ref) {
  return (
    <textarea
      ref={ref}
      className={`field min-h-[120px] resize-y leading-relaxed ${className}`}
      {...props}
    />
  );
});

export function Label({ className = "", children, hint, ...props }) {
  return (
    <label className={`mb-1.5 flex items-baseline justify-between gap-2 ${className}`} {...props}>
      <span className="text-[13px] font-medium text-muted">{children}</span>
      {hint && <span className="text-xs text-faint">{hint}</span>}
    </label>
  );
}

export function Field({ label, hint, error, children, htmlFor }) {
  return (
    <div>
      {label && (
        <Label htmlFor={htmlFor} hint={hint}>
          {label}
        </Label>
      )}
      {children}
      {error && <p className="mt-1.5 text-[13px] text-danger">{error}</p>}
    </div>
  );
}
