import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

test('the entry document invalidates the prior register bundle cache key', () => {
  const html=fs.readFileSync(new URL('../../site/index.html',import.meta.url),'utf8');
  assert.match(html,/paper-register\.js\?v=processing-001/);
  assert.doesNotMatch(html,/paper-register\.js\?v=research-001/);
});
