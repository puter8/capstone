-- Phase 1C: sessions + messages tables for Pally conversation history
-- Backend accesses via service_role key (bypasses RLS).
-- v2: add per-user auth.uid()-based policies when Supabase Auth is introduced.

CREATE TABLE IF NOT EXISTS sessions (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    character_name TEXT        NOT NULL DEFAULT 'Pally',
    level          TEXT        NOT NULL DEFAULT 'B1'
                               CHECK (level IN ('A2', 'B1', 'B2', 'C1')),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at       TIMESTAMPTZ
);

ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS messages (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID        NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        TEXT        NOT NULL CHECK (role IN ('user', 'pally')),
    transcript  TEXT        NOT NULL,
    axes        JSONB,
    character   JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS messages_session_id_created_at
    ON messages (session_id, created_at);
