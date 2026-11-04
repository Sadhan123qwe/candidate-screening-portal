import type { ComponentPropsWithoutRef, ElementType } from "react";

const PADDING = { none: "", sm: "pad-sm", md: "pad-md", lg: "pad-lg" };

type GlassCardProps<T extends ElementType> = {
  as?: T;
  padding?: keyof typeof PADDING;
} & ComponentPropsWithoutRef<T>;

export function GlassCard<T extends ElementType = "div">({ as, padding = "md", className = "", ...props }: GlassCardProps<T>) {
  const Element: ElementType = as ?? "div";
  return <Element className={`glass ${PADDING[padding as keyof typeof PADDING]} ${className}`} {...props} />;
}
