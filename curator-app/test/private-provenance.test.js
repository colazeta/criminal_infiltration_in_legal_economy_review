import test from 'node:test';
import assert from 'node:assert/strict';
import {isolatedStore} from '../../scripts/architecture/private-backup.mjs';
import {syncTargets,handlePaperEnrichment} from '../src/paper-enrichment.js';
import {ingestAnnotation} from '../src/annotation-archive.js';

const commit='e'.repeat(40),secret='private-provenance-test-key-only';
const repo='https://github.com/colazeta/criminal_infiltration_in_legal_economy_review';
const candidate='CAND-PRIVATE-PROVENANCE-TEST';
const now=Date.parse('2026-09-21T06:30:00Z');

async function fixture(){
  const x=isolatedStore(secret,commit);await x.core.requireReady();x.env=await x.core.environment();x.env.CURATOR_LOGIN='owner';
  await syncTargets(x.env,{schemaVersion:1,records:[{id:candidate,title:'Private provenance fixture',doi:'',sourceLinks:['https://example.org/paper']}]},now);
  await ingestAnnotation(x.env,{action:'observe',
    issue:{id:500,number:50,body:'<!-- curator-candidate:'+candidate+' -->',html_url:repo+'/issues/50',created_at:'2026-09-20T00:00:00Z',updated_at:'2026-09-20T00:00:00Z',actor:'owner'},
    comment:{id:501,body:'<!-- manual-scientific-enrichment:test:'+candidate+' -->\n### Top-level scientific fields\n- summary: retained private note\n### Clinical-contribution framework — analyst proposal only\n- status: insufficient_evidence\n### Sources consulted\nhttps://example.org/paper',html_url:repo+'/issues/50#issuecomment-501',created_at:'2026-09-20T01:00:00Z',updated_at:'2026-09-20T01:00:00Z',actor:'owner'}},now);
  return x;
}
function request(path){return new Request('https://enrichment.internal/api/paper-enrichment/'+path);}

test('full provenance remains curator-authenticated and includes retained operational and annotation history',async()=>{
  const x=await fixture(),target=x.db.prepare('SELECT target_id FROM enrichment_targets WHERE record_id=?').get(candidate).target_id;
  let response=await handlePaperEnrichment(request('provenance?id='+target),x.env,null);assert.equal(response.status,401);
  response=await handlePaperEnrichment(request('provenance?id='+target),x.env,{login:'owner'});assert.equal(response.status,200);
  const data=await response.json();assert.equal(data.target.record_id,candidate);assert.equal(data.inputs.length,1);assert.equal(data.jobs.length,4);assert.equal(data.annotations.length,1);
  assert.ok(Array.isArray(data.attempts));assert.ok(Array.isArray(data.runs));assert.ok(Array.isArray(data.sources));assert.ok(Array.isArray(data.proposals));
  const annotation=data.annotations[0];
  response=await handlePaperEnrichment(request('annotation?id='+target+'&annotation='+annotation.annotation_id),x.env,{login:'owner'});assert.equal(response.status,200);
  const detail=await response.json();assert.match(detail.source.entity.body,/retained private note/);assert.equal(detail.source.entity.actor,'owner');assert.equal(detail.receipt.source_sha256.length,64);
  x.db.close();
});
