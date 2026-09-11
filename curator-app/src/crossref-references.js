/* Derive bounded outgoing DOI observations only from an already retained Crossref snapshot.
   This module performs no network requests and never creates review members. */
import {canonicalJson, sha256} from './review-v2.js';
const MAX_ENTRIES = 20000, PAGE = 100;
const statement = (db, sql, ...values) => db.prepare(sql).bind(...values);
const fail = code => {const error = new Error(code); error.code = code; throw error;};
const normal = value => String(value || '').trim().replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, '').toLowerCase();
const valid = value => typeof value === 'string' && /^10\.\d{4,9}\/\S+$/.test(value) && value.length <= 512;

export function referenceSnapshot(message, expectedDoi) {
  if (!message || normal(message.DOI) !== normal(expectedDoi) || !valid(normal(expectedDoi))) fail('crossref_reference_identity_conflict');
  if (message.reference !== undefined && !Array.isArray(message.reference)) fail('crossref_reference_payload_invalid');
  const references = message.reference || [];
  if (references.length > MAX_ENTRIES) fail('crossref_reference_payload_limit');
  const declared = Number.isSafeInteger(message['reference-count']) && message['reference-count'] >= 0 ? message['reference-count'] : null;
  const dois = references.map(ref => ref && typeof ref === 'object' && typeof ref.DOI === 'string' ? normal(ref.DOI) : null)
    .map(doi => valid(doi) ? doi : null);
  return {dois, declared, returned: references.length, has_list: Array.isArray(message.reference),
    unresolved: dois.filter(doi => doi === null).length};
}

export async function retainedCrossrefReferences(env, target, checkpoint, now) {
  const db = env.REVIEW_DB, record = JSON.parse(target.record_json);
  const source = checkpoint?.source_id ? await statement(db,
    "SELECT * FROM enrichment_sources WHERE source_id=? AND target_id=? AND input_sha256=? AND provider='Crossref' AND evidence_kind='metadata'",
    checkpoint.source_id, target.target_id, target.input_sha256).first() : await statement(db,
    "SELECT * FROM enrichment_sources WHERE target_id=? AND input_sha256=? AND provider='Crossref' AND evidence_kind='metadata' ORDER BY observed_at DESC,source_id DESC LIMIT 1",
    target.target_id, target.input_sha256).first();
  if (!source) {
    if (checkpoint?.source_id) fail('crossref_reference_source_unavailable');
    return null; // Other citation providers may continue; do not fetch unapproved replacements.
  }
  const object = await env.REVIEW_EVIDENCE.get(source.storage_key);
  if (!object) fail('crossref_reference_source_unavailable');
  const text = await object.text();
  if (await sha256(text) !== source.content_sha256) fail('crossref_reference_source_integrity');
  let message;
  try {message = JSON.parse(text);} catch {fail('crossref_reference_payload_invalid');}
  const parsed = referenceSnapshot(message, record.doi);
  const offset = checkpoint?.offset ?? 0;
  if (!Number.isSafeInteger(offset) || offset < 0 || offset > parsed.returned) fail('crossref_reference_cursor_invalid');
  const end = Math.min(offset + PAGE, parsed.returned), done = end === parsed.returned;
  const snapshot = 'crossref:' + source.source_id, observed = new Date(now).toISOString();
  const citing = 'doi:' + normal(record.doi), statements = [];
  const part = [...new Set(parsed.dois.slice(offset, end).filter(Boolean))];
  for (const doi of part) {
    const cited = 'doi:' + doi;
    const id = await sha256(canonicalJson([target.target_id,'Crossref','outgoing',citing,cited,snapshot]));
    statements.push(statement(db, 'INSERT OR IGNORE INTO enrichment_citation_observations VALUES (?,?,?,?,?,?,?,?,?,?)',
      id, target.target_id, target.input_sha256, 'Crossref', 'outgoing', citing, cited, snapshot, source.source_url, observed));
  }
  // Partial covers unresolved items or an unconfirmed declared count even when this list is exhausted.
  const status = !parsed.has_list ? 'not_returned' : done && parsed.unresolved === 0 && parsed.declared === parsed.returned ? 'provider_complete' : 'partial';
  const coverageId = await sha256(canonicalJson([target.target_id,snapshot,offset,end,status]));
  statements.push(statement(db, 'INSERT OR IGNORE INTO enrichment_citation_coverage VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
    coverageId, target.target_id, target.input_sha256, 'Crossref', 'outgoing', snapshot, source.source_url,
    part.length, parsed.declared, done ? null : String(end), status, observed));
  for (let i = 0; i < statements.length; i += 40) await db.batch(statements.slice(i, i + 40));
  const receipt = await statement(db, 'SELECT coverage_id FROM enrichment_citation_coverage WHERE coverage_id=?', coverageId).first();
  if (!receipt) fail('crossref_reference_readback_failed');
  return {source_id: source.source_id, offset: end, done, returned_entries: parsed.returned,
    unresolved_entries: parsed.unresolved, coverage_status: status};
}
