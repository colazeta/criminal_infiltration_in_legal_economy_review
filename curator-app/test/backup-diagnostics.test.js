import test from 'node:test';
import assert from 'node:assert/strict';
import {diagnostic} from '../../scripts/architecture/backup-diagnostics.mjs';
test('backup transport diagnostics reveal only allowlisted phase and HTTP status',()=>{
 const url='https://criminal-infiltration-curator.colazeta-research.workers.dev/api/paper-enrichment-machine';
 const options={body:JSON.stringify({operation:'architecture-backup',backup:{part:'sql',table:'PRIVATE'},secret:'PRIVATE'})};
 assert.deepEqual(diagnostic(url,options,403),{stage:'backup_transport',phase:'sql',status:403});
 assert.deepEqual(diagnostic('https://PRIVATE',options,'PRIVATE'),{stage:'backup_transport',phase:'other',status:'transport_failure'});
 assert.ok(!JSON.stringify(diagnostic(url,{body:'PRIVATE'},503)).includes('PRIVATE'));
});
