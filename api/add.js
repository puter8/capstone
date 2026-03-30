import { ensureLogsTable, getSql } from "./db.js";

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");

  const a = parseFloat(req.query.a);
  const b = parseFloat(req.query.b);

  if (isNaN(a) || isNaN(b)) {
    return res.status(400).json({ error: "숫자 두 개를 입력하세요." });
  }

  const result = a + b;

  try {
    await ensureLogsTable();
    const sql = getSql();
    await sql`
      INSERT INTO calc_logs (a, b, op, result, error)
      VALUES (${a}, ${b}, ${"add"}, ${result}, ${null})
    `;
  } catch (error) {
    // Keep calculator functionality even if DB logging fails.
    console.error("Failed to save log:", error);
  }

  res.status(200).json({ result });
}
