import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../../site/workspace.js',import.meta.url),'utf8');
const context=vm.createContext({URL});vm.runInContext(source,context);
const api=context.CILEWorkspace,base='https://example.test/project/';

test('view state round-trips Unicode, special characters and pagination',()=>{
  const input={query:'mafia & legal',author:'D’Amico; João',venue:'Journal / 1',year:'2026',review:'pending',access:'unknown',sort:'oldest',content:'summary',category:'diagnosis',page:3,size:50,paper:'CAND-EXAMPLE'};
  const output=api.readView(api.viewURL(base,input));
  assert.deepEqual(JSON.parse(JSON.stringify(output)),input);
});
test('duplicate and malformed numeric parameters do not become navigation instructions',()=>{
  const output=api.readView(base+'?page=-1&size=999&q=first&q=second&year=2026&year=2025');
  assert.equal(output.page,1);assert.equal(output.size,25);assert.equal(output.query,'');assert.equal(output.year,'all');
  assert.equal(api.readView(base+'?page=1e5').page,1);
});
test('URL state rejects control characters and unbounded input',()=>{
  assert.equal(api.readView(base+'?paper=%00secret').paper,'');
  assert.equal(api.readView(base+'?q='+('x'.repeat(601))).query,'');
});
test('shared paper links retain the project path and contain only the public identifier',()=>{
  const link=api.paperURL(base+'index.html?q=mafia&page=9&token=secret#register','CAND-ONE');
  assert.equal(link,base+'?paper=CAND-ONE');
  assert.equal(api.paperURL(base+'?q=mafia','CAND-ONE'),link);
});
test('view links drop unknown and credential-like query parameters',()=>{
  const url=api.viewURL(base+'?token=secret&private=hidden#section',{query:'risk',page:2});
  assert.equal(url.href,base+'?q=risk&page=2');
});
test('default view has no redundant parameters',()=>{
  assert.equal(api.viewURL(base,api.readView(base)).href,base);
});
test('reference text preserves recorded values without invented citation fields',()=>{
  const record=Object.freeze({authors:'A. Author; B. Author',year:2025,title:'Recorded <title>',venue:'Recorded venue',doi:'10.1234/record'});
  assert.equal(api.reference(record),'A. Author; B. Author · (2025) · Recorded <title> · Recorded venue · DOI: 10.1234/record');
  assert.equal(api.reference({title:'Only a title'}),'Only a title');
});
test('the workspace is a read-only consumer, not a parallel data or approval source',()=>{
  assert.doesNotMatch(source,/\bfetch\s*\(|localStorage|sessionStorage|innerHTML|\/api\/paper-enrichment/);
  assert.match(source,/getRecords\(\)\.find\(row=>row\.id===view\.paper\)/);
});
test('public pages keep the same Method destination and explicit workspace loading order',()=>{
  for(const page of ['index','stats','aml','model','curate']) {
    const html=fs.readFileSync(new URL('../../site/'+page+'.html',import.meta.url),'utf8');
    assert.match(html,/<nav[\s\S]*?method\.html/);
    if(['index','stats'].includes(page)) {
      assert.ok(html.indexOf('workspace.js?v=1')<html.indexOf('paper-register.js?v=archive-20260919-v2'));
      assert.ok(html.includes('workspace.js?v=1'));
    }
  }
});
