// Kora-compatible scalar vocabulary, explicit optional-field contract.
// Local validator checks do not establish native execution success.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {isDeepStrictEqual} from 'node:util';
const require=createRequire(import.meta.url),YAML=require('yaml'),Ajv=require('ajv');
const root=path.dirname(fileURLToPath(import.meta.url));
const pilot=fs.existsSync(path.join(root,'pilot'))?path.join(root,'pilot'):path.join(root,'../control-plane');
const current=YAML.parse(fs.readFileSync(path.join(pilot,'processes/cile-hourly-control-plane.yaml'),'utf8'));
const previous=YAML.parse(fs.readFileSync(path.join(root,'history/process-schema-d7f84cc8.yaml'),'utf8'));
const registry=JSON.parse(fs.readFileSync(path.join(root,'evidence/kora-process-schema-0.13.0.json'),'utf8').replace(/^\uFEFF/,''));
const resourceSchema=registry.data.schema.jsonSchema;
const fragmentRule=resourceSchema.properties.types.patternProperties['^(.*)$'].properties.properties.patternProperties['^(.*)$'];
const allowed=fragmentRule.anyOf.find(s=>s.type==='object').properties.type.anyOf.map(s=>s.const);
const ajv=new Ajv({strict:false,allErrors:true,coerceTypes:false,useDefaults:false,removeAdditional:false});
const validateResource=ajv.compile(resourceSchema);
if(!validateResource(current))throw Error(JSON.stringify(validateResource.errors));
let fragments=0;
function visit(s,p){
 if(typeof s==='boolean')return;
 if(typeof s.type!=='string'||!allowed.includes(s.type)||'nullable' in s)throw Error('Unsupported type form at '+p);
 fragments++;
 for(const[k,v]of Object.entries(s.properties||{}))visit(v,`${p}.properties.${k}`);
 if(s.items&&typeof s.items==='object')visit(s.items,`${p}.items`);
}
for(const[k,v]of Object.entries(current.types))visit(v,`types.${k}`);
const restored=structuredClone(current);
for(const name of ['ActivationInput','ActivationWithFrontier']) {
 const evidence=current.types[name].properties.identity_preflight_evidence;
 if(current.types[name].required.includes('identity_preflight_evidence'))throw Error('Evidence became mandatory');
 for(const [key,type]of [['pending_observation_count','integer'],['oldest_pending_age_seconds','number']]){
  if(!isDeepStrictEqual(evidence.properties[key],{type,minimum:0})||(evidence.required||[]).includes(key))throw Error('Wrong optional numeric declaration');
  restored.types[name].properties.identity_preflight_evidence.properties[key].nullable=true;
 }
}
if(!isDeepStrictEqual(restored,previous))throw Error('Unexpected schema changes besides removing four nullable keywords');
if(!isDeepStrictEqual(current.types.ActivationInput.properties.identity_preflight_evidence,current.types.ActivationWithFrontier.properties.identity_preflight_evidence))throw Error('Shared schema drift');
const cases=JSON.parse(fs.readFileSync(path.join(root,'cases.json'),'utf8'));
const oldCases=JSON.parse(fs.readFileSync(path.join(root,'history/cases-d7f84cc8.json'),'utf8'));
const template=cases.find(c=>c.id==='A-starvation-insufficient-evidence');
const values=[undefined,null,-1,-0.1,0,0.5,1,19,20,86399.999,86400,'20',true,false,{},[]];
const countOK=v=>v===undefined||(Number.isInteger(v)&&v>=0);
const ageOK=v=>v===undefined||(typeof v==='number'&&Number.isFinite(v)&&v>=0);
let assertions=0,deliberateNullAcceptanceChanges=0;
for(const name of ['ActivationInput','ActivationWithFrontier']){
 const oldValid=ajv.compile(previous.types[name]),valid=ajv.compile(current.types[name]);
 const base=name==='ActivationInput'?template.input:{...template.input,...template.frontierInput};
 for(const count of values)for(const age of values){
  const e={activity_kind:'new_research',evidence_ref:'synthetic:optional-numbers'};
  if(count!==undefined)e.pending_observation_count=count;
  if(age!==undefined)e.oldest_pending_age_seconds=age;
  const input={...base,identity_preflight_evidence:e};
  const expected=countOK(count)&&ageOK(age);
  const result=valid(input),oldResult=oldValid(input);
  if(result!==expected)throw Error(`${name}: numeric acceptance mismatch`);
  if(result!==oldResult){
   if(result||!(count===null||age===null))throw Error('Non-null acceptance changed');
   deliberateNullAcceptanceChanges++;
  }
  assertions++;
 }
 for(const[e,expected]of [[undefined,true],[{},true],[null,false],[[],false],['unknown',false],
  [{activity_kind:null},false],[{activity_kind:'F3'},false],[{activity_kind:'unknown'},true],
  [{activity_kind:'in_progress'},true],[{evidence_ref:''},false],[{evidence_ref:null},false],[{extra:true},false]]){
  const input=e===undefined?base:{...base,identity_preflight_evidence:e};
  if(valid(input)!==expected)throw Error('Other schema constraints changed');assertions++;
 }
 for(const patch of [{writer_ready:undefined},{identity_starvation_status:'not_required'}]){
  if(valid({...base,...patch}))throw Error('Required/additional properties weakened');assertions++;
 }
}
let revised=0;
for(const old of oldCases){
 const c=cases.find(x=>x.id===old.id);if(!c)throw Error('Lost case '+old.id);
 if(!isDeepStrictEqual(old.input,c.input))throw Error('Historical input changed '+old.id);
 if(/^[AB]-starvation-null-(age|count)$/.test(old.id)){
  if(c.kind!=='schema-rejection'||!isDeepStrictEqual(c.expected,{valid:false}))throw Error('Null must be rejected');
  revised++;
 }else if(!isDeepStrictEqual(c.expected,old.expected)||c.kind!==old.kind)throw Error('Unrelated oracle changed '+old.id);
}
if(revised!==4)throw Error('Expected exactly four documented null-case revisions');
const {evaluateIdentityStarvation}=await import(pathToFileURL(path.join(pilot,'scripts/identity-preflight.mjs')));
for(const patch of [{pending_observation_count:null,oldest_pending_age_seconds:86400},{pending_observation_count:20,oldest_pending_age_seconds:null}]){
 const p=evaluateIdentityStarvation({identity_preflight_evidence:{...patch,activity_kind:'new_research',evidence_ref:'synthetic:invalid-direct-call'}});
 if(p.identity_starvation_status!=='undetermined'||p.identity_starvation_reason!=='invalid_queue_evidence')throw Error('Helper treated null as omission');
}
const report={scope:'Offline scalar/optional declaration and contract tests, not native compiler/runtime execution',
 schemaSource:'CLI 0.13.0 Process schema: scalar integer/number, object properties and required lists; no new keyword introduced',
 oldNativeEvidence:'native-setup-d7f84cc8.json: nullable rejected before all fixtures',
 fragments,removedNullableKeywords:4,sharedSchemasIdentical:true,noOtherSchemaChanges:true,
 assertions,passed:assertions,deliberateNullAcceptanceChanges,oldInputsPreserved:oldCases.length,
 oldExpectationsUnchanged:oldCases.length-revised,documentedNullCaseRevisions:revised,newZeroCases:4,
 normalization:'None. Null is invalid workflow input. Producers must supply omitted unknown metrics explicitly; no conversion before Kora validation is assumed or implemented.'};
fs.writeFileSync(path.join(root,'process-type-checks.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
