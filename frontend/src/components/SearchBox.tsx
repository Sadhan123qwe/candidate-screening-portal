import { useEffect, useState } from "react";
import { Input } from "./ui/Controls";

const DEBOUNCE_MS = 300;

interface SearchBoxProps {
  id: string;
  /** Read by screen readers. Shown only if visibleLabel is left out and there's no other label. */
  label: string;
  visibleLabel?: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}

/** Waits for a pause in typing, so each keystroke doesn't trigger a request. */
export function SearchBox({ id, label, visibleLabel, placeholder, value, onChange }: SearchBoxProps) {
  const [text, setText] = useState(value);

  // Follow outside changes, such as the back button restoring an earlier URL.
  useEffect(() => setText(value), [value]);

  useEffect(() => {
    if (text === value) return;
    const timer = setTimeout(() => onChange(text), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [text, value, onChange]);

  return (
    <Input
      id={id}
      type="search"
      label={visibleLabel}
      aria-label={label}
      placeholder={placeholder}
      value={text}
      onChange={(event) => setText(event.target.value)}
    />
  );
}
