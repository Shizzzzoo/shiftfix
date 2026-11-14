export function safeCell(v: unknown) {
  const s = String(v ?? "");
  return /^[\s]*[=+\-@\t\r]/.test(s) ? "'" + s : s;
}
export function csvText(rows: Record<string, unknown>[], columns: string[]) {
  return (
    "\ufeff" +
    [
      columns,
      ...rows.map((r) =>
        columns.map((c) =>
          safeCell(typeof r[c] === "object" ? JSON.stringify(r[c]) : r[c]),
        ),
      ),
    ]
      .map((row) =>
        row
          .map((v) => '"' + String(v ?? "").replaceAll('"', '""') + '"')
          .join(","),
      )
      .join("\r\n")
  );
}
export function downloadCsv(
  name: string,
  rows: Record<string, unknown>[],
  columns: string[],
) {
  const url = URL.createObjectURL(
    new Blob([csvText(rows, columns)], { type: "text/csv;charset=utf-8" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name + ".csv";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function parseCsv(text: string) {
  if (text.length > 1024 * 1024) throw Error("CSV must be smaller than 1 MB.");
  let rows: string[][] = [],
    row: string[] = [],
    cell = "",
    quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      if (quoted && text[i + 1] === '"') {
        cell += '"';
        i++;
      } else quoted = !quoted;
    } else if (c === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((c === "\n" || c === "\r") && !quoted) {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cell);
      if (row.some((v) => v.trim())) rows.push(row);
      row = [];
      cell = "";
    } else cell += c;
  }
  if (quoted) throw Error("CSV contains an unclosed quoted field.");
  row.push(cell);
  if (row.some((v) => v.trim())) rows.push(row);
  if (rows.length > 101) throw Error("Import at most 100 data rows.");
  if (!rows.length) throw Error("CSV is empty.");
  const headers = rows.shift()!.map((s) => s.replace(/^\ufeff/, "").trim());
  if (new Set(headers).size !== headers.length)
    throw Error("Duplicate column names.");
  if (
    headers.some((h) => ["__proto__", "constructor", "prototype"].includes(h))
  )
    throw Error("Invalid column name.");
  return rows.map((r, i) => {
    if (r.length !== headers.length)
      throw Error(`Row ${i + 2} has the wrong number of columns.`);
    return Object.fromEntries(headers.map((h, j) => [h, r[j].trim()]));
  });
}
