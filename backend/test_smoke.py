# -*- coding: utf-8 -*-
"""
CI smoke test — 시크릿/실서비스 없이 도는 최소 검증.

목적:
- 앱이 import 되는지 (문법 에러, import 에러, 정의 안 된 참조 등)
- 핵심 라우트가 사라지지 않았는지 (PR #33 처럼 머지 사고로 엔드포인트가
  조용히 삭제되는 것을 CI 단계에서 차단)

실제 STT/Gemini/TTS/Supabase E2E 는 시크릿·비용 때문에 여기서 돌리지 않는다.
그건 로컬/별도 통합 테스트에서 실제 서비스로 검증한다.
"""
import main


def test_app_imports():
    assert main.app is not None


def test_core_routes_present():
    paths = {getattr(r, "path", None) for r in main.app.routes}
    # 절대 사라지면 안 되는 핵심 비즈니스 엔드포인트. 새 라우트 추가는 자유.
    required = {
        "/api/health",
        "/api/onboarding",
        "/api/profile",
        "/api/conversations",
        "/api/conversations/{conversation_id}/turns",
    }
    missing = required - paths
    assert not missing, f"core routes missing (merge clobber?): {sorted(missing)}"
