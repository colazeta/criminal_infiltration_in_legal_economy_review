import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import './check-process-types.mjs';
const require=createRequire(import.meta.url),YAML=require('yaml'),Ajv=require('ajv');
const root=path.dirname(fileURLToPath(import.meta.url));
const pilot=fs.existsSync(path.join(root,'pilot'))?path.join(root,'pilot'):path.join(root,'../control-plane');
const proc=YAML.parse(fs.readFileSync(path.join(pilot,'processes/cile-hourly-control-plane.yaml'),'utf8'));
const schema=JSON.parse(fs.readFileSync(path.join(root,'evidence/kora-test-schema.json'),'utf8').replace(/^\uFEFF/,''));
const ajv=new Ajv({strict:false,allErrors:true}),test=ajv.compile(schema.data.schema.jsonSchema);
const inputValidators={'evaluate-frontier':ajv.compile(proc.types.ActivationInput),'route-activation':ajv.compile(proc.types.ActivationWithFrontier)};
const files=fs.readdirSync(path.join(pilot,'tests')).filter(f=>f.endsWith('.yaml'));
for(const name of files){const doc=YAML.parse(fs.readFileSync(path.join(pilot,'tests',name),'utf8'),{version:'1.1'});if(!test(doc))throw Error(name+JSON.stringify(test.errors));const input=doc.spec.input.inline;if(typeof input.scheduled_at!=='string')throw Error(name+' timestamp is not a string');const validator=inputValidators[doc.spec.target.node];if(!validator(input))throw Error(name+JSON.stringify(validator.errors));}
const result={passed:true,count:files.length,checks:['Process resource schema and scalar optional numeric fragments','Null rejected; omission and known zero distinguished','Kora Test JSON schema','Target node input JSON schema','YAML 1.1 scheduled_at remains string'],boundary:'Offline schema checks, not native Kora compilation or execution'};
fs.writeFileSync(path.join(root,'fixture-validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
