export default function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");

  const a = parseFloat(req.query.a);
  const b = parseFloat(req.query.b);

  if (isNaN(a) || isNaN(b)) {
    return res.status(400).json({ error: "숫자 두 개를 입력하세요." });
  }

  res.status(200).json({ result: a + b });
}
