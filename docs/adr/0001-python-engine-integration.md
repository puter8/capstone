# ADR 0001: Python 엔진 통합 방식 (ENGINE-01)

**날짜:** 2026-05-24  
**상태:** Accepted  
**작성:** 김민주 (Phase 1B)  
**소비:** 백은혜 (Phase 1C) — D+1 coordination input

---

## 배경

`ai/analyzer.py` + `ai/matrix_engine.py`로 구현된 5축 분석 엔진을 백엔드(FastAPI)에서 호출하는 방식을 결정해야 한다.  
Phase 1C(/api/chat 구현)가 이 결정을 critical input으로 기다리고 있으므로 D+1 안에 확정한다.

---

## 고려한 옵션

### 옵션 A: FastAPI에서 직접 import ✅ (선택)
```python
# backend/main.py
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from ai.analyzer import analyze_utterance
from ai.matrix_engine import compute_character, apply_ema
```

### 옵션 B: subprocess 호출
```python
result = subprocess.run(["python", "ai/analyzer.py", text], capture_output=True)
```

### 옵션 C: 별도 Python 마이크로서비스
- ai/ 를 독립 FastAPI 서버로 띄우고 HTTP 호출

### 옵션 D: TypeScript 포팅
- ai/analyzer.py 로직을 frontend/lib/ 에 TS로 재구현

---

## 결정: 옵션 A (FastAPI 직접 import)

### 근거

| 기준 | A (직접 import) | B (subprocess) | C (마이크로서비스) | D (TS 포팅) |
|------|----------------|----------------|-------------------|-------------|
| 구현 속도 | ⚡ 즉시 | 보통 | 느림 (별도 배포) | 느림 (재구현) |
| 지연(latency) | 🟢 없음 | 🟡 fork overhead | 🔴 네트워크 RTT | 🟢 없음 |
| 유지보수 | 단일 코드베이스 | 분리 | 분리 | 이중 유지보수 |
| Railway 배포 | 단일 서비스 | 단일 서비스 | 2개 서비스 | - |
| Demo deadline | ✅ 17일 충분 | ✅ | ❌ 리스크 | ❌ 리스크 |

1. **속도**: `/api/chat` 한 번 호출에 STT→분석→Gemini→TTS 파이프라인이 직렬로 실행된다. subprocess/네트워크 오버헤드 추가는 데모 지연에 직접 영향.
2. **단순성**: Railway에 단일 FastAPI 서비스로 배포. `sys.path` 한 줄로 ai/ 모듈 접근.
3. **소유권 일치**: backend/는 백은혜, ai/는 김민주+백은혜 공동 소유. 같은 프로세스에서 import하므로 인터페이스 마찰 없음.
4. **MVP 범위**: 엔진은 pure Python(외부 의존성 없음). import 안정성 문제 없음.

---

## Contract (Phase 1C 소비 기준)

### 호출 방식
```python
# backend/main.py 상단
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.analyzer import analyze_utterance
from ai.matrix_engine import compute_character, apply_ema, DEFAULT_ALPHA
```

### 함수 시그니처

```python
# ai/analyzer.py
def analyze_utterance(text: str) -> dict:
    """
    Returns:
        {
            "Formality": int,   # 0~100
            "Energy": int,      # 0~100
            "Intimacy": int,    # 0~100
            "Humor": int,       # 0~100
            "Curiosity": int,   # 0~100
        }
    """

# ai/matrix_engine.py
def compute_character(axes: dict) -> dict:
    """
    Args:
        axes: analyze_utterance() 반환값 또는 apply_ema() 반환값
    Returns:
        {
            "tone_casual": int,    # 0~100
            "energy_level": int,   # 0~100
            "humor_level": int,    # 0~100
        }
    """

def apply_ema(prev: dict, new_axes: dict, alpha: float = DEFAULT_ALPHA) -> dict:
    """
    Args:
        prev:     이전 누적 axes (세션 첫 발화면 DEFAULT_AXES로 초기화)
        new_axes: analyze_utterance() 반환값
        alpha:    0.7 (데모용, roadmap 명시)
    Returns:
        EMA 보정된 axes dict (analyze_utterance 반환값과 동일 구조)
    """

DEFAULT_ALPHA = 0.7  # 데모용 (roadmap: α=0.7)
```

### /api/chat 호출 흐름
```
STT transcript
    ↓
analyze_utterance(transcript)         → new_axes
    ↓
apply_ema(prev_axes, new_axes, 0.7)   → smoothed_axes
    ↓
compute_character(smoothed_axes)       → character (tone/energy/humor)
    ↓
[Gemini 응답 생성 + TTS + hint_ko]    (asyncio.gather)
    ↓
응답 payload: { reply, tts_audio, axes: smoothed_axes, character, hint_ko }
```

### Supabase 저장 구조
```python
# messages 테이블 axes / character JSONB
axes_json    = smoothed_axes          # 5축 int dict
character_json = character            # tone/energy/humor int dict
```

### prev_axes 관리 (세션 상태)
- 세션 첫 발화: `prev_axes = {"Formality":50, "Energy":30, "Intimacy":20, "Humor":10, "Curiosity":15}`
- 이후: Supabase messages 테이블에서 가장 최근 row의 `axes` JSONB 조회 → prev_axes로 사용
- 클라이언트가 session_id를 헤더 또는 body로 전달 → 백엔드가 DB에서 로드

---

## Contract Test

```python
# tests/test_matrix.py (기존 파일에 추가 or 참조)
from ai.analyzer import analyze_utterance
from ai.matrix_engine import compute_character, apply_ema

def test_contract_casual():
    axes = analyze_utterance("yo lol that's so wild bro!!")
    assert all(k in axes for k in ["Formality","Energy","Intimacy","Humor","Curiosity"])
    assert all(0 <= v <= 100 for v in axes.values())
    char = compute_character(axes)
    assert all(k in char for k in ["tone_casual","energy_level","humor_level"])
    assert all(0 <= v <= 100 for v in char.values())

def test_contract_formal():
    axes = analyze_utterance("I would like to formally request a thorough explanation regarding the aforementioned policy.")
    char = compute_character(axes)
    assert axes["Formality"] > 50
    assert char["tone_casual"] < 50

def test_ema_smoothing():
    prev = {"Formality":50,"Energy":30,"Intimacy":20,"Humor":10,"Curiosity":15}
    new  = {"Formality":10,"Energy":85,"Intimacy":60,"Humor":90,"Curiosity":35}
    smoothed = apply_ema(prev, new, alpha=0.7)
    # alpha=0.7: 새 발화 70% 반영
    assert abs(smoothed["Formality"] - round(0.7*10 + 0.3*50)) <= 1
```

---

## 결론

Phase 1C는 위 contract를 따라 `sys.path` 추가 후 직접 import해서 사용한다.  
엔진 코드(ai/) 수정이 필요하면 김민주에게 PR로 요청한다.

---

*Last updated: 2026-05-24*