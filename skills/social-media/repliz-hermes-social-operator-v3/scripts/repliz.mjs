#!/usr/bin/env node
import crypto from 'node:crypto'; import fs from 'node:fs'; import {spawnSync} from 'node:child_process';
const [,,rawMethod,rawPath,bodyArg,...rest]=process.argv;
const tokenIndex=rest.indexOf('--approval-token'); const token=tokenIndex>=0?rest[tokenIndex+1]:undefined;
const method=(rawMethod||'').toUpperCase(), path=rawPath;
const key=process.env.REPLIZ_ACCESS_KEY, secret=process.env.REPLIZ_SECRET_KEY, base=process.env.REPLIZ_BASE_URL||'https://api.repliz.com';
if(!method||!path||!key||!secret){console.error('Usage: repliz.mjs METHOD PATH [payload.json|json] [--approval-token token]');process.exit(2)}
const mut=!['GET','HEAD','OPTIONS'].includes(method); let body=null;
if(bodyArg){ try{body=fs.existsSync(bodyArg)?fs.readFileSync(bodyArg,'utf8'):bodyArg; JSON.parse(body)}catch(e){console.error(`Invalid JSON body: ${e.message}`);process.exit(2)} }
const payloadHash=crypto.createHash('sha256').update(body||'').digest('hex');
function fail(msg,code=3){console.error(msg);process.exit(code)}
if(mut){
 if(!token) fail('Mutation refused: a payload-bound approval token is required.');
 const [v,enc,sig]=token.split('.'); const signing=process.env.REPLIZ_APPROVAL_SIGNING_KEY;
 if(v!=='v1'||!enc||!sig||!signing) fail('Invalid token or missing REPLIZ_APPROVAL_SIGNING_KEY');
 const expected=crypto.createHmac('sha256',signing).update(enc).digest('base64url');
 if(!crypto.timingSafeEqual(Buffer.from(sig),Buffer.from(expected))) fail('Invalid approval signature');
 let c;try{c=JSON.parse(Buffer.from(enc,'base64url').toString())}catch{fail('Unreadable approval token')}
 if(c.exp<Date.now()||c.method!==method||c.path!==path||c.payloadHash!==payloadHash) fail('Approval token does not bind this exact mutation');
 const used=spawnSync('python3',['scripts/audit.py','consume-token','--jti',c.jti],{cwd:new URL('.',import.meta.url).pathname,encoding:'utf8'});
 if(used.status!==0) fail(`Approval token refused: ${used.stdout||used.stderr}`);
}
const url=new URL(path,base); const auth=Buffer.from(`${key}:${secret}`).toString('base64');
let res; try{res=await fetch(url,{method,headers:{Authorization:`Basic ${auth}`,...(body?{'Content-Type':'application/json'}:{})},body:body||undefined})}catch(e){
 const event={ts:new Date().toISOString(),event_type:'network_uncertain',method,path,payload_hash:payloadHash,result:{message:e.message}}; spawnSync('python3',['scripts/audit.py','event','--json',JSON.stringify(event)],{cwd:new URL('.',import.meta.url).pathname,encoding:'utf8'}); fail('Network uncertainty. Do NOT retry a mutation automatically; verify target state first.',5)
}
const text=await res.text(); let data;try{data=text?JSON.parse(text):null}catch{data=text}
const event={ts:new Date().toISOString(),event_type:'http',method,path,status:res.status,payload_hash:payloadHash,result:{ok:res.ok,bodyType:typeof data}};
spawnSync('python3',['scripts/audit.py','event','--json',JSON.stringify(event)],{cwd:new URL('.',import.meta.url).pathname,encoding:'utf8'});
console.log(JSON.stringify({status:res.status,ok:res.ok,data},null,2)); process.exit(res.ok?0:1);
