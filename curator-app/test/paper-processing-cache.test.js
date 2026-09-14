import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

test('the entry document invalidates earlier register bundle cache keys', () => {
  const html=fs.readFileSync(new URL('../../site/index.html',import.meta.url),'utf8');
  assert.match(html,/paper-register\.js\?v=delivery-002/);
  assert.doesNotMatch(html,/paper-register\.js\?v=(?:(?:research|processing|completion)-001)/);
});

test('both research-sheet imports invalidate the previous unversioned child bundle', () => {
  const source=fs.readFileSync(new URL('../../site/paper-register.js',import.meta.url),'utf8');
  assert.equal((source.match(/import\("\.\/paper-sheet-research\.js\?v=delivery-002"\)/g)||[]).length,2);
  assert.doesNotMatch(source,/import\("\.\/paper-sheet-research\.js"\)/);
});
