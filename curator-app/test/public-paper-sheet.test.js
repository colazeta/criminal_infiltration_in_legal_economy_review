import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../../site/paper-sheet-support.js', import.meta.url), 'utf8');
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.value = ''; this.attributes = {}; }
  set textContent(value) { this.value = String(value ?? ''); this.children = []; }
  get textContent() { return this.value + this.children.map((n) => n.textContent).join(' '); }
  set innerHTML(_) { throw new Error('HTML injection forbidden'); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.value = ''; this.children = nodes; }
  setAttribute(key, value) { this.attributes[key] = value; }
}
function setup(fetchImpl = async () => { throw new Error('offline'); }) {
  const context = vm.createContext({ document: { createElement: (tag) => new Element(tag) },
    URL, AbortController, setTimeout, clearTimeout, fetch: fetchImpl });
  vm.runInContext(source, context);
  return context.CILEPaperSheetSupport;
}
const bibliography = { title: 'A paper', authors: 'Author', year: 2026, venue: 'Journal', doi: '10.1/test' };
const record = { id: 'CAND-TEST', ...bibliography };
function fixture(synopsis = 'Updated synopsis') {
  return { schemaVersion: 1, records: [{ id: record.id, bibliography: { ...bibliography },
    readingAid: { kind: 'verified_abstract_source', synopsis, sourceLabel: 'Publisher', sourceUrl: 'https://example.org/paper', checkedAt: '2026-09-13' },
    abstract: { status: 'available', source: 'Publisher', sourceUrl: 'https://example.org/paper', checkedAt: '2026-09-13' },
    retrieval: { status: 'full_text', fullTextUrl: 'https://example.org/paper.pdf', resolvedDoi: '10.1/test', checkedAt: '2026-09-13' },
    access: { status: 'unknown', source: 'Assessment', checkedAt: '2026-09-13' } }] };
}
function descendants(node) { return [node, ...node.children.flatMap(descendants)]; }

test('renders the actual synopsis, abstract source, date and retrieval metadata', () => {
  const api = setup(); const parent = new Element('section');
  api.render(parent, fixture().records[0], record);
  assert.match(parent.textContent, /Updated synopsis/);
  assert.match(parent.textContent, /non testo originale/);
  assert.match(parent.textContent, /2026-09-13/);
  assert.match(parent.textContent, /Accesso non determinato/);
  assert.ok(descendants(parent).some((node) => node.href === 'https://example.org/paper.pdf'));
});

test('a synopsis upgrade is visible when the same record is reopened, without cached data', async () => {
  const calls = []; let revision = 'Initial synopsis';
  const api = setup(async (url, options) => {
    calls.push([url, options.cache]);
    return { ok: true, json: async () => fixture(revision) };
  });
  const parent = new Element('section');
  await api.load(parent, record);
  assert.match(parent.textContent, /Initial synopsis/);
  revision = 'Enriched synopsis';
  await api.load(parent, record);
  assert.match(parent.textContent, /Enriched synopsis/);
  assert.doesNotMatch(parent.textContent, /Initial synopsis/);
  assert.deepEqual(calls, [['./paper-support.json', 'no-store'], ['./paper-support.json', 'no-store']]);
});

test('failed retrieval does not claim that an abstract is absent', async () => {
  const api = setup(); const parent = new Element('section');
  await api.load(parent, record);
  assert.match(parent.textContent, /non significa che l’abstract sia assente/);
  assert.equal(parent.attributes['aria-busy'], 'false');
});

test('mixed bibliography generations and duplicate IDs are rejected', () => {
  const api = setup();
  const mixed = fixture(); mixed.records[0].bibliography.title = 'Another paper';
  assert.throws(() => api.selectRecord(mixed, record), /revision_mismatch/);
  const duplicate = fixture(); duplicate.records.push(duplicate.records[0]);
  assert.throws(() => api.selectRecord(duplicate, record), /identity/);
  assert.throws(() => api.selectRecord({ schemaVersion: 1, records: [] }, record), /revision_mismatch/);
});

test('a late response cannot overwrite a different or closed sheet', async () => {
  let current = true; let resolve;
  const api = setup(() => new Promise((done) => { resolve = done; }));
  const parent = new Element('section');
  const pending = api.load(parent, record, () => current);
  current = false;
  parent.textContent = 'Another sheet';
  resolve({ ok: true, json: async () => fixture() });
  await pending;
  assert.equal(parent.textContent, 'Another sheet');
});

test('untrusted metadata remains text and unsafe or credentialled links stay inert', () => {
  const api = setup(); const parent = new Element('section'); const data = fixture('<img onerror=alert(1)>').records[0];
  data.readingAid.sourceUrl = 'javascript:alert(1)';
  data.abstract.sourceUrl = 'https://user:password@example.org';
  api.render(parent, data, record);
  assert.match(parent.textContent, /<img onerror=alert\(1\)>/);
  assert.ok(descendants(parent).every((node) => node.tag !== 'img'));
  assert.ok(descendants(parent).filter((node) => node.href).every((node) => !/javascript:|password/.test(node.href)));
  assert.equal(api.safeUrl('http://example.org'), '');
});

test('a resolver DOI conflict is visible without replacing registered identity', () => {
  const api = setup(); const parent = new Element('section'); const data = fixture().records[0];
  data.retrieval.resolvedDoi = '10.1/other';
  api.render(parent, data, record);
  assert.match(parent.textContent, /differisce da quello registrato/);
  assert.equal(record.doi, '10.1/test');
});

test('preparatory text is not presented as an author abstract', () => {
  const api = setup(); const parent = new Element('section'); const data = fixture().records[0];
  data.readingAid.kind = 'review_synopsis'; data.abstract = null;
  api.render(parent, data, record);
  assert.match(parent.textContent, /Sintesi preliminare — da verificare/);
  assert.doesNotMatch(parent.textContent, /Disponibilità dell’abstract verificata/);
});

test('the existing double-click and accessible button route both reach enrichment', () => {
  const registerSource = fs.readFileSync(new URL('../../site/paper-register.js', import.meta.url), 'utf8');
  assert.match(registerSource, /row\.addEventListener\(["']dblclick["']/);
  assert.match(registerSource, /open\.addEventListener\(["']click["']/);
  assert.match(registerSource, /import\("\.\/paper-sheet-support\.js\?v=frontend-20260917"\)/);
  assert.match(registerSource, /CILEPaperSheetSupport\.load\(support, record, isCurrent\)/);
  assert.doesNotMatch(registerSource, /non sono ancora collegati a questa scheda/);
});
