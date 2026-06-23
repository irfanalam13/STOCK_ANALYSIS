import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "@/utils/helpers";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, id, ...props }, ref) => (
    <div className="w-full">
      {label && (
        <label htmlFor={id} className="mb-1 block text-sm font-medium text-fg">
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={id}
        className={cn(
          "h-10 w-full rounded-lg border border-border bg-surface-2 px-3 text-sm text-fg",
          "placeholder:text-muted focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/30",
          error && "border-down focus:border-down focus:ring-down/30",
          className,
        )}
        {...props}
      />
      {error && <p className="mt-1 text-xs text-down">{error}</p>}
    </div>
  ),
);
Input.displayName = "Input";
