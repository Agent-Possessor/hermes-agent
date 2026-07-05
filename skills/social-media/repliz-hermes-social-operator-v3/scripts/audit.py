#!/usr/bin/env python3
import argparse, hashlib, json, os, sqlite3, sys, time
from pathlib import Path
DB = Path(os.environ.get('REPLIZ_AUDIT_DB', Path.home()/'.hermes/repliz/audit.sqlite3'))

def conn():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DB)
    c.execute('''CREATE TABLE IF NOT EXISTS audit_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, event_type TEXT NOT NULL,
      action TEXT, method TEXT, path TEXT, fingerprint TEXT, status INTEGER,
      payload_hash TEXT, result_json TEXT, prev_hash TEXT, event_hash TEXT NOT NULL)''')
    c.execute('CREATE TABLE IF NOT EXISTS used_tokens (jti TEXT PRIMARY KEY, used_at TEXT NOT NULL)')
    return c

def emit(event):
    c=conn(); prev=c.execute('SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1').fetchone()
    prev_hash=prev[0] if prev else ''
    canonical=json.dumps(event, sort_keys=True, separators=(',', ':'))
    digest=hashlib.sha256((prev_hash+'|'+canonical).encode()).hexdigest()
    c.execute('INSERT INTO audit_events(ts,event_type,action,method,path,fingerprint,status,payload_hash,result_json,prev_hash,event_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
      (event.get('ts'),event.get('event_type'),event.get('action'),event.get('method'),event.get('path'),event.get('fingerprint'),event.get('status'),event.get('payload_hash'),json.dumps(event.get('result',{}),separators=(',',':')),prev_hash,digest))
    c.commit(); print(json.dumps({'ok':True,'event_hash':digest,'db':str(DB)}))

def consume(jti):
    c=conn()
    try:
      c.execute('INSERT INTO used_tokens(jti,used_at) VALUES(?,datetime("now"))',(jti,)); c.commit(); print(json.dumps({'ok':True}))
    except sqlite3.IntegrityError:
      print(json.dumps({'ok':False,'reason':'token_already_used'})); sys.exit(4)

p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
e=sub.add_parser('event'); e.add_argument('--json',required=True)
u=sub.add_parser('consume-token'); u.add_argument('--jti',required=True)
a=p.parse_args()
if a.cmd=='event': emit(json.loads(a.json))
else: consume(a.jti)
