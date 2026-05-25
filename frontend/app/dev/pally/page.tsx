'use client';

import { useState, useMemo } from 'react';
import PallyCanvas from '@/components/pally/PallyCanvas';
import { Axes, DEFAULT_AXES } from '@/lib/types/character';

function computeCharacter(axes: Axes) {
  const W = [
    [-0.45, 0.10, 0.15, 0.15, 0.00],
    [ 0.05, 0.40, 0.15, 0.10, 0.10],
    [ 0.00, 0.05, 0.10, 0.50, 0.05],
  ];
  const BIAS = [50, 20, 10];
  const v = [axes.Formality, axes.Energy, axes.Intimacy, axes.Humor, axes.Curiosity];
  const [tone, energy, humor] = W.map((row, i) =>
    Math.max(0, Math.min(100, Math.round(row.reduce((s, w, j) => s + w * v[j], 0) + BIAS[i])))
  );
  return { tone_casual: tone, energy_level: energy, humor_level: humor };
}

const AXIS_COLORS: Record<keyof Axes, string> = {
  Humor: '#a78bfa', Formality: '#60a5fa', Energy: '#fb923c',
  Intimacy: '#f472b6', Curiosity: '#34d399',
};
const AXIS_META: Record<keyof Axes, { low: string; high: string; visual: string }> = {
  Humor:     { low: '진지',   high: '유머/밈',  visual: '뾰족함' },
  Formality: { low: '슬랭',   high: '격식체',  visual: '모서리 둥글기' },
  Energy:    { low: '차분',   high: '활발',    visual: '눈 타입' },
  Intimacy:  { low: '거리감', high: '친밀',    visual: '몸 색상' },
  Curiosity: { low: '선언적', high: '탐구적',  visual: '애니메이션 속도' },
};

const PRESETS = {
  casual:  { Formality: 10, Energy: 80, Intimacy: 75, Humor: 85, Curiosity: 40 },
  formal:  { Formality: 90, Energy: 25, Intimacy: 15, Humor:  5, Curiosity: 55 },
  curious: { Formality: 45, Energy: 60, Intimacy: 50, Humor: 30, Curiosity: 90 },
  neutral: DEFAULT_AXES,
} as const;

// tier 라벨
function tierLabel(axis: keyof Axes, v: number): string {
  const t = v <= 33 ? 0 : v <= 66 ? 1 : 2;
  const map: Record<keyof Axes, string[]> = {
    Humor:     ['사각형', '중간별', '날카로운별'],
    Formality: ['각짐(r=0)', '둥글(r=40)', '원(r=100)'],
    Energy:    ['eye1 점', 'eye2 검정', 'eye3 노랑'],
    Intimacy:  ['파랑', '노랑', '빨강'],
    Curiosity: ['느린 bob', '중간 bounce', '빠른 wiggle'],
  };
  return map[axis][t];
}

export default function PallyDevPage() {
  const [axes, setAxes] = useState<Axes>(DEFAULT_AXES);
  const [thinking, setThinking] = useState(false);
  const computed = useMemo(() => computeCharacter(axes), [axes]);

  return (
    <div style={{
      minHeight: '100vh', background: '#0f0f13', color: '#e8e8f0',
      fontFamily: "'DM Mono','Fira Code',monospace",
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '24px 16px 48px',
    }}>
      <div style={{ textAlign: 'center', marginBottom: 28 }}>
        <div style={{ fontSize: 10, letterSpacing: 4, color: '#6b6b8a', textTransform: 'uppercase', marginBottom: 6 }}>
          Phase 1B · Dev
        </div>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Pally Canvas Debugger</h1>
        <p style={{ fontSize: 12, color: '#6b6b8a', marginTop: 4 }}>
          슬라이더로 5축 조작 → 3단계 구간 점프 확인
        </p>
      </div>

      <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', justifyContent: 'center', width: '100%', maxWidth: 860 }}>

        {/* 왼쪽: Pally */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
          <div style={{ background: '#1a1a24', borderRadius: 24, border: '1px solid #2a2a3a', padding: 24 }}>
            <PallyCanvas axes={axes}  size={210} />
          </div>

          <button onClick={() => setThinking(t => !t)} style={{
            background: thinking ? '#7c3aed' : '#2a2a3a', border: 'none', borderRadius: 10,
            padding: '8px 20px', color: '#e8e8f0', fontSize: 13, cursor: 'pointer', fontFamily: 'inherit',
          }}>
            {thinking ? '💭 Thinking...' : '💬 Idle'}
          </button>

          {/* 프리셋 */}
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'center' }}>
            {(Object.keys(PRESETS) as (keyof typeof PRESETS)[]).map(name => (
              <button key={name} onClick={() => setAxes({ ...PRESETS[name] })} style={{
                background: '#1a1a24', border: '1px solid #2a2a3a', borderRadius: 8,
                padding: '5px 12px', color: '#a0a0c0', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit',
              }}>{name}</button>
            ))}
          </div>

          {/* matrix_engine 출력 */}
          <div style={{ background: '#1a1a24', border: '1px solid #2a2a3a', borderRadius: 12, padding: '12px 16px', fontSize: 11, lineHeight: 2, minWidth: 210 }}>
            <div style={{ color: '#6b6b8a', fontSize: 10, letterSpacing: 2, textTransform: 'uppercase', marginBottom: 4 }}>matrix_engine output</div>
            {[
              { k: 'tone_casual',  v: computed.tone_casual,  c: '#a78bfa' },
              { k: 'energy_level', v: computed.energy_level, c: '#fb923c' },
              { k: 'humor_level',  v: computed.humor_level,  c: '#34d399' },
            ].map(({ k, v, c }) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <span style={{ color: '#6b6b8a' }}>{k}</span>
                <span style={{ color: c, fontWeight: 700 }}>{v}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 오른쪽: 슬라이더 */}
        <div style={{ flex: 1, minWidth: 270, display: 'flex', flexDirection: 'column', gap: 22 }}>
          {(Object.keys(axes) as (keyof Axes)[]).map(axis => {
            const v = axes[axis];
            const t = v <= 33 ? 0 : v <= 66 ? 1 : 2;
            
            return (
              <div key={axis}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
                  <div>
                    <span style={{ fontWeight: 700, color: AXIS_COLORS[axis], fontSize: 14 }}>{axis}</span>
                    <span style={{ fontSize: 10, color: '#6b6b8a', marginLeft: 8 }}>{AXIS_META[axis].visual}</span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: AXIS_COLORS[axis] }}>{v}</span>
                    <span style={{ fontSize: 10, color: AXIS_COLORS[axis], marginLeft: 6,
                      background: `${AXIS_COLORS[axis]}22`, borderRadius: 4, padding: '1px 6px' }}>
                      {tierLabel(axis, v)}
                    </span>
                  </div>
                </div>

                {/* 3구간 표시 바 */}
                <div style={{ display: 'flex', gap: 3, marginBottom: 6 }}>
                  {[0,1,2].map(i => (
                    <div key={i} style={{
                      flex: 1, height: 3, borderRadius: 2,
                      background: i === t ? AXIS_COLORS[axis] : '#2a2a3a',
                      transition: 'background 0.15s',
                    }} />
                  ))}
                </div>

                <input type="range" min={0} max={100} value={v}
                  onChange={e => setAxes(prev => ({ ...prev, [axis]: Number(e.target.value) }))}
                  style={{ width: '100%', accentColor: AXIS_COLORS[axis], cursor: 'pointer' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#4a4a6a', marginTop: 2 }}>
                  <span>{AXIS_META[axis].low}</span>
                  <span style={{ color: '#3a3a5a' }}>│ 33 │ 66 │</span>
                  <span>{AXIS_META[axis].high}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
