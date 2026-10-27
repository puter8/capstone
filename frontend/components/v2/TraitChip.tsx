import { cn } from "@/lib/utils";

/** One of the English tier labels from profile.traits, shown as is. */
export function TraitChip({ trait, className }: { trait: string; className?: string }) {
  return (
    <li
      className={cn("rounded-p-full border border-p-border px-[14px] py-[6px] font-p-brand text-p-quote-sm italic text-p-text", className)}
      lang="en"
      style={{ fontVariationSettings: '"SOFT" 0, "WONK" 1' }}
    >
      {trait}
    </li>
  );
}
