# Pally — Self Demo 시연 요령

> 데모 URL: **https://capstone-eight-virid.vercel.app/home**
>
> 반드시 **모바일 브라우저** 또는 **Chrome DevTools 모바일 뷰 (폭 390px)** 로 열어주세요.

---

## 사전 준비 (30초)

1. 위 URL을 모바일 또는 Chrome DevTools → 모바일 뷰로 열기
2. 브라우저 마이크 권한 허용 (첫 녹음 시 팝업 → 허용)
3. 이어폰 또는 스피커 준비 (Pally TTS 음성 재생됨)

---

## Step 1 — 새 채팅 화면 확인 (10초)

**보이는 것**
- "오늘은 어떤 이야기를 해볼까요?" 텍스트
- Pally 캐릭터 (초기 상태)
- 주황색 마이크 버튼

**설명 포인트**
> "발화 전 Pally의 초기 외형입니다. 대화할수록 사용자 스타일에 맞게 변화합니다."

---

## Step 2 — 첫 발화 (20초)

1. 주황 마이크 버튼 탭
2. 마이크 권한 허용 (최초 1회)
3. 아래 문장 중 하나를 영어로 말하기

**추천 발화 대사** — 핑크+별 변환 시나리오 (Intimacy↑ · Humor↑)
```
"OMG you're literally the funniest, I love you so much bestie, this is the best thing ever lmaoooo!"
```
또는 (일반)
```
"Oh my gosh, I just had ramen for lunch and it was so spicy!"
```
또는
```
"I'm so excited, I just got tickets to a concert!"
```

**보이는 것**: 말풍선에 **Listening...** 표시, 빨간 Stop 버튼

4. 말이 끝나면 빨간 Stop 버튼 탭

---

## Step 3 — Thinking 상태 (5~10초 자동)

**보이는 것**
- 말풍선: `YOU / [내가 한 말]` + **Thinking...**
- 주황 마이크 버튼 (반투명, 비활성)

**설명 포인트**
> "STT → 5축 분석 → Gemini 응답 생성 중입니다."

---

## Step 4 — Pally 응답 + TTS 재생 (10~15초)

**보이는 것**
- 말풍선: `YOU / [내 발화]` + `Pally / [응답]`
- Pally TTS 음성 자동 재생

**설명 포인트**
> "Gemini 2.5 Flash가 사용자 발화 스타일을 분석해 Pally 성격에 맞는 응답을 생성합니다."
> "문법 실수가 있으면 Pally가 자연스럽게 교정 표현을 사용합니다."

---

## Step 5 — 두 번째 발화 (20초)

TTS 재생 완료 후 주황 마이크 버튼 탭

**추천 발화 대사**
```
"Yeah I love spicy food! I can eat it every single day!"
```
또는
```
"Have you ever tried Korean ramen? It's really amazing."
```

**보이는 것**: 말풍선에 `Pally / [이전 응답]` + **Listening...**

Stop 버튼 탭 → Thinking → 두 번째 Pally 응답 재생

---

## Step 6 — 히스토리 보기 (선택, 10초)

말풍선 우측 하단 **v 버튼** 탭

**보이는 것**: 전체 대화 히스토리 스크롤 뷰

^ 버튼으로 닫기

---

## Step 7 — 세션 종료 + Pally 변화 확인 (10초)

좌상단 **X 버튼** 탭

**보이는 것**
- Pally 캐릭터 외형 변화 (색상·형태·눈 타입)
- 새 채팅 화면으로 초기화

**설명 포인트**
> "세션 동안 누적된 5축 점수(Formality·Energy·Intimacy·Humor·Curiosity)가 CHARACTER MATRIX를 통해 Pally 외형에 반영됩니다."
> "캐주얼하고 에너지 넘치는 발화 → 밝은 색 + 뾰족한 형태 / 격식체 → 둥글고 차분한 형태"

---

## 전체 소요 시간

| 구간 | 시간 |
|------|------|
| 사전 준비 | 30초 |
| Step 1~4 (1턴) | 약 1분 |
| Step 5~6 (2턴) | 약 1분 |
| Step 7 (종료) | 10초 |
| **합계** | **약 2분 30초** |

---

## 문법 교정 시연용 발화 (선택)

의도적으로 틀린 표현 → Pally가 자연스럽게 교정

| 틀린 발화 | Pally 교정 포인트 |
|---------|-----------------|
| `"I is so happy today!"` | `you're` 또는 `you are` 사용 |
| `"Yesterday I go to the park."` | `went` 사용 |
| `"I very boring now."` | `"you're bored?"` 로 응답 |
| `"Yesterday I go to the store and buyed the most funniest snack ever omg!"` | `went`, `bought` 교정; 슬랭(omg) 그대로 유지 — 핑크+별 시나리오 발화 |

---

## 핑크+별 변환 집중 시연 (선택 · 약 3분)

Intimacy·Humor 축을 집중적으로 올려 **핑크 색상 + 별(뾰족) 형태** Pally를 만드는 시나리오.
친근하고 유머러스한 발화를 4턴 연속 → X 세션 종료 시 변환 확인.

**정상 발화 (2턴에 사용)**
```
"OMG you're literally the funniest, I love you so much bestie, this is the best thing ever lmaoooo!"
```

**문법 교정 포함 발화 (나머지 2턴에 사용)**
```
"Yesterday I go to the store and buyed the most funniest snack ever omg!"
```

> Intimacy·Humor가 기본값(20/10)에서 크게 상승 → X 버튼 세션 종료 → 핑크+별 Pally 공개

---

## 트러블슈팅

| 증상 | 해결 |
|------|------|
| "Failed to fetch" 오류 | 네트워크 확인 후 새로고침 |
| TTS 소리 안 남 | 기기 볼륨 확인 / 이어폰 연결 확인 |
| 마이크 버튼 반응 없음 | 브라우저 마이크 권한 허용 확인 |
| STT 결과가 비어있음 | 조용한 환경에서 다시 시도 |
