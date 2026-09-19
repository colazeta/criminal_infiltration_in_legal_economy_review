import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const version = 'frontend-20260917-nav2-status-auto';
test('the entry documents invalidate earlier register bundle cache keys', () => {
  for (const page of ['index.html', 'stats.html']) {
    const html=fs.readFileSync(new URL('../../site/'+page,import.meta.url),'utf8');
    assert.ok(html.includes('paper-register.js?v='+version+'"'));
    assert.doesNotMatch(html,/paper-register\.js\?v=(?:delivery-002|(?:research|processing|completion)-001)/);
  }
});

test('both sheet imports use the current explicit child bundle revision', () => {
  const source=fs.readFileSync(new URL('../../site/paper-register.js',import.meta.url),'utf8');
  for (const [child,childVersion] of [['research','status-20260917'],['support','frontend-20260917']]) {
    const expected='import("./paper-sheet-'+child+'.js?v='+childVersion+'")';
    assert.equal(source.split(expected).length-1,2);
    assert.ok(!source.includes('import("./paper-sheet-'+child+'.js")'));
  }
});
