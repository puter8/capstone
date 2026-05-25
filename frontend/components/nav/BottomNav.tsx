'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

// GNB: black pill bar + protruding FAB. Icons are tinted via CSS mask-image
// so a single SVG can render white (idle) or #FFB84A (active route).

const ACTIVE_COLOR = '#FFB84A';
const IDLE_COLOR = '#ffffff';
const ICON_SIZE = 30;

const SIDE_TABS = [
  { id: 'home', label: '홈', side: 'left', href: '/home' },
  { id: 'history', label: '학습', side: 'left', href: '/history' },
  { id: 'ranking', label: '랭킹', side: 'right', href: '/ranking' },
  { id: 'my', label: '내 정보', side: 'right', href: '/my' },
] as const;

function TabIcon({ id, active }: { id: string; active: boolean }) {
  // CSS mask-image: the SVG defines the shape (alpha channel),
  // background-color paints it. Lets one file render in multiple colors.
  const url = `url(/icons/${id}.svg)`;
  return (
    <span
      aria-hidden
      className="inline-block"
      style={{
        width: ICON_SIZE,
        height: ICON_SIZE,
        backgroundColor: active ? ACTIVE_COLOR : IDLE_COLOR,
        WebkitMaskImage: url,
        maskImage: url,
        WebkitMaskRepeat: 'no-repeat',
        maskRepeat: 'no-repeat',
        WebkitMaskPosition: 'center',
        maskPosition: 'center',
        WebkitMaskSize: 'contain',
        maskSize: 'contain',
      }}
    />
  );
}

export function BottomNav() {
  const pathname = usePathname();

  const renderTab = (tab: (typeof SIDE_TABS)[number]) => {
    const active = pathname === tab.href;
    return (
      <Link
        key={tab.id}
        href={tab.href}
        aria-label={tab.label}
        aria-current={active ? 'page' : undefined}
        className="w-12 h-12 flex items-center justify-center"
      >
        <TabIcon id={tab.id} active={active} />
      </Link>
    );
  };

  return (
    <nav
      aria-label="하단 내비게이션"
      className="absolute bottom-[10px] left-[10px] right-[10px] z-30 h-[120px]"
    >
      {/* Black rounded bar */}
      <div
        className={cn(
          'absolute inset-x-0 bottom-0 h-[80px]',
          'bg-fab rounded-[40px]',
          'shadow-[0_4px_14px_rgba(0,0,0,0.18)]',
        )}
        aria-hidden
      />

      {/* Side icons (2 each) layered on the bar */}
      <ul className="absolute inset-x-0 bottom-0 h-[80px] flex items-center px-2">
        <li className="flex flex-1 justify-around">
          {SIDE_TABS.filter((t) => t.side === 'left').map(renderTab)}
        </li>
        {/* Spacer where FAB sits */}
        <li className="w-[96px]" aria-hidden />
        <li className="flex flex-1 justify-around">
          {SIDE_TABS.filter((t) => t.side === 'right').map(renderTab)}
        </li>
      </ul>

      {/* FAB: black ring → white disc → black plus */}
      <button
        type="button"
        aria-label="새 대화"
        aria-disabled="true"
        disabled
        className={cn(
          'absolute left-1/2 -translate-x-1/2 top-[14px]',
          'w-[80px] h-[80px] rounded-full bg-fab',
          'flex items-center justify-center',
          'shadow-[0_3px_10px_rgba(0,0,0,0.2)]',
          'cursor-default',
        )}
      >
        <span className="w-[64px] h-[64px] rounded-full bg-surface-raised flex items-center justify-center">
          <svg width="44" height="44" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M12 5v14M5 12h14"
              stroke="#1a1a1a"
              strokeWidth="2.2"
              strokeLinecap="round"
            />
          </svg>
        </span>
      </button>
    </nav>
  );
}
