import { useEffect, useRef, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

interface ModalProps {
  title: string;
  description?: string;
  onClose: () => void;
  children: ReactNode;
}

/** A dialog that holds keyboard focus, closes on Esc, and blurs the page behind it. */
export function Modal({ title, description, onClose, children }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  useEffect(() => {
    // Focus goes back to whatever opened the dialog, so keyboard users don't lose their place.
    const opener = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();
    document.body.classList.add("modal-open");
    return () => {
      document.body.classList.remove("modal-open");
      opener?.focus?.();
    };
  }, []);

  function keepFocusInside(event: ReactKeyboardEvent) {
    if (event.key !== "Tab" || !dialogRef.current) return;
    const focusable = [...dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
    if (focusable.length === 0) {
      event.preventDefault();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const active = document.activeElement;
    if (event.shiftKey && (active === first || active === dialogRef.current)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return createPortal(
    <div className="modal-overlay">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className="glass modal-dialog"
        onKeyDown={keepFocusInside}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-[22px] font-semibold leading-[28px]">{title}</h2>
            {description && <p className="mt-1 text-muted">{description}</p>}
          </div>
          <button type="button" aria-label="Close" onClick={onClose} className="modal-close">
            <svg aria-hidden="true" width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
              <path d="M1.5 1.5l11 11M12.5 1.5l-11 11" />
            </svg>
          </button>
        </div>
        <div className="mt-[14px]">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
