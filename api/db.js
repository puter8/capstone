import postgres from "postgres";

const connectionStringFromUrlVars =
  process.env.DATABASE_URL ||
  process.env.POSTGRES_URL ||
  process.env.POSTGRES_PRISMA_URL ||
  process.env.POSTGRES_URL_NON_POOLING ||
  process.env.DATABASE_URL_UNPOOLED;

const pgUser = process.env.PGUSER || process.env.POSTGRES_USER;
const pgPassword = process.env.PGPASSWORD || process.env.POSTGRES_PASSWORD;
const pgHost = process.env.PGHOST || process.env.POSTGRES_HOST;
const pgPort = process.env.PGPORT || process.env.POSTGRES_PORT || "5432";
const pgDatabase = process.env.PGDATABASE || process.env.POSTGRES_DATABASE;

const connectionStringFromParts =
  pgUser && pgPassword && pgHost && pgDatabase
    ? `postgresql://${encodeURIComponent(pgUser)}:${encodeURIComponent(
        pgPassword
      )}@${pgHost}:${pgPort}/${pgDatabase}?sslmode=require`
    : null;

const connectionString = connectionStringFromUrlVars || connectionStringFromParts;

const sql = connectionString
  ? postgres(connectionString, {
      ssl: "require",
    })
  : null;

let logsTableEnsured = false;

export function getSql() {
  if (!sql) {
    throw new Error("No Postgres connection env var is set (URL or PG parts)");
  }
  return sql;
}

export async function ensureLogsTable() {
  if (logsTableEnsured) {
    return;
  }

  const client = getSql();
  await client`
    CREATE TABLE IF NOT EXISTS calc_logs (
      id SERIAL PRIMARY KEY,
      ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      a DOUBLE PRECISION NOT NULL,
      b DOUBLE PRECISION NOT NULL,
      op TEXT NOT NULL,
      result DOUBLE PRECISION,
      error TEXT
    )
  `;

  logsTableEnsured = true;
}
