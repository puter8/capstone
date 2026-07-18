import { PopupActionButton } from "@/components/ui/PopupActionButton";

type ConfirmDialogProps = {
  body: string;
  confirmLabel: string;
  onCancel: () => void;
  onConfirm: () => void;
  title: string;
};

export function ConfirmDialog({ body, confirmLabel, onCancel, onConfirm, title }: ConfirmDialogProps) {
  return (
    <div className="absolute inset-0 z-40 bg-black/40">
      <section aria-modal="true" className="absolute left-5 top-[332px] h-[210px] w-[calc(100%-40px)] rounded-3xl bg-white p-6 shadow-[0_24px_56px_rgba(28,26,23,0.14)]" role="dialog">
        <h2 className="text-title-1 text-text">{title}</h2>
        <p className="mt-3 whitespace-pre-line text-[15px] leading-5 text-text-secondary">{body}</p>
        <div className="absolute bottom-6 left-6 right-6 flex justify-end gap-3">
          <PopupActionButton onClick={onCancel}>돌아가기</PopupActionButton>
          <PopupActionButton onClick={onConfirm} variant="primary">{confirmLabel}</PopupActionButton>
        </div>
      </section>
    </div>
  );
}
