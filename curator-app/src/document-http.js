import {documentLibrary,readDocumentPage,resolveEvidence,validRecordId} from './document-repository.js';
import {searchPapers} from './research-query.js';

export async function handleDocumentRead(request,env,{publicOnly=true}={}){
 const url=new URL(request.url),h={'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...(publicOnly?{'Access-Control-Allow-Origin':'https://colazeta.github.io','Vary':'Origin'}:{})};
 const error=(code,status)=>Response.json({error:code},{status,headers:h});
 if(request.method==='OPTIONS'&&publicOnly)return new Response(null,{status:204,headers:{...h,'Access-Control-Allow-Methods':'GET'}});
 if(request.method!=='GET')return error('method_not_allowed',405);
 const allowed=['id','document','page','query','cursor','evidence','revision'];
 if([...url.searchParams.keys()].some(k=>!allowed.includes(k)||url.searchParams.getAll(k).length!==1))return error('invalid_request',400);
 const id=url.searchParams.get('id'),document=url.searchParams.get('document'),page=url.searchParams.get('page'),evidence=url.searchParams.get('evidence');
 if(id&&!validRecordId(id)||document&&!/^[a-f0-9]{64}$/.test(document)||page&&!/^\d{1,3}$/.test(page)||url.search.length>2500)return error('invalid_request',400);
 try{
  let result;
  if(evidence){if(!id||document||page||evidence.length>160)return error('invalid_request',400);result=await resolveEvidence(env,id,[evidence],{publicOnly,expectedRevision:url.searchParams.get('revision')})}
  else if(document||page){if(!id||!document||!page)return error('invalid_request',400);result=await readDocumentPage(env,id,document,Number(page),{publicOnly})}
  else if(id)result=await documentLibrary(env,id,{publicOnly});
  else {const query=url.searchParams.get('query')||'',cursor=url.searchParams.get('cursor');if(query.length>300)return error('invalid_request',400);result=await searchPapers(env,{query,cursor,limit:20},{publicOnly})}
  const text=JSON.stringify(result);if(text.length>150000)return error('response_limit',422);
  return new Response(text,{headers:h});
 }catch(e){return error(e.code&&/^(document|extraction|paper|page|evidence|invalid|review)_[a-z_]+$/.test(e.code)?e.code:'document_library_unavailable',[400,404,409,422].includes(e.status)?e.status:503)}
}
export async function serveDocumentRead(request,store){
 if(!store)return Response.json({error:'document_library_unavailable'},{status:503,headers:{'Cache-Control':'no-store','Access-Control-Allow-Origin':'https://colazeta.github.io'}});
 const url=new URL(request.url);url.protocol='https:';url.host='enrichment.internal';url.pathname='/document-library';
 return store.fetch(new Request(url,request));
}
