#!/usr/bin/env python3
"""Exercise the website requests as real, resumable agent conversations.

No model override. Session files and raw events remain in ignored .eval-runs.
The first user turn is byte-for-byte the website request; boundaries are project
instructions, with no solution or verification manifest supplied to the agent.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
REQUESTS = {x['id']: x['prompt'] for x in json.loads((ROOT/'evals/onboarding/requests.json').read_text())}
BOUNDARIES = '''# Evaluation workspace
Work only in this project and temporary build/test directories. Do not read
parent or sibling projects, previous agent sessions, unrelated repositories,
or user files. Public documentation and package downloads are available.
Do not spawn or delegate to other agents. Keep this project local: no publishing,
deployment, account creation, or external writes. Read-only local fixture services
and disposable test files are authorized. Preserve input data and library files.
'''
IGNORED = {'.git','.agents','.claude','node_modules','.venv','__pycache__','.pytest_cache'}

def snapshot(project):
    return {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in project.rglob('*') if p.is_file() and not any(x in IGNORED for x in p.relative_to(project).parts)}

def execute(command, project, prompt, prefix, timeout):
    prefix.with_suffix('.prompt.txt').write_text(prompt)
    start=time.monotonic()
    with prefix.with_suffix('.events.jsonl').open('w') as out, prefix.with_suffix('.stderr.txt').open('w') as err:
        proc=subprocess.Popen(command,cwd=project,stdin=subprocess.PIPE,stdout=out,stderr=err,text=True,start_new_session=True)
        try:
            proc.communicate(prompt, timeout=timeout)
            code=proc.returncode
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.communicate();code=124
    events=[]
    for line in prefix.with_suffix('.events.jsonl').read_text().splitlines():
        try: events.append(json.loads(line))
        except json.JSONDecodeError: pass
    response='';session=None;model=None;denials=[]
    for event in events:
        session=event.get('thread_id') or event.get('session_id') or session
        if event.get('type')=='system' and event.get('subtype')=='init':model=event.get('model')
        if event.get('type')=='item.completed' and event.get('item',{}).get('type')=='agent_message':response=event['item'].get('text','')
        if event.get('type')=='result':
            response=event.get('result','')
            denials=event.get('permission_denials',[])
            if event.get('is_error') and code==0:code=1
    response_file=prefix.with_suffix('.response.txt')
    if response:response_file.write_text(response)
    elif response_file.exists():response=response_file.read_text()
    return {'exit_code':code,'seconds':round(time.monotonic()-start,2),'session_id':session,'model':model,'response':response,'permission_denials':denials}

def command(agent, project, prefix, session=None):
    if agent=='codex':
        base=['codex','exec','-s','danger-full-access','-c','approval_policy="never"','-C',str(project)]
        if session:return base+['resume','--json','-o',str(prefix.with_suffix('.response.txt')),session,'-']
        return base+['--json','-o',str(prefix.with_suffix('.response.txt')),'-']
    base=['claude','-p','--output-format','stream-json','--verbose','--permission-mode','acceptEdits',
          '--allowedTools','Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch,Skill',
          '--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--setting-sources','']
    return base+(['--resume',session] if session else [])

def save(run, result):
    (run/'conversation.json').write_text(json.dumps(result,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    subs=p.add_subparsers(dest='action',required=True)
    start=subs.add_parser('start')
    start.add_argument('--agent',choices=['codex','claude'],required=True)
    start.add_argument('--case',choices=list(REQUESTS),required=True)
    start.add_argument('--language',choices=['python','typescript'],required=True,help='Evaluation answer, not exposed in the first turn')
    start.add_argument('--attempt',default='1')
    start.add_argument('--website-source',type=Path,required=True)
    start.add_argument('--timeout',type=int,default=180)
    follow=subs.add_parser('continue')
    follow.add_argument('run',type=Path)
    follow.add_argument('--reply-file',type=Path,required=True)
    follow.add_argument('--timeout',type=int,default=900)
    args=p.parse_args()
    if args.action=='start':
        prompt=REQUESTS[args.case]
        if prompt not in args.website_source.read_text():raise SystemExit('Website prompt drift: update reviewed requests.json first')
        stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        run=ROOT/'.eval-runs'/'onboarding'/f'{stamp}-{args.agent}-{args.case}-{args.language}-{args.attempt}'
        project=run/'project';project.mkdir(parents=True)
        subprocess.run(['git','init','-q',str(project)],check=True)
        with (run/'install.txt').open('w') as log:
            install=subprocess.run(['npx','--yes','skills','add',str(ROOT),'--skill','vgi-worker','--agent',{'codex':'codex','claude':'claude-code'}[args.agent],'--copy','--yes'],cwd=project,stdout=log,stderr=subprocess.STDOUT,timeout=120)
        if install.returncode:raise SystemExit(f'Installation failed: {run}')
        skill=project/('.agents' if args.agent=='codex' else '.claude')/'skills'/'vgi-worker'
        if not (skill/'SKILL.md').exists():raise SystemExit('Skill not installed in expected directory')
        (project/('AGENTS.md' if args.agent=='codex' else 'CLAUDE.md')).write_text(BOUNDARIES)
        result={'agent':args.agent,'case':args.case,'language':args.language,'attempt':args.attempt,
                'started_at':stamp,'website_prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                'agent_version':subprocess.check_output([args.agent,'--version'],text=True).strip(),
                'skill_sha256':hashlib.sha256((skill/'SKILL.md').read_bytes()).hexdigest(),
                'initial_files':snapshot(project),'turns':[],'status':'running'}
        save(run,result)
    else:
        run=args.run.resolve();project=run/'project'
        result=json.loads((run/'conversation.json').read_text())
        prompt=args.reply_file.read_text()
    result['status']='running'
    save(run,result)
    number=len(result['turns'])+1
    prefix=run/f'turn-{number}'
    session=result['turns'][-1]['session_id'] if result['turns'] else None
    turn=execute(command(result['agent'],project,prefix,session),project,prompt,prefix,args.timeout)
    if session and turn['session_id'] != session:
        turn['resume_error']='Agent returned a different session ID'
        turn['exit_code']=1
    turn['prompt']=prompt
    result['turns'].append(turn)
    if number==1:
        after=snapshot(project)
        result['files_created_before_language']=[name for name in after if name not in result['initial_files']]
        result['files_changed_before_language']=[name for name in after if name in result['initial_files'] and after[name]!=result['initial_files'][name]]
    result['status']='awaiting_review' if turn['exit_code']==0 else 'agent_error'
    save(run,result)
    print(json.dumps({'run':str(run),'agent':result['agent'],'case':result['case'],'language':result['language'],'turn':number,'status':result['status'],'seconds':turn['seconds'],'response':turn['response'][:2200]},indent=2))
    return turn['exit_code']

if __name__=='__main__':raise SystemExit(main())
