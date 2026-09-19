// Offline checks. The CLI resource schema is not the server's process compiler.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {isDeepStrictEqual} from 'node:util';
const require=createRequire(import.meta.url),YAML=require('yaml'),Ajv=require('ajv');
const root=path.dirname(fileURLToPath(import.meta.url));
const pilot=fs.existsSync(path.join(root,'pilot'))?path.join(root,'pilot'):path.join(root,'../control-plane');
const readYaml=p=>YAML.parse(fs.readFileSync(p,'utf8'));
const current=readYaml(path.join(pilot,'processes/cile-hourly-control-plane.yaml'));
const previous=readYaml(path.join(root,'history/process-schema-63106891.yaml'));
const registry=JSON.parse(fs.readFileSync(path.join(root,'evidence/kora-process-schema-0.13.0.json'),'utf8').replace(/^\uFEFF/,''));
const resourceSchema=registry.data.schema.jsonSchema;
const fragmentRule=resourceSchema.properties.types.patternProperties['^(.*)$'].properties.properties.patternProperties['^(.*)$'];
const allowed=fragmentRule.anyOf.find(s=>s.type==='object').properties.type.anyOf.map(s=>s.const);
const ajv=new Ajv({strict:false,allErrors:true,coerceTypes:false,useDefaults:false,removeAdditional:false});
const validateResource=ajv.compile(resourceSchema),validateFragment=ajv.compile(fragmentRule);
const previousResourceAccepted=validateResource(previous);
if(!validateResource(current))throw Error('Process resource schema: '+JSON.stringify(validateResource.errors));
// Traverse actual schema fragments, not the properties map or required/enum values.
function fragments(types){
 const all=[];
 const visit=(s,p)=>{
  if(typeof s==='boolean')return;
  all.push({path:p,schema:s});
  for(const [k,v] of Object.entries(s.properties||{}))visit(v,`${p}.properties.${k}`);
  if(s.items&&typeof s.items==='object'&&!Array.isArray(s.items))visit(s.items,`${p}.items`);
  if(s.additionalProperties&&typeof s.additionalProperties==='object')visit(s.additionalProperties,`${p}.additionalProperties`);
 };
 for(const [name,s] of Object.entries(types))visit(s,`types.${name}`);
 return all;
}
const incompatible=fragments(previous.types).filter(({schema:s})=>typeof s.type!=='string'||!allowed.includes(s.type));
if(incompatible.length!==4)throw Error('Expected exactly four old incompatible fragments');
for(const {path:p,schema:s} of fragments(current.types)){
 if(typeof s.type!=='string'||!allowed.includes(s.type)||!validateFragment(s))throw Error('Invalid explicit scalar type at '+p);
}
const reverted=structuredClone(current);
for(const name of ['ActivationInput','ActivationWithFrontier'])for(const [key,type]of [['pending_observation_count','integer'],['oldest_pending_age_seconds','number']]){
 const s=reverted.types[name].properties.identity_preflight_evidence.properties[key];
 if(s.type!==type||s.nullable!==true||s.minimum!==0)throw Error('Unexpected replacement shape');
 s.type=[type,'null'];delete s.nullable;
}
if(!isDeepStrictEqual(reverted,previous))throw Error('Changes beyond the four precise declarations');
if(!isDeepStrictEqual(current.types.ActivationInput.properties.identity_preflight_evidence,current.types.ActivationWithFrontier.properties.identity_preflight_evidence))throw Error('Shared evidence schema drift');
const cases=JSON.parse(fs.readFileSync(path.join(root,'cases.json'),'utf8'));
const template=cases.find(c=>c.id==='A-starvation-insufficient-evidence');
const values=[undefined,null,-1,-0.1,0,0.5,1,19,20,86399.999,86400,'20',true,false,{},[]];
const countOK=v=>v===undefined||v===null||(Number.isInteger(v)&&v>=0);
const ageOK=v=>v===undefined||v===null||(typeof v==='number'&&Number.isFinite(v)&&v>=0);
let checks=0;
for(const name of ['ActivationInput','ActivationWithFrontier']){
 const oldValid=ajv.compile(previous.types[name]),newValid=ajv.compile(current.types[name]);
 const base=name==='ActivationInput'?template.input:{...template.input,...template.frontierInput};
 const assert=(patch,expected,label)=>{
  const input={...base,...patch};
  const oldResult=oldValid(structuredClone(input)),newResult=newValid(structuredClone(input));
  if(oldResult!==expected||newResult!==expected)throw Error(`${name} ${label}: expected ${expected}, old ${oldResult}, new ${newResult}`);
  checks++;
 };
 for(const count of values)for(const age of values){
  const evidence={activity_kind:'new_research',evidence_ref:'synthetic:nullable-equivalence'};
  if(count!==undefined)evidence.pending_observation_count=count;
  if(age!==undefined)evidence.oldest_pending_age_seconds=age;
  assert({identity_preflight_evidence:evidence},countOK(count)&&ageOK(age),'numeric/null/omission cross-product');
 }
 for(const [e,expected]of [[undefined,true],[{},true],[null,false],[[],false],['unknown',false],
  [{activity_kind:null},false],[{activity_kind:'F3'},false],[{activity_kind:'unknown'},true],
  [{activity_kind:'in_progress'},true],[{activity_kind:'non_research'},true],
  [{evidence_ref:''},false],[{evidence_ref:null},false],[{unexpected:true},false]]){
  const patch=e===undefined?{}:{identity_preflight_evidence:e};assert(patch,expected,'evidence object boundaries');
 }
 assert({identity_starvation_status:'not_required'},false,'caller-forged result');
 assert({writer_ready:undefined},false,'required input missing');
}
for(const c of cases){
 const oldValid=ajv.compile(previous.types.ActivationInput),newValid=ajv.compile(current.types.ActivationInput);
 if(oldValid(c.input)!==newValid(c.input))throw Error('Existing fixture acceptance changed: '+c.id);
}
const report={scope:'Offline CLI resource/fragment-form checks and AJV nullable semantic equivalence, NOT Kora compiler/runtime execution',
 previousCommit:'631068912c29561a76279229dc36107abd7ccb22',incompatibleFragments:incompatible.map(({path,schema})=>({path,oldType:schema.type})),
 patchedFragments:4,sharedSchemasIdentical:true,noOtherSchemaChanges:true,explicitScalarTypeFragments:fragments(current.types).length,
 cliResourceSchemaAcceptsOldNestedUnion:previousResourceAccepted,cliResourceSchemaAcceptsNewForm:true,
 semanticAssertions:checks,semanticAssertionsPassed:checks,existingFixtureAcceptanceUnchanged:cases.length,
 nullableEvidence:'AJV documents scalar type + nullable:true as equivalent to type:[T,null]. CLI resource schema allows scalar type and additional keywords; server compiler/runtime nullable behavior remains unverified until native rerun.',
 sources:['evidence/kora-process-schema-0.13.0.json','https://ajv.js.org/json-schema.html#nullable-openapi']};
fs.writeFileSync(path.join(root,'process-type-checks.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
