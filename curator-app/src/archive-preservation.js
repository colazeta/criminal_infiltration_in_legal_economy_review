/* Bounded read-only export. Every page is encrypted before leaving the object.
   This is a backup, never a second current archive or a publication source. */
import {canonicalJson,sha256} from './review-v2.js';
import {ARCHIVE_TABLES,databaseSnapshot} from './architecture-audit.js';

export const BACKUP_CONTRACT='CILE-PRIVATE-ARCHIVE-BACKUP-2';
export const LEGACY_BACKUP_CONTRACT='CILE-PRIVATE-ARCHIVE-BACKUP-1';
const knownContract=contract=>[BACKUP_CONTRACT,LEGACY_BACKUP_CONTRACT].includes(contract);
const enc=new TextEncoder(),dec=new TextDecoder('utf-8',{fatal:true});
const fail=()=>{throw Error('archive_backup_invalid')};
const b64=bytes=>{let value='';for(let i=0;i<bytes.length;i+=8192)value+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(value)};
const unb64=value=>Uint8Array.from(atob(value),c=>c.charCodeAt(0));

// Explicit structured-clone subset: unknown types fail, rather than losing bytes.
export function encodeStored(value){
  if(value instanceof Uint8Array)return {type:'bytes',value:b64(value)};
  if(value===null||typeof value==='string'||typeof value==='boolean'||typeof value==='number'&&Number.isFinite(value))return {type:'scalar',value};
  if(Array.isArray(value))return {type:'array',value:value.map(encodeStored)};
  if(value&&Object.getPrototypeOf(value)===Object.prototype)return {type:'object',value:Object.keys(value).sort().map(k=>[k,encodeStored(value[k])])};
  fail();
}
export function decodeStored(encoded){
  if(!encoded||Object.keys(encoded).sort().join(',')!=='type,value')fail();
  if(encoded.type==='bytes'){const b=unb64(encoded.value);if(b64(b)!==encoded.value)fail();return b}
  if(encoded.type==='scalar'){if(encoded.value!==null&&!['string','boolean','number'].includes(typeof encoded.value))fail();return encoded.value}
  if(encoded.type==='array'&&Array.isArray(encoded.value))return encoded.value.map(decodeStored);
  if(encoded.type==='object'&&Array.isArray(encoded.value)){
    const result={};for(const pair of encoded.value){if(!Array.isArray(pair)||pair.length!==2||typeof pair[0]!=='string'||Object.hasOwn(result,pair[0]))fail();Object.defineProperty(result,pair[0],{value:decodeStored(pair[1]),writable:true,enumerable:true,configurable:true})}return result;
  }
  fail();
}
async function backupKey(secret,contract){
  if(typeof secret!=='string'||secret.length<32||!knownContract(contract))fail();
  const root=await crypto.subtle.importKey('raw',enc.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  const material=await crypto.subtle.sign('HMAC',root,enc.encode(contract));
  return crypto.subtle.importKey('raw',material,{name:'AES-GCM'},false,['encrypt','decrypt']);
}
export async function sealBackupPage(value,secret,commit,snapshot_id,contract=BACKUP_CONTRACT){
  const raw=enc.encode(canonicalJson(value));if(raw.length>7000000)fail();
  const iv=crypto.getRandomValues(new Uint8Array(12)),aad=enc.encode(contract+'\n'+commit+'\n'+snapshot_id);
  const ciphertext=await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:aad,tagLength:128},await backupKey(secret,contract),raw);
  return {contract,commit,snapshot_id,iv:b64(iv),ciphertext:b64(new Uint8Array(ciphertext))};
}
export async function openBackupPage(page,secret,commit,snapshot_id){
  if(!page||Object.keys(page).sort().join(',')!=='ciphertext,commit,contract,iv,snapshot_id'||!knownContract(page.contract)||page.commit!==commit||page.snapshot_id!==snapshot_id)fail();
  const iv=unb64(page.iv);if(iv.length!==12||typeof page.ciphertext!=='string'||page.ciphertext.length>9500000)fail();
  const raw=await crypto.subtle.decrypt({name:'AES-GCM',iv,additionalData:enc.encode(page.contract+'\n'+commit+'\n'+snapshot_id),tagLength:128},await backupKey(secret,page.contract),unb64(page.ciphertext));
  return JSON.parse(dec.decode(raw));
}

export async function archiveBackupPage(env,storage,request){
  if(!request||!/^[-a-f0-9]{36}$/.test(request.snapshot_id||''))fail();
  const {snapshot_id,...parts}=request;request=parts;
  if(!request||typeof request!=='object'||Array.isArray(request)||Object.keys(request).some(k=>!['part','table','after'].includes(k)))fail();
  let page;
  if(request.part==='catalogue'){
    if(Object.keys(request).length!==1)fail();
    const {counts,schema,digests,schema_sha256,state_sha256}=await databaseSnapshot(env.REVIEW_DB);
    page={part:'catalogue',counts,schema,digests,schema_sha256,state_sha256,sql_pagination:'rowid_keyset',
      kv_exclusions:['nonce:','probe:'],scope:'entire_enrichment_store',
      other_stores_included:false,alarm:await storage.getAlarm()};
  }else if(request.part==='sql'){
    if(Object.keys(request).sort().join(',')!=='after,part,table'||!ARCHIVE_TABLES.includes(request.table)||!(request.after===null||Number.isSafeInteger(request.after)))fail();
    // All governed tables currently have rowid. No arbitrary identifier or SQL.
    const query=env.REVIEW_DB.prepare(`SELECT rowid AS __backup_rowid,* FROM ${request.table}${request.after===null?'':' WHERE rowid>?'} ORDER BY rowid LIMIT 100`);
    const values=(await (request.after===null?query:query.bind(request.after)).all()).results;
    const rowids=values.map(row=>row.__backup_rowid);
    if(rowids.some((id,index)=>!Number.isSafeInteger(id)||(index?id<=rowids[index-1]:request.after!==null&&id<=request.after)))fail();
    page={part:'sql',table:request.table,after:request.after,rowids,rows:values.map(({__backup_rowid,...row})=>row)};
  }else if(request.part==='kv'){
    if(Object.keys(request).sort().join(',')!=='after,part'||typeof request.after!=='string'||request.after.length>2048)fail();
    const entries=await storage.list({limit:16,...(request.after?{startAfter:request.after}:{})});
    const keys=[...entries.keys()];
    if(keys.some(k=>typeof k!=='string'||k<=request.after)||keys.some((k,i)=>i&&k<=keys[i-1]))fail();
    page={part:'kv',after:request.after,next:keys.at(-1)||null,entries:[...entries].filter(([k])=>!k.startsWith('nonce:')&&!k.startsWith('probe:')).map(([k,v])=>[k,encodeStored(v)])};
  }else fail();
  return sealBackupPage(page,env.SESSION_SECRET,env.DEPLOY_COMMIT,snapshot_id);
}

export async function digestRows(values){return sha256(canonicalJson([...values].sort((a,b)=>canonicalJson(a).localeCompare(canonicalJson(b),'en'))))}
