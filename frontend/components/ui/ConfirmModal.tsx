import type { ReactNode } from "react";

interface ConfirmModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
}

export function ConfirmModal({ title, onClose, children }: ConfirmModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-canvas/80 px-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-none border border-muted/20 bg-surface p-6">
        <div className="flex items-start justify-between gap-4">
          <h2 className="text-base font-semibold text-muted">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Schließen"
            className="text-muted/50 hover:text-muted"
          >
            ✕
          </button>
        </div>
        <div className="mt-4">{children}</div>
      </div>
    </div>
  );
}
