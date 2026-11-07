#!/usr/bin/env python3
"""Run the three exact website requests through two-turn agent conversations.

Requires the local fixture service started with onboarding_fixtures.py serve.
Each case/language/agent gets an isolated project and fresh session. Review the
saved first-turn answers and oracle failures before publishing an evaluation.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def run_case(agent,case,language,website,base_url,attempt):
    start=[sys.executable,str(ROOT/'scripts/evaluate_onboarding.py'),'start','--agent',agent,'--case',case,'--language',language,'--attempt',attempt,'--website-source',str(website)]
    proc=subprocess.run(start,cwd=ROOT,capture_output=True,text=True)
    if proc.returncode:return {'agent':agent,'case':case,'language':language,'status':'start_error','detail':proc.stdout[-2500:]+proc.stderr[-1000:]}
    initial=json.loads(proc.stdout);run=Path(initial['run'])
    metadata=json.loads((run/'conversation.json').read_text())
    if metadata['files_created_before_language'] or metadata['files_changed_before_language']:
        return {'run':str(run),'status':'wrote_before_language','created':metadata['files_created_before_language']}
    prep=['uv','run',str(ROOT/'scripts/onboarding_fixtures.py'),'prepare',str(run),'--base-url',base_url]
    proc=subprocess.run(prep,cwd=ROOT,capture_output=True,text=True)
    if proc.returncode:return {'run':str(run),'status':'fixture_error','detail':proc.stderr[-1000:]}
    follow=[sys.executable,str(ROOT/'scripts/evaluate_onboarding.py'),'continue',str(run),'--reply-file',str(run/'reply.txt')]
    proc=subprocess.run(follow,cwd=ROOT,capture_output=True,text=True)
    (run/'driver-followup.txt').write_text(proc.stdout+proc.stderr)
    if proc.returncode:return {'run':str(run),'status':'agent_error'}
    oracle=['uv','run',str(ROOT/'scripts/verify_onboarding.py'),str(run),'--base-url',base_url]
    proc=subprocess.run(oracle,cwd=ROOT,capture_output=True,text=True)
    (run/'driver-oracle.txt').write_text(proc.stdout+proc.stderr)
    if not (run/'oracle.json').exists():return {'run':str(run),'status':'oracle_error','detail':proc.stderr[-1000:]}
    result=json.loads((run/'oracle.json').read_text())
    return {'run':str(run),'agent':agent,'case':case,'language':language,'status':result['status'],'checks':[(x['name'],x['status']) for x in result.get('checks',[])],'error':result.get('error')}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--website-source',type=Path,required=True);p.add_argument('--base-url-file',type=Path,required=True)
    p.add_argument('--agents',nargs='+',choices=['codex','claude'],default=['codex','claude'])
    p.add_argument('--cases',nargs='+',choices=['api','files','library'],default=['api','files','library'])
    p.add_argument('--languages',nargs='+',choices=['python','typescript'],default=['python','typescript'])
    p.add_argument('--skip-files-python',action='store_true');p.add_argument('--attempt',default='1')
    p.add_argument('--workers',type=int,default=2)
    args=p.parse_args();base=args.base_url_file.read_text().strip()
    jobs=[(agent,case,language) for language in args.languages for case in args.cases for agent in args.agents if not(args.skip_files_python and case=='files' and language=='python')]
    failed=False
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending={pool.submit(run_case,*job,args.website_source,base,args.attempt):job for job in jobs}
        for future in as_completed(pending):
            try:result=future.result()
            except Exception as exc:result={'job':pending[future],'status':'driver_error','error':str(exc)}
            print(json.dumps(result),flush=True)
            failed |= result['status']!='passed'
    return 1 if failed else 0
if __name__=='__main__':raise SystemExit(main())
