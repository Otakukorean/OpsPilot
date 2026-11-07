"use client";

import { AlertTriangle, LoaderCircle, X } from "lucide-react";
import { useEffect, useId, useRef } from "react";

type ConfirmationModalProps = {
  open: boolean;
  title: string;
  description: string;
  subject?: string;
  confirmLabel: string;
  pendingLabel?: string;
  isPending?: boolean;
  error?: string;
  onCancel: () => void;
  onConfirm: () => void;
};

export function ConfirmationModal({
  open,
  title,
  description,
  subject,
  confirmLabel,
  pendingLabel = "Working…",
  isPending = false,
  error,
  onCancel,
  onConfirm,
}: ConfirmationModalProps) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const isPendingRef = useRef(isPending);
  const onCancelRef = useRef(onCancel);

  useEffect(() => {
    isPendingRef.current = isPending;
    onCancelRef.current = onCancel;
  }, [isPending, onCancel]);

  useEffect(() => {
    if (!open) return;

    const previousFocus = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    cancelRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !isPendingRef.current) {
        event.preventDefault();
        onCancelRef.current();
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
        "button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])",
      );
      if (!focusable?.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[80] grid place-items-center bg-[#17211d]/55 p-4 backdrop-blur-[2px]"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isPending) onCancel();
      }}
    >
      <div
        aria-describedby={descriptionId}
        aria-labelledby={titleId}
        aria-modal="true"
        className="relative w-full max-w-md overflow-hidden border border-[#cbbfba] bg-[#fbfcf8] shadow-[0_28px_80px_rgba(16,28,23,0.28)]"
        ref={dialogRef}
        role="alertdialog"
      >
        <div className="h-1 bg-[#a54838]" />
        <div className="p-5 sm:p-6">
          <div className="flex items-start gap-4">
            <span className="flex size-10 shrink-0 items-center justify-center border border-[#e0bdb7] bg-[#faece9] text-[#9f4034]">
              <AlertTriangle aria-hidden="true" size={19} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#a54838]">Permanent action</p>
              <h2 className="mt-1 text-lg font-semibold tracking-[-0.025em] text-[#27332e]" id={titleId}>{title}</h2>
            </div>
            <button
              aria-label="Close confirmation"
              className="-mr-1 -mt-1 flex size-9 shrink-0 items-center justify-center text-[#75807b] hover:bg-[#edf0eb] hover:text-[#34413b] disabled:opacity-40"
              disabled={isPending}
              onClick={onCancel}
              type="button"
            >
              <X aria-hidden="true" size={17} />
            </button>
          </div>

          <p className="mt-5 text-sm leading-6 text-[#66726c]" id={descriptionId}>{description}</p>
          {subject ? <p className="mt-3 truncate border-l-2 border-[#b75a4d] bg-[#f4f3ef] px-3 py-2.5 text-sm font-semibold text-[#35413c]">{subject}</p> : null}
          <p className="mt-3 text-xs font-semibold text-[#8d493f]">This action cannot be undone.</p>
          {error ? <p className="mt-4 border border-[#e1beb8] bg-[#faece9] px-3 py-2 text-xs leading-5 text-[#963e33]" role="alert">{error}</p> : null}

          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button
              className="h-10 border border-[#cbd2cb] bg-white px-4 text-xs font-bold text-[#53605a] hover:bg-[#f0f2ed] disabled:opacity-50"
              disabled={isPending}
              onClick={onCancel}
              ref={cancelRef}
              type="button"
            >
              Cancel
            </button>
            <button
              className="flex h-10 items-center justify-center gap-2 bg-[#a54838] px-4 text-xs font-bold text-white hover:bg-[#8f392f] disabled:bg-[#c78e85]"
              disabled={isPending}
              onClick={onConfirm}
              type="button"
            >
              {isPending ? <LoaderCircle aria-hidden="true" className="animate-spin" size={15} /> : null}
              {isPending ? pendingLabel : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
