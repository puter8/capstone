# Final Report Workspace

이 폴더는 Pally 최종 보고서 작성용 작업 공간이다. 초기 기획 문서와 최종 구현 결과가 섞여 있으므로, 제출용 문장은 이 파일과 `final-report-draft.md`를 기준으로 정리한다.

## 작성 기준

- 최종 제품명: Pally — CharaShift MVP
- 팀: 퓨터(puter8)
- 트랙: 이화여대 캡스톤 디자인 산학 트랙
- 데모일: 2026-06-07
- 최종 MVP 핵심: 사용자 영어 발화 스타일을 5축으로 분석하고, CHARACTER MATRIX를 통해 Pally의 외형과 말투를 실시간 변화시키는 모바일 웹 영어 회화 서비스
- 최종 구현 스택: Next.js 14, FastAPI, Google Cloud STT/TTS, Gemini 2.5 Flash, Supabase, Canvas2D Superformula, Vercel, Railway

## 문서 사용 순서

1. `final-report-draft.md`
   - 최종 보고서 본문 초안.
   - 바로 복사해서 제출 양식에 맞게 다듬는 용도.

2. `../../README.md`
   - 구현 완료 범위, 데모 URL, 스크린샷, 폴더 구조, 기술 설명.
   - 최종 구현 기준으로 가장 업데이트된 공개 설명 문서.

3. `../../.planning/ROADMAP.md`
   - Phase별 개발 계획과 진행 상태의 source of truth.
   - Phase 0, 1A, 1B, 1C, 2 구조를 설명할 때 사용.

4. `../../.planning/PROJECT.md`
   - 프로젝트 핵심 가치, 요구사항, 제약조건, 주요 의사결정.

5. `../adr/0001-python-engine-integration.md`
   - Python 5축 엔진을 FastAPI에서 직접 import하기로 한 근거.

6. 기존 기획 문서
   - `Project Briefs.MD`, `Ideation.MD`, `Implementation_Plan.MD`, `Design_Document.MD`
   - 문제 정의, 타깃 사용자, 초기 아이디어 설명에 사용.
   - 단, 일부 초기 문서에는 GPT-4o, Reddit PRAW, pgvector RAG 등 최종 MVP에서 제외되거나 변경된 내용이 있으므로 제출 전 최신 구현 기준으로 수정해야 한다.

## 최종 보고서에 넣을 핵심 서사

Pally는 기존 영어 회화 서비스의 획일적인 응답 문제를 해결하기 위해, 사용자의 발화 스타일을 정량화하고 이를 AI 캐릭터의 성격과 시각 상태에 반영한다. 사용자는 모바일 웹에서 영어로 말하고, 시스템은 음성을 텍스트로 변환한 뒤 5축 점수(Formality, Energy, Intimacy, Humor, Curiosity)를 계산한다. 이 점수는 CHARACTER MATRIX와 EMA 보정을 거쳐 Pally의 말투, 에너지, 유머 수준 및 Canvas2D 캐릭터 형태에 반영된다.

최종 MVP는 외부 LLM 호출 자체보다, 발화 스타일을 구조화된 수치로 변환하고 이를 캐릭터 상태로 다시 변환하는 자체 엔진을 핵심 기술로 삼는다. Gemini는 응답 생성과 한국어 인라인 힌트에 사용되고, 음성 입출력은 Google Cloud STT/TTS로 처리한다. 대화 기록과 분석 결과는 Supabase에 저장되며, 프론트엔드는 Vercel, 백엔드는 Railway에 배포된다.

## 제출 전 확인할 것

- 데모 URL이 현재 접속 가능한지 확인
- README의 스크린샷 3개가 실제 파일로 존재하는지 확인
- 최종 보고서에서 GPT-4o, OpenAI, Reddit RAG를 현재 구현 기능처럼 쓰지 않기
- "향후 확장"과 "현재 구현"을 분리해서 쓰기
- 팀원 역할을 최신 구현 기준으로 맞추기
