import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {mapBounded} from '../src/public-paper-research.js';

test('bounded map preserves order while limiting concurrent work', async () => {
  let active = 0;
  let peak = 0;
  const values = [0, 1, 2, 3, 4, 5, 6];
  const output = await mapBounded(values, 3, async value => {
    active += 1;
    peak = Math.max(peak, active);
    await new Promise(resolve => setTimeout(resolve, 5));
    active -= 1;
    return value * 2;
  });
  assert.deepEqual(output, [0, 2, 4, 6, 8, 10, 12]);
  assert.equal(peak, 3);
});

test('public index construction uses the bounded worker pool', () => {
  const source = readFileSync(new URL('../src/public-paper-research.js', import.meta.url), 'utf8');
  assert.match(source, /const INDEX_CONCURRENCY=6;/);
  assert.match(source, /await mapBounded\(pageTargets,INDEX_CONCURRENCY/);
});

test('bounded map rejects invalid limits instead of silently running unbounded', async () => {
  await assert.rejects(mapBounded([1], 0, async value => value), /invalid_bounded_map/);
});
