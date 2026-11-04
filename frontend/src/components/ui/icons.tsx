import type { ReactNode } from "react";

function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      aria-hidden="true"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="flex-none"
    >
      {children}
    </svg>
  );
}

export function ApplicationsIcon() {
  return (
    <Icon>
      <rect x="4" y="4" width="16" height="16" rx="3" />
      <path d="M8 9h8M8 12.5h8M8 16h5" />
    </Icon>
  );
}

export function JobsIcon() {
  return (
    <Icon>
      <rect x="3.5" y="7.5" width="17" height="12.5" rx="3" />
      <path d="M8.5 7.5V6a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v1.5" />
    </Icon>
  );
}

export function CandidatesIcon() {
  return (
    <Icon>
      <circle cx="12" cy="8.5" r="4" />
      <path d="M4.5 20c.8-3.6 3.8-5.5 7.5-5.5s6.7 1.9 7.5 5.5" />
    </Icon>
  );
}

export function ModelIcon() {
  return (
    <Icon>
      <path d="M3.5 20.5h17M7 17v-5M12 17V6M17 17V9.5" />
    </Icon>
  );
}
