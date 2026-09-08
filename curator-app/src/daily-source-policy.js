// Operational search policy; separate from the scientific four-part protocol.
export const DAILY_PROTOCOL = "CILE-DAILY-v3";
export const DAILY_SOURCES = Object.freeze(["Exa"]);

export function queryManifestProblem(manifest) {
  if (!manifest || manifest.protocol_version !== DAILY_PROTOCOL || !Array.isArray(manifest.queries) || manifest.queries.length !== 7) return "approved_query_manifest_required";
  const windows = new Set(), ids = new Set();
  for (const q of manifest.queries) {
    if (!q || !DAILY_SOURCES.includes(q.provider) || !/^W[1-7]$/.test(q.window)
      || typeof q.text !== "string" || !q.text.trim() || q.text.length > 2000
      || typeof q.query_id !== "string" || !/^[A-Za-z0-9-]{3,60}$/.test(q.query_id)) return "invalid_query_manifest";
    windows.add(q.window); ids.add(q.query_id);
  }
  return windows.size !== 7 || ids.size !== 7 ? "duplicate_or_missing_query" : null;
}
