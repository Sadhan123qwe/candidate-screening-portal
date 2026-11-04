import type { ReactNode } from "react";
import { Button } from "./Button";
import { GlassCard } from "./GlassCard";

const SKELETON_WIDTHS = ["72%", "94%", "58%", "86%"];

export function LoadingState() {
  return (
    <GlassCard padding="md" role="status" className="space-y-4">
      <span className="sr-only">Loading...</span>
      {SKELETON_WIDTHS.map((width) => (
        <span key={width} aria-hidden="true" className="skeleton" style={{ width }} />
      ))}
    </GlassCard>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <GlassCard padding="none" role="alert" className="state">
      <p className="text-[color:var(--bad-text)]">{message}</p>
      <Button onClick={onRetry}>Retry</Button>
    </GlassCard>
  );
}

export function EmptyState({ message, action }: { message: string; action?: ReactNode }) {
  return (
    <GlassCard padding="none" className="state">
      <p className="text-muted">{message}</p>
      {action}
    </GlassCard>
  );
}
