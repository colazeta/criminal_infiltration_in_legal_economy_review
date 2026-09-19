import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {routeActivation as oldRoute} from './history/router-before-starvation.mjs';
import {isDeepStrictEqual} from 'node:util';
const root=path.dirname(fileURLToPath(import.meta.url));
const pilot=fs.existsSync(path.join(root,'pilot'))?path.join(root,'pilot'):path.join(root,'../control-plane');
const {evaluateFrontier}=await import(pathToFileURL(path.join(pilot,'scripts/frontier-core.mjs')));
const cases=JSON.parse(fs.readFileSync(path.join(root,'cases.json'),'utf8'));
const baseline=JSON.parse(fs.readFileSync(path.join(root,'history/cases-before-starvation.json'),'utf8'));
for(const c of baseline){
 if(c.id.endsWith('-starvation-over-complete')) {
  const current=cases.find(x=>x.historical_case_id===c.id);
  if(!current||!isDeepStrictEqual(c.input,current.input))throw Error(`Historical input changed: ${c.id}`);
  if(current.expected.route!=='BLOCKED'||current.expected.identity_starvation_status!=='undetermined')throw Error(`Incorrect revised contract: ${c.id}`);
  continue;
 }
 const current=cases.find(x=>x.id===c.id);
 if(JSON.stringify(c.expected)!==JSON.stringify(current.expected))throw Error(`Changed expected: ${c.id}`);
 if(c.id.endsWith('-starvation-over-complete')&&JSON.stringify(c.input)!==JSON.stringify(current.input))throw Error(`Changed historical input: ${c.id}`);
}
const results=cases.filter(c=>c.id.includes('-starvation-')&&!c.historical_case_id).map(c=>{
 const actual=oldRoute({...c.input,...evaluateFrontier(c.input)});
 return {id:c.id,expectedRoute:c.expected.route,baselineRoute:actual.route,routeMismatch:actual.route!==c.expected.route};
});
const report={scope:'Old router with independently authored explicit-evidence route assertions. Two owner-authorized current revisions checked separately against archived original inputs.',unchangedCurrentExpectations:baseline.length-2,archivedOriginalExpectations:2,authorizedCurrentOracleRevisions:2,unchangedHistoricalInputs:2,total:results.length,demonstratedRouteMismatches:results.filter(r=>r.routeMismatch).length,results};
fs.writeFileSync(path.join(root,'starvation-baseline.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({...report,results:undefined}));
