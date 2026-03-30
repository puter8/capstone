import { ensureLogsTable, getSql } from "./db.js";

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");

  const parsedLimit = parseInt(req.query.limit ?? "50", 10);
  const limit = Number.isNaN(parsedLimit)
    ? 50
    : Math.min(Math.max(parsedLimit, 1), 200);

  try {
    await ensureLogsTable();
    const sql = getSql();
    const rows = await sql`
      SELECT id, ts, a, b, op, result, error
      FROM calc_logs
      ORDER BY id DESC
      LIMIT ${limit}
    `;

    const payload = rows.map((row) => ({
      id: row.id,
      ts: row.ts instanceof Date ? row.ts.toISOString() : row.ts,
      a: row.a,
      b: row.b,
      op: row.op,
      result: row.result,
      error: row.error,
    }));

    return res.status(200).json(payload);
  } catch (error) {
    return res.status(500).json({ error: String(error?.message ?? error) });
  }
}
