import { ensureLogsTable } from "./db.js";

export default async function handler(req, res) {
  try {
    await ensureLogsTable();
    return res.status(200).json({ ok: true, message: "calc_logs table is ready" });
  } catch (error) {
    return res.status(500).json({ ok: false, error: String(error?.message ?? error) });
  }
}
