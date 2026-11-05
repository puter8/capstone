import { cn } from "@/lib/utils";

/** One of the English tier labels from profile.traits, shown as is. */
export function TraitChip({ trait, className }: { trait: string; className?: string }) {
  return (
    <li
      className={cn("min-w-0 rounded-p-full bg-p-primary px-p-1 py-p-2 text-center font-p-brand text-p-quote-sm italic text-p-on-primary max-[359px]:text-[14px]", className)}
      lang="en"
      style={{ fontVariationSettings: '"SOFT" 0, "WONK" 1' }}
    >
      {trait}
    </li>
  );
}
