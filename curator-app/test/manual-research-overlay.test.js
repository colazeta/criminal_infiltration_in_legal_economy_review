import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../../site/paper-sheet-manual.js', import.meta.url), 'utf8');

function setup() {
  const context = vm.createContext({
    document: { createElement() { return { append() {}, setAttribute() {} }; } },
    URL,
    fetch: async () => { throw new Error('offline'); },
    Map,
    Object,
    RegExp,
    String,
    Number,
    Array,
    Error,
  });
  vm.runInContext(source, context);
  return context.CILEManualResearch;
}

test('manual annotation parser exposes source-derived content but not analyst working sections', () => {
  const api = setup();
  const id = 'CAND-ACADEMIC-2026-09-01-001';
  const body = `<!-- manual-scientific-enrichment:2026-09-15:${id} -->\n## Scientific reading-support annotation\nSource: [Publisher](https://example.org/paper)\n### Source-derived fields\n- **Study:** Italy, 2010–2019.\n- **Findings:** Result reported.\n### Analyst assessment\nThis sentence is an internal interpretation.\n### Clinical-contribution framework — analyst proposal only\n- **primary:** \`diagnosis\`\n- **secondary:** \`screening\`\n### Remaining work\nExtract more tables.`;
  const parsed = api.parseComment({body, html_url:'https://github.com/o/r/issues/1#issuecomment-2', created_at:'2026-09-15T10:00:00Z', _issue_number:1}, id);
  assert.equal(parsed.assessment_state, 'unreviewed_manual_support');
  assert.deepEqual(Array.from(parsed.classes), ['diagnosis','screening']);
  const visible = parsed.sections.flatMap(section => section.items).join(' ');
  assert.match(visible, /Italy, 2010–2019/);
  assert.doesNotMatch(visible, /internal interpretation/);
  assert.doesNotMatch(visible, /Extract more tables/);
});

test('manual annotation parser rejects another candidate identity', () => {
  const api = setup();
  assert.throws(() => api.parseComment({body:'<!-- manual-scientific-enrichment:2026-09-15:CAND-OTHER -->'}, 'CAND-X'));
});
