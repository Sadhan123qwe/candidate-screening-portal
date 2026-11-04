import {
  forwardRef,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";

interface FieldProps {
  id: string;
  label?: string;
  error?: string;
  hint?: string;
  children: ReactNode;
}

/** A label above the control, with any hint or error beneath it. */
export function Field({ id, label, error, hint, children }: FieldProps) {
  return (
    <div>
      {label && (
        <label htmlFor={id} className="field-label">
          {label}
        </label>
      )}
      {children}
      {hint && !error && <p className="field-hint">{hint}</p>}
      {error && (
        <p id={`${id}-error`} role="alert" className="field-error">
          {error}
        </p>
      )}
    </div>
  );
}

/** The attributes that tie a control to its error message. */
export function errorAttributes(id: string, error?: string) {
  return error ? { "aria-invalid": true, "aria-describedby": `${id}-error` } : {};
}

interface ControlProps {
  id: string;
  label?: string;
  error?: string;
  hint?: string;
}

type InputProps = ControlProps & InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input({ id, label, error, hint, className = "", ...props }, ref) {
  return (
    <Field id={id} label={label} error={error} hint={hint}>
      <input ref={ref} id={id} className={`control ${error ? "control-error" : ""} ${className}`} {...errorAttributes(id, error)} {...props} />
    </Field>
  );
});

export function Select({ id, label, error, hint, className = "", children, ...props }: ControlProps & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <Field id={id} label={label} error={error} hint={hint}>
      <select id={id} className={`control ${error ? "control-error" : ""} ${className}`} {...errorAttributes(id, error)} {...props}>
        {children}
      </select>
    </Field>
  );
}

export function Textarea({ id, label, error, hint, className = "", ...props }: ControlProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <Field id={id} label={label} error={error} hint={hint}>
      <textarea id={id} className={`control ${error ? "control-error" : ""} ${className}`} {...errorAttributes(id, error)} {...props} />
    </Field>
  );
}
