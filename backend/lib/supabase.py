import os

_client = None


def get_supabase():
    """Supabase service-role 클라이언트 (싱글톤, 서버 전용)."""
    global _client
    if _client is not None:
        return _client

    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError("supabase package is not installed. Run: pip install supabase") from exc

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

    _client = create_client(url, key)
    return _client
