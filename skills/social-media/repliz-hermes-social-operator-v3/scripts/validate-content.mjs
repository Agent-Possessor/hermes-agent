#!/usr/bin/env node
import fs from 'node:fs';
const file=process.argv[2]; if(!file){console.error('Usage: validate-content.mjs payload.json');process.exit(2)}
let p; try{p=JSON.parse(fs.readFileSync(file,'utf8'))}catch(e){console.error(`Invalid JSON: ${e.message}`);process.exit(2)}
const errs=[]; const warns=[];
if(!p.accountId||typeof p.accountId!=='string') errs.push('accountId is required');
if(!p.type) errs.push('type is required');
if(!p.scheduleAt || Number.isNaN(Date.parse(p.scheduleAt))) errs.push('scheduleAt must be ISO-8601 with timezone');
if(p.scheduleAt && !/[zZ]|[+-]\d\d:\d\d$/.test(p.scheduleAt)) errs.push('scheduleAt must include timezone');
if(['image','video','reel','album','story'].includes(p.type) && (!Array.isArray(p.medias)||p.medias.length===0)) errs.push(`${p.type} requires medias[]`);
for(const [i,m] of (p.medias||[]).entries()){
 if(!m.url || !/^https:\/\//.test(m.url)) errs.push(`medias[${i}].url must be public https URL`);
 if(!m.type) errs.push(`medias[${i}].type is required`);
 if(m.alt && m.alt.length>300) warns.push(`medias[${i}].alt exceeds 300 characters`);
}
if((p.description||'').length>2200) warns.push('description exceeds 2200 chars; platform may reject or truncate');
if((p.description||'').match(/#\w+/g)?.length>30) warns.push('more than 30 hashtags');
const out={valid:errs.length===0,errors:errs,warnings:warns,checkedAt:new Date().toISOString()}; console.log(JSON.stringify(out,null,2)); process.exit(out.valid?0:1);
