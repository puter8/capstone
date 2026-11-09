# Pally 브랜드 팔레트 탐색

2026-10-15 기준 사용자 결정과 로컬 HTML 시안 기록.

**최신 결정:** 메인 라일락 퍼플 `#B7B5F2` + 서브 버터 옐로 `#F2DFA0` 확정. 아래 후보 표는 결정 전 탐색 이력이다. 새 시스템은 사용자 지정 파일 [new-design.md](../../new-design.md)에 저장하며 기존 `DESIGN.md`는 유지한다. 폰트·컴포넌트 세부 규격은 새 설계안이다.

- 어두운 앱 배경을 사용한다. How We Feel의 색감·타이포 분위기와 Talkpal의 UI/UX를 참고한다. 기존 Pally 화면 스타일은 새 디자인의 기준으로 사용하지 않는다.
- 팔리 캐릭터는 기존 모양과 색상 모두 유지한다. 홈 시안은 `frontend/public/pally/pally-character.svg` 원본을 수정 없이 포함한다.
- Claude를 연상시키는 별표 장식은 사용하지 않는다. 팔리 원본의 눈 속 무늬는 캐릭터의 일부로 유지한다.
- 탐색 당시 세 팔레트는 비교 후보였으며, 이후 퍼플 + 버터 옐로로 확정했다.

| 후보 | 메인 | 서브 | 배경 |
| --- | --- | --- | --- |
| 살구 + 민트 | `#F6A480` | `#AAD8CB` | `#171716` |
| 버터 옐로 + 소프트 블루 | `#EFD780` | `#A9BDEA` | `#181817` |
| 라일락 + 라임 | `#B7B5F2` | `#D4E4A0` | `#17171B` |

홈에서 메인은 마이크·선택된 메뉴, 서브는 보조 문구·키보드 포커스에 적용했다. 캐릭터에는 브랜드 팔레트를 적용하지 않는다. 서체는 로컬 시스템 서체를 사용한 분위기 제안이며 레퍼런스 앱의 실제 서체로 확정한 것이 아니다.

- 팔레트·온보딩: `output/brand-exploration/pally-onboarding-palettes.html`
- 홈 비교: `output/brand-exploration/pally-home-palettes.html`
- 미리보기: `http://127.0.0.1:8765/pally-home-palettes.html`

홈 HTML은 시각 비교용이다. 마이크 클릭은 세 안의 말하기 상태만 동기화하며 실제 녹음·저장·화면 이동을 수행하지 않는다. 제품 코드나 배포에는 반영하지 않았다.

## 후속 탐색 — 퍼플의 서브 컬러

사용자가 퍼플 방향을 선호하고 라임 대신 다른 서브 컬러를 요청했다. 메인 `#B7B5F2`, 배경 `#17171B`, 팔리 캐릭터 원본을 고정해 아래 세 조합을 비교했다. 이후 추가 조사에서 제안한 버터 옐로를 최종 선택했다.

| 서브 후보 | 색상 | 인상 |
| --- | --- | --- |
| 로즈 | `#E5B6C7` | 포근하고 다정함 |
| 살구 | `#EDC1A5` | 차분한 퍼플과 따뜻한 캐릭터를 연결 — 디자인 추천안 |
| 소프트 블루 | `#A8CFE0` | 맑고 차분함 |

비교 시안: `output/brand-exploration/pally-purple-secondary.html`. 서브색은 보조 문구, 해당 문구의 옅은 바탕, 마이크 주변의 옅은 링, 키보드 포커스에 적용했다. 기존 비교 시안은 탐색 이력으로 유지한다.

## 새 시스템 산출물

- 기준 문서: `new-design.md`
- 원본 CSS 토큰: `docs/design/pally.tokens.css`
- 실제 폰트·컴포넌트 가이드: `output/brand-exploration/pally-design-system.html`
- 확정 색상 적용 예시: `pally-home-final.html`, `pally-onboarding-final.html` (위 가이드와 같은 폴더)
- Pretendard는 기존 설치 자산, Fraunces는 Google Fonts 공식 배포본을 미리보기 안에 포함했다. 라이선스도 함께 보존한다.
- 제품 코드·Figma 파일·배포는 이번 범위에서 변경하지 않는다.
