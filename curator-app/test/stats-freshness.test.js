import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../../site/stats.js', import.meta.url), 'utf8').split('\nfetch(')[0];
function render(now, asOf) {
  const elements = new Map();
  const document = { querySelector(key) {
    if (!elements.has(key)) elements.set(key, {});
    return elements.get(key);
  }};
  class Clock extends Date { static now() { return Date.parse(now); } }
  const context = vm.createContext({ document, Date: Clock, Intl, payload: {calendar: {
    asOf, completedDays: 0, expectedDays: 0, missingDays: 0, lastLedgerDate: null,
  }}});
  vm.runInContext(source + '\nrenderStatus(payload);', context);
  return elements.get('#run-status');
}

test('stale calendar is visibly warned without inventing missing days', () => {
  const banner = render('2026-09-10T12:00:00Z', '2026-09-08T12:00:00Z');
  assert.match(banner.className, /partial/);
  assert.match(banner.textContent, /ATTENZIONE/);
  assert.match(banner.textContent, /giornate successive non sono verificate/);
});
test('fresh projection and refresh grace do not claim stale data', () => {
  const banner = render('2026-09-09T13:00:00Z', '2026-09-08T12:00:00Z');
  assert.doesNotMatch(banner.textContent, /ATTENZIONE/);
  assert.match(banner.textContent, /non conferma di importazione/);
});
