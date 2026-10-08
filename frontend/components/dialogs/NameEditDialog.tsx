import { useState } from "react";

import { PopupActionButton } from "@/components/ui/PopupActionButton";
import { TextInput } from "@/components/ui/TextInput";
import { DISPLAY_NAME_MAX_LENGTH } from "@/lib/display-name";
import { cn } from "@/lib/utils";

type NameEditDialogProps = {
  /** Why the last save failed. Shown here because the dialog covers the page behind it. */
  error?: string | null;
  initialName: string;
  onCancel: () => void;
  onConfirm: (name: string) => void;
};

export function NameEditDialog({ error, initialName, onCancel, onConfirm }: NameEditDialogProps) {
  const [name, setName] = useState(initialName);

  return (
    <div className="absolute inset-0 z-40 bg-black/40">
      <section aria-modal="true" className={cn("absolute left-5 top-[331px] w-[calc(100%-40px)] rounded-3xl bg-white p-6 shadow-[0_24px_56px_rgba(28,26,23,0.14)]", error ? "min-h-[212px]" : "h-[212px]")} role="dialog">
        <h2 className="text-title-2 text-text">당신의 새로운 이름은?</h2>
        <TextInput className="mt-5 w-full" maxLength={DISPLAY_NAME_MAX_LENGTH} onChange={(event) => setName(event.target.value)} placeholder="새로운 이름을 입력해주세요" value={name} />
        {error ? <p className="mt-2 text-caption-1 text-red-600" role="alert">{error}</p> : null}
        <div className="mt-5 flex justify-end gap-3">
          <PopupActionButton onClick={onCancel}>돌아가기</PopupActionButton>
          <PopupActionButton disabled={!name.trim()} onClick={() => onConfirm(name.trim())} variant="primary">확인</PopupActionButton>
        </div>
      </section>
    </div>
  );
}
