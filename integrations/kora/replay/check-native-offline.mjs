// Executes the pure functions against native YAML checks. Not SDK/native execution.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {isDeepStrictEqual} from 'node:util';
const require=createRequire(import.meta.url),YAML=require('yaml'),Ajv=require('ajv');
const root=path.dirname(fileURLToPath(import.meta.url));
const pilot=fs.existsSync(path.join(root,'pilot'))?path.join(root,'pilot'):path.join(root,'../control-plane');
const {evaluateFrontier}=await import(pathToFileURL(path.join(pilot,'scripts/frontier-core.mjs')));
const {routeActivation}=await import(pathToFileURL(path.join(pilot,'scripts/router-core.mjs')));
const proc=YAML.parse(fs.readFileSync(path.join(pilot,'processes/cile-hourly-control-plane.yaml'),'utf8'));
const ajv=new Ajv({strict:false});
const outputValidators={'evaluate-frontier':ajv.compile(proc.types.FrontierStatus),'route-activation':ajv.compile(proc.types.RouteDecision)};
const functions={'evaluate-frontier':evaluateFrontier,'route-activation':routeActivation};
const results=fs.readdirSync(path.join(pilot,'tests')).filter(f=>f.endsWith('.yaml')).map(file=>{
 const doc=YAML.parse(fs.readFileSync(path.join(pilot,'tests',file),'utf8'));
 const actual=functions[doc.spec.target.node](doc.spec.input.inline);
 const errors=[];
 if(!outputValidators[doc.spec.target.node](actual)) errors.push('output-schema');
 for(const check of doc.spec.checks){
  if(check.type==='schema')continue;
  if(check.type!=='exact'||!/^\$\.\w+$/.test(check.path))throw Error('Unsupported check: '+file);
  const field=check.path.slice(2);
  const expected=Object.hasOwn(check,'expected')?check.expected:doc.spec.expected.inline[field];
  if(!isDeepStrictEqual(actual[field],expected))errors.push({field,expected,actual:actual[field]});
 }
 return {file,classification:file.includes('-starvation-over-complete')?'underspecified_historical':'contract_assertion',passed:errors.length===0,errors};
});
const report={scope:'Offline pure functions on native YAML, not SDK/sandbox/native execution',total:results.length,passed:results.filter(r=>r.passed).length,failed:results.filter(r=>!r.passed).length,results};
fs.writeFileSync(path.join(root,'native-offline-results.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({...report,results:results.filter(r=>!r.passed)},null,2));
process.exitCode=report.failed?1:0;
