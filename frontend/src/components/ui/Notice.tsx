export function ErrorNotice({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <div role="alert" className="notice notice-bad">
      {message}
    </div>
  );
}

export function WarningNotice({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <div role="alert" className="notice notice-warn">
      {message}
    </div>
  );
}
