import type { ButtonHTMLAttributes } from "react";

// Written out in full, because Tailwind drops any class it can't find literally in the source.
const VARIANT = { primary: "btn-primary", secondary: "btn-secondary", ghost: "btn-ghost" };

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof VARIANT;
}

export function Button({ variant = "secondary", type = "button", className = "", ...props }: ButtonProps) {
  return <button type={type} className={`btn ${VARIANT[variant]} ${className}`} {...props} />;
}
