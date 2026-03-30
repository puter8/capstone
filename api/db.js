import postgres from "postgres";

const connectionString = process.env.DATABASE_URL;

const sql = connectionString
  ? postgres(connectionString, {
      ssl: "require",
    })
  : null;

let logsTableEnsured = false;

export function getSql() {
  if (!sql) {
    throw new Error("DATABASE_URL is not set");
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
