#!/usr/bin/env node
const format=process.argv.includes('--format')?process.argv[process.argv.indexOf('--format')+1]:'json';
const base=process.env.REPLIZ_BASE_URL||'https://api.repliz.com',key=process.env.REPLIZ_ACCESS_KEY,secret=process.env.REPLIZ_SECRET_KEY;
if(!key||!secret){console.error('Missing Repliz credentials');process.exit(2)}
const auth=Buffer.from(`${key}:${secret}`).toString('base64');
async function get(path){const r=await fetch(new URL(path,base),{headers:{Authorization:`Basic ${auth}`}}); const t=await r.text();let d;try{d=JSON.parse(t)}catch{d={raw:t}};return {status:r.status,data:d}}
const checks=[];
for(const c of [
 ['accounts','/public/account?page=1&limit=100'],
 ['failed_schedules','/public/schedule?page=1&limit=100&status=failed'],
 ['pending_comments','/public/comment?page=1&limit=100&status=pending']
]){try{const r=await get(c[1]); checks.push({check:c[0],status:r.status,count:Array.isArray(r.data?.docs)?r.data.docs.length:null,ok:r.status>=200&&r.status<300})}catch(e){checks.push({check:c[0],ok:false,error:e.message})}}
const alerts=checks.filter(x=>!x.ok || (['failed_schedules','pending_comments'].includes(x.check)&&Number(x.count)>0)); const out={checkedAt:new Date().toISOString(),checks,alerts};
if(format==='markdown'){console.log(`# Repliz monitor\n\nChecked: ${out.checkedAt}\n\n${checks.map(c=>`- ${c.check}: ${c.ok?'OK':'ERROR'}${c.count!==null?` (${c.count})`:''}`).join('\n')}`)}else console.log(JSON.stringify(out,null,2));
process.exit(alerts.length?1:0);
