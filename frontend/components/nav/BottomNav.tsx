'use client';

import { cn } from '@/lib/utils';

type TabId = 'home' | 'history' | 'new' | 'ranking' | 'profile';
interface Tab {
  id: TabId;
  label: string;
  isFab: boolean;
}

// Korean labels locked by DESIGN.md decisions log 2026-05-25 + UI-SPEC § Copywriting Contract.
const TABS: readonly Tab[] = [
  { id: 'home', label: '홈', isFab: false },
  { id: 'history', label: '히스토리', isFab: false },
  { id: 'new', label: '새 대화', isFab: true },
  { id: 'ranking', label: '랭킹', isFab: false },
  { id: 'profile', label: '내 정보', isFab: false },
];

// 24x24 stroke icons — minimal placeholder shapes (Figma exact glyphs deferred to Phase B polish).
function TabIcon({ id }: { id: TabId }) {
  // #33363f = icon token — SVG stroke attr cannot reference Tailwind tokens.
  const stroke = '#33363f';
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      {id === 'home' && (
        <path
          d="M4 11l8-7 8 7v9a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1v-9z"
          stroke={stroke}
          strokeWidth="2"
          strokeLinejoin="round"
        />
      )}
      {id === 'history' && (
        <g
          stroke={stroke}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="8" fill="none" />
          <path d="M12 7v5l3 2" />
        </g>
      )}
      {id === 'ranking' && (
        <path
          d="M5 21V10M12 21V4M19 21v-7"
          stroke={stroke}
          strokeWidth="2"
          strokeLinecap="round"
        />
      )}
      {id === 'profile' && (
        <g
          stroke={stroke}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        >
          <circle cx="12" cy="8" r="4" />
          <path d="M4 21a8 8 0 0 1 16 0" />
        </g>
      )}
    </svg>
  );
}

export function BottomNav() {
  return (
    <nav
      aria-label="하단 내비게이션"
      className={cn(
        'fixed bottom-0 inset-x-0 z-30',
        'mx-auto w-full max-w-[402px]',
        'bg-surface border-t border-border',
        // Upward soft drop shadow per DESIGN.md "Navbar separator" decision 2026-05-25.
        'shadow-[0_-2px_10px_rgba(0,0,0,0.06)]',
      )}
    >
      <ul className="flex items-center justify-around h-16">
        {TABS.map((tab) => (
          <li key={tab.id} className="flex-1 flex justify-center">
            {tab.isFab ? (
              // 새 대화 FAB — 56px black disc, white cross. NOT orange (DESIGN.md decisions log).
              <div
                aria-disabled="true"
                aria-label={tab.label}
                className="flex flex-col items-center gap-1 cursor-default"
              >
                <div className="w-14 h-14 rounded-full bg-fab flex items-center justify-center">
                  {/* #ffffff white cross — SVG stroke attr cannot reference Tailwind tokens */}
                  <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
                    <path
                      d="M10 4v12M4 10h12"
                      stroke="#ffffff"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                </div>
                <span className="text-caption-2 text-text-muted">{tab.label}</span>
              </div>
            ) : (
              <div
                aria-disabled="true"
                aria-label={tab.label}
                className="flex flex-col items-center gap-1 cursor-default w-16 h-14 justify-center"
              >
                <TabIcon id={tab.id} />
                <span className="text-caption-2 text-text-muted">{tab.label}</span>
              </div>
            )}
          </li>
        ))}
      </ul>
    </nav>
  );
}
