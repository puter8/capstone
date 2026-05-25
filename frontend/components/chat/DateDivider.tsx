type DateDividerProps = {
  kind: 'date' | 'time';
  label: string;
};

export function DateDivider({ label }: DateDividerProps) {
  return (
    <div className="flex items-center gap-3 w-full h-4">
      <span className="flex-1 border-t border-dashed border-border" aria-hidden />
      <span className="text-text-tertiary text-[12px] leading-4 whitespace-nowrap">
        {label}
      </span>
      <span className="flex-1 border-t border-dashed border-border" aria-hidden />
    </div>
  );
}
