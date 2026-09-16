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
    Map, Object, RegExp, String, Number, Array, Error,
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

test('schema-aligned manual packet maps into the existing paper-sheet field groups', () => {
  const api = setup();
  const id = 'CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-001';
  const body = `<!-- manual-scientific-enrichment:2026-09-15:${id} -->\n### Manual scientific enrichment packet — schema-aligned, non-decisional\n#### Top-level scientific fields\n- **summary — reported:** Firm-level consequences of infiltration.\n- **contribution — reported:** Estimates changes after entry.\n- **research_question — reported:** What happens after infiltration?\n- **infiltration_definition — reported:** Statistical proxy.\n- **infiltration_operationalisation — reported:** Time-varying treatment.\n- **authors_limitations — reported:** Proxy can misclassify.\n#### Study S1\n- **study_type:** longitudinal quasi-experimental study.\n- **population:** Italian corporations.\n- **period:** 2006–2016.\n- **sample size:** about 9,200 firms.\n- **geography:** Centre and North of Italy.\n#### Datasets\n- **D1 CADS:** balance-sheet information.\n- **D2 Infocamere:** ownership/governance.\n#### Analysis A2 — causal effect\n- **design:** staggered Difference-in-Differences.\n- **method:** firm and time fixed effects.\n- **identification:** within-firm change around entry.\n- **robustness:** PSM and SCM.\n#### Key variable uses\n- **V1 NDR_it — role:** treatment indicator.\n- **V2 log revenues — role:** primary outcome.\n#### Findings to encode\n- **F1:** revenues increase after infiltration.\n#### Clinical-contribution framework — analyst proposal only\n- **status:** \`proposed\`\n- **primary:** \`prognosis\`\n- **secondary:** \`aetiology\`\n- **alternative:** \`aetiology\``;
  const parsed = api.parseComment({body, html_url:'https://github.com/o/r/issues/1#issuecomment-2', created_at:'2026-09-15T10:00:00Z', _issue_number:1}, id);
  const structured = parsed.structured;
  assert.equal(structured.overview.find(([key]) => key === 'research_question')[1], 'What happens after infiltration?');
  assert.equal(structured.studies[0].rows.find(([key]) => key === 'period')[1], '2006–2016.');
  assert.match(structured.datasets.join(' '), /CADS/);
  assert.equal(structured.methods[0].rows.find(([key]) => key === 'design')[1], 'staggered Difference-in-Differences.');
  assert.match(structured.variables.join(' '), /NDR_it/);
  assert.match(structured.findings.map(row => row[1] || row).join(' '), /revenues increase/);
  assert.deepEqual(Array.from(parsed.classes), ['prognosis','aetiology']);
});

test('manual annotation parser rejects another candidate identity', () => {
  const api = setup();
  assert.throws(() => api.parseComment({body:'<!-- manual-scientific-enrichment:2026-09-15:CAND-OTHER -->'}, 'CAND-X'));
});
