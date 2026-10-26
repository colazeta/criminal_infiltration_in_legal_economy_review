import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {isDeepStrictEqual} from 'node:util';
const root=path.dirname(fileURLToPath(import.meta.url));
const baseline=JSON.parse(fs.readFileSync(path.join(root,'history/cases-before-starvation.json'),'utf8'));
const current=JSON.parse(fs.readFileSync(path.join(root,'cases.json'),'utf8'));
const originals=JSON.parse(fs.readFileSync(path.join(root,'starvation-inputs.json'),'utf8').replace(/^\uFEFF/,''));
const dedicatedArchive=JSON.parse(fs.readFileSync(path.join(root,'history/starvation-original-cases.json'),'utf8').replace(/^\uFEFF/,''));
if(!isDeepStrictEqual(originals,dedicatedArchive))throw Error('Dedicated archive altered');
for(const original of originals){
 const archived=baseline.find(c=>c.id===original.id);
 if(!isDeepStrictEqual(original,archived)||original.expected.route!=='RESOLVE')throw Error('Historical case altered');
 const revised=current.find(c=>c.historical_case_id===original.id);
 if(!revised||!isDeepStrictEqual(revised.input,original.input))throw Error('Current input changed');
 if(revised.expected.route!=='BLOCKED'||revised.expected.identity_starvation_status!=='undetermined'||
 revised.expected.reason!=='new_research_safety_not_established'||revised.expected.identity_starvation_reason!=='missing_preflight_evidence')throw Error('Incorrect revised oracle');
 if(current.some(c=>c.id===original.id))throw Error('Historical ID still in active suite');
}
console.log(JSON.stringify({originalCasesPreserved:originals.length,originalExpected:'RESOLVE',currentVersions:2,currentExpected:'BLOCKED',currentStatus:'undetermined',sameInputs:true,exitCodeRules:'unchanged'}));
