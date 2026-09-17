import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../../site/stats.js', import.meta.url), 'utf8');
function render(now, asOf) {
  const elements = new Map();
  const document = { querySelector(key) {
    if (!elements.has(key)) elements.set(key, {});
    return elements.get(key);
  }};
  class Clock extends Date { static now() { return Date.parse(now); } }
  const context = vm.createContext({ document, Date: Clock, Intl, payload: {
    daily: [{date:'2026-09-08',status:'completed',uniqueResults:0,intakeCandidates:0}],
    extraRuns: [], calendar: {asOf},
  }});
  vm.runInContext(source + '\nrenderStatus(payload);', context);
  return {title:elements.get('#statistics-notice-title').textContent,
    message:elements.get('#latest-execution').textContent,
    detail:elements.get('#run-status').textContent,
    badge:elements.get('#research-statistics-state').textContent};
}

test('stale publication is labelled without inventing missing days or a stopped search', () => {
  const notice = render('2026-09-10T12:00:00Z', '2026-09-08T12:00:00Z');
  assert.match(notice.badge, /Dati non aggiornati/);
  assert.match(notice.detail, /26 ore/);
  assert.match(notice.message, /non dimostra che le ricerche siano ferme/);
  assert.doesNotMatch(notice.detail, /mancanti|fallita|retry/);
});
test('fresh projection and refresh grace do not claim stale data', () => {
  const notice = render('2026-09-09T13:00:00Z', '2026-09-08T12:00:00Z');
  assert.equal(notice.badge, '· Dati disponibili');
  assert.doesNotMatch(notice.detail, /26 ore/);
  assert.match(notice.message, /non includono gli avvii straordinari/);
});
