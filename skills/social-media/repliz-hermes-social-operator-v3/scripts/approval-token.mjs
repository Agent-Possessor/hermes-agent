#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
const args=process.argv.slice(2);
const get=(name)=>{const i=args.indexOf(name); return i>=0?args[i+1]:undefined};
const command=args[0];
if(command!=='issue'){ console.error('Usage: approval-token.mjs issue --action A --method M --path P --payload FILE --ttl-minutes N'); process.exit(2); }
const secret=process.env.REPLIZ_APPROVAL_SIGNING_KEY;
if(!secret){console.error('Missing REPLIZ_APPROVAL_SIGNING_KEY');process.exit(2)}
const action=get('--action'), method=get('--method')?.toUpperCase(), path=get('--path'), file=get('--payload');
const ttl=Number(get('--ttl-minutes')||10);
if(!action||!method||!path||!file||!Number.isFinite(ttl)||ttl<1||ttl>60){console.error('Invalid arguments; TTL must be 1-60 minutes');process.exit(2)}
const raw=fs.readFileSync(file); const payloadHash=crypto.createHash('sha256').update(raw).digest('hex');
const claims={v:1,jti:crypto.randomUUID(),action,method,path,payloadHash,iat:Date.now(),exp:Date.now()+ttl*60_000};
const encoded=Buffer.from(JSON.stringify(claims)).toString('base64url');
const sig=crypto.createHmac('sha256',secret).update(encoded).digest('base64url');
console.log(`v1.${encoded}.${sig}`);
