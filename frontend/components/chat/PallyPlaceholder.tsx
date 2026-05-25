/**
 * Phase 1A — Pally placeholder.
 *
 * D-11 / CLAUDE.md §1: This file lives at components/chat/, NOT components/pally/.
 * The components/pally/ directory is Phase 1B's namespace (Canvas2D Superformula
 * renderer). When Phase 1B's renderer is wired in via Plan 05, page.tsx swaps the
 * import in one line.
 *
 * Visual: 262x262 box containing an inline SVG approximation of the Figma "Star4"
 * spike (8-point soft spike, primary orange fill). Phase 1B will overwrite this
 * entirely when its renderer ships.
 */

export function PallyPlaceholder() {
  return (
    <div
      className="w-[262px] h-[262px] flex items-center justify-center"
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 262 262"
        width="262"
        height="262"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* primary token (#fe9012) — SVG fill cannot reference Tailwind tokens */}
        <path
          d="
            M131 0
            L160 80
            L240 60
            L195 130
            L262 161
            L181 178
            L200 252
            L131 215
            L62 252
            L81 178
            L0 161
            L67 130
            L22 60
            L102 80 Z
          "
          fill="#fe9012"
        />
      </svg>
    </div>
  );
}
