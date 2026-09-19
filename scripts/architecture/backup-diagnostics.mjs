/* Observe transport failures in the deployed backup client without changing its
   code, request, response, cryptography or restore gate. Never log request data. */
export function diagnostic(input,options,status){
  let phase='other';
  try{
    const url=new URL(typeof input==='string'?input:input.url);
    if(url.origin==='https://criminal-infiltration-curator.colazeta-research.workers.dev'){
      if(url.pathname==='/version')phase='version';
      else if(url.pathname==='/api/paper-enrichment-machine'){
        const body=JSON.parse(options?.body||'{}');
        if(body.operation==='architecture-backup'&&['catalogue','sql','kv'].includes(body.backup?.part))phase=body.backup.part;
      }
    }
  }catch{}
  return {stage:'backup_transport',phase,status:Number.isInteger(status)&&status>=100&&status<=599?status:'transport_failure'};
}
const original=globalThis.fetch;
globalThis.fetch=async(input,options)=>{
  try{
    const response=await original(input,options);
    if(!response.ok)process.stderr.write(JSON.stringify(diagnostic(input,options,response.status))+'\n');
    return response;
  }catch(error){process.stderr.write(JSON.stringify(diagnostic(input,options,null))+'\n');throw error}
};
