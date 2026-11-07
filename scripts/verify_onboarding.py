#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = ["duckdb==2.0.0", "pillow==13.0.0", "piexif==1.1.3"]
# ///
"""Independent assertions for the real onboarding conversations.

Expected results live outside generated projects. These checks ignore the
agent's expected rows and add unseen inputs after implementation.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
from onboarding_fixtures import photo

ROOT=Path(__file__).resolve().parents[1]

def quote(s):return "'"+str(s).replace("'","''")+"'"
def normalized(v):
    if isinstance(v,(datetime.datetime,datetime.date)):return v.isoformat()
    if isinstance(v,(list,tuple)):return [normalized(x) for x in v]
    return v

def verify(run,base_url):
    import duckdb
    meta=json.loads((run/'conversation.json').read_text());project=run/'project'
    manifests=[p for p in project.rglob('vgi-worker.json') if not any(part in {'.agents','.claude','node_modules','.venv'} for part in p.relative_to(project).parts)]
    if not manifests:raise ValueError('No worker verification manifest was produced')
    manifest=min(manifests,key=lambda p:len(p.relative_to(project).parts))
    os.chdir(manifest.parent)
    result={'status':'failed','case':meta['case'],'agent':meta['agent'],'language':meta['language'],'checks':[]}
    spec=json.loads(manifest.read_text())
    result['worker_project']=str(manifest.parent.relative_to(project))
    catalog={'files':'photos','api':'support','library':'validation'}[meta['case']]
    if spec['catalog']!=catalog:raise ValueError(f'Expected requested catalog {catalog}, got {spec["catalog"]}')
    with tempfile.TemporaryDirectory(prefix='vgi-onboarding-repositories-') as repos:
        con=duckdb.connect(':memory:',config={'extension_repository_directory':repos})
        try:
            con.execute("SET allow_extension_repositories='allowed'")
            con.execute("CREATE EXTENSION REPOSITORY query_farm WITH PREFIX 'https://duckdb-extensions.query.farm'")
            con.execute('INSTALL vgi FROM query_farm; LOAD vgi FROM query_farm')
            result.update(engine_version=duckdb.__version__,extension_version=con.execute("SELECT extension_version FROM duckdb_extensions() WHERE extension_name='vgi'").fetchone()[0])
            attach=f'ATTACH {quote(catalog)} AS {catalog} (TYPE vgi, LOCATION {quote(shlex.join(spec["worker"]))})'
            con.execute(attach);result['attach_sql']=attach
            def check(name,sql,expected=None,error=False):
                entry={'name':name,'sql':sql,'status':'failed'}
                try:
                    rows=normalized(con.execute(sql).fetchall());entry['rows']=rows
                    if error:entry['error']='Expected an explicit SQL error, got rows'
                    elif rows==expected:entry['status']='passed'
                    else:entry['expected_rows']=expected
                except Exception as exc:
                    entry['error']=str(exc)
                    if error:entry['status']='passed'
                result['checks'].append(entry)
            check('attached catalog schema',f"SELECT count(*) FROM information_schema.schemata WHERE catalog_name={quote(catalog)} AND schema_name='main'",[[1]])
            name={'files':'files','api':'tickets','library':'is_valid_sku'}[meta['case']]
            check('function is discoverable',f"SELECT count(*) FROM duckdb_functions() WHERE database_name={quote(catalog)} AND schema_name='main' AND function_name={quote(name)}",[[1]])
            if meta['case']=='files':
                folder=project/'inputs/photos';empty=project/'inputs/empty'
                table=f'photos.main.files({quote(folder)})'
                check('metadata, dates, and signed GPS',f"SELECT regexp_extract(path,'[^/]+$'), camera_model, replace(left(CAST(taken_at AS VARCHAR),10),':','-'), round(latitude,4), round(longitude,4) FROM {table} ORDER BY 1",[
                    ['north.jpg','Fixture Camera A','2025-01-02',40.5,-73.75],['plain.jpg',None,None,None,None],['south.jpg','Fixture Camera B','2024-06-15',-33.875,151.2]])
                check('actual file sizes',f"SELECT regexp_extract(path,'[^/]+$'), size_bytes FROM {table} ORDER BY 1",[[p.name,p.stat().st_size] for p in sorted(folder.glob('*.jpg')) if p.name!='broken.jpg'])
                check('empty folder',f'SELECT count(*) FROM photos.main.files({quote(empty)})',[[0]])
                check('null folder','SELECT count(*) FROM photos.main.files(NULL::VARCHAR)',[[0]])
                check('repeat scans',f'SELECT count(*) FROM {table}',[[3]])
                holdout=folder/'new-photo.jpg'
                try:
                    photo(holdout,'Holdout Camera','2026:02:03 04:05:06')
                    check('new input discovered without rebuilding',f"SELECT camera_model FROM {table} WHERE path LIKE '%new-photo.jpg'",[['Holdout Camera']])
                finally:holdout.unlink(missing_ok=True)
            elif meta['case']=='api':
                if not base_url:raise ValueError('--base-url required for API checks')
                call=lambda variant:f'support.main.tickets({quote(base_url+"/"+variant)})'
                check('all API pages',f'SELECT ticket_id,customer_id,status,subject FROM {call("normal")} ORDER BY ticket_id',[[101,1,'open','Login'],[102,2,'closed','Invoice'],[103,1,'open','Export'],[104,3,'open','Setup']])
                check('join keeps customers with zero open tickets',f"SELECT c.customer_name, count(t.ticket_id) FROM read_csv({quote(project/'inputs/customers.csv')}) c LEFT JOIN {call('normal')} t ON c.customer_id=t.customer_id AND t.status='open' GROUP BY c.customer_name ORDER BY c.customer_name",[['Northwind',2],['Redwood',1],['Seabrook',0]])
                check('empty API',f'SELECT count(*) FROM {call("empty")}',[[0]])
                check('null URL','SELECT count(*) FROM support.main.tickets(NULL::VARCHAR)',[[0]])
                check('unseen API response',f'SELECT ticket_id,subject FROM {call("holdout")}',[[907,'Unseen ticket']])
                check('multiple Arrow batches',f'SELECT count(*),sum(ticket_id) FROM {call("large")}',[[10001,50015001]])
                for variant in ['error','rate-limit','malformed','loop']:
                    check(f'{variant} is not an empty success',f'SELECT * FROM {call(variant)}',error=True)
            else:
                check('library semantics',"SELECT validation.main.is_valid_sku(v) FROM (VALUES ('ABC-1234'),('QRS-0000'),('abc-1234'),('ZZZ-9999'),('ABC-12'),('ABC-1234 '),('ÉBC-1234'),('ABC-1234\\n')) t(v)",[[True],[True],[False],[False],[False],[False],[False],[False]])
                check('null propagation','SELECT validation.main.is_valid_sku(NULL::VARCHAR)',[[None]])
                check('invalid CSV records',f"SELECT record_id FROM read_csv({quote(project/'inputs/products.csv')}, all_varchar=true) WHERE NOT validation.main.is_valid_sku(sku) ORDER BY record_id",[['2'],['4'],['7']])
                check('missing values stay separate',f"SELECT record_id FROM read_csv({quote(project/'inputs/products.csv')}, all_varchar=true) WHERE sku IS NULL ORDER BY record_id",[['6']])
                check('multiple input batches',"SELECT count(*) FROM range(10000) WHERE validation.main.is_valid_sku('ABC-' || lpad(range::VARCHAR,4,'0'))",[[10000]])
                check('empty input',"SELECT count(*) FROM (SELECT validation.main.is_valid_sku(i::VARCHAR) FROM range(0) t(i))",[[0]])
            changed=[]
            for name,digest in json.loads((run/'input-hashes.json').read_text()).items():
                p=project/name
                if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:changed.append(name)
            result['checks'].append({'name':'input files unchanged','status':'passed' if not changed else 'failed','changed':changed})
            result['status']='passed' if all(x['status']=='passed' for x in result['checks']) else 'failed'
            con.execute(f'DETACH {catalog}')
        finally:con.close()
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--base-url');p.add_argument('--child',action='store_true');p.add_argument('--timeout',type=int,default=150)
    args=p.parse_args();run=args.run.resolve()
    if args.child:
        try: result=verify(run,args.base_url)
        except Exception as exc:result={'status':'failed','error':str(exc)}
        print(json.dumps(result,indent=2));return 0 if result['status']=='passed' else 1
    command=[sys.executable,__file__,str(run),'--child']+(['--base-url',args.base_url] if args.base_url else [])
    with (run/'oracle.json').open('w') as out,(run/'oracle.stderr.txt').open('w') as err:
        proc=subprocess.Popen(command,stdout=out,stderr=err,text=True,start_new_session=True)
        try:code=proc.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait();code=124
            (run/'oracle.json').write_text(json.dumps({'status':'failed','error':'Independent verification timed out'})+'\n')
    result=json.loads((run/'oracle.json').read_text())
    print(json.dumps({'run':str(run),'status':result['status'],'checks':[(x['name'],x['status']) for x in result.get('checks',[])],'error':result.get('error')},indent=2))
    return code
if __name__=='__main__':raise SystemExit(main())
