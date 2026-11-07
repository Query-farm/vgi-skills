#!/usr/bin/env python3
"""Run two fresh native-agent builds to exercise starter selection and adaptation.

Uses authenticated local CLIs and their configured defaults. Consumes account
usage. Review results, then run verify_starter_build.py for each run directory.
Raw account-specific events stay in ignored .eval-runs.
"""
import sys,json,subprocess,datetime,uuid,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
from evaluate_onboarding import command,execute,BOUNDARIES

def run(agent,language):
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');run=ROOT/'.eval-runs/starter-integration/agents'/f'{stamp}-{agent}-{uuid.uuid4().hex[:8]}';project=run/'project';project.mkdir(parents=True)
 subprocess.run(['git','init','-q',str(project)],check=True)
 with (run/'install.log').open('w') as log:
  subprocess.run(['npx','--yes','skills','add',str(ROOT),'--skill','vgi-worker','--agent',{'codex':'codex','claude':'claude-code'}[agent],'--copy','--yes'],cwd=project,stdout=log,stderr=subprocess.STDOUT,check=True)
 boundary=project/('AGENTS.md' if agent=='codex' else 'CLAUDE.md');boundary.write_text(BOUNDARIES)
 prompt=f"Use the vgi-worker skill. Build a {language} VGI worker exposing badge.main.initials(name VARCHAR) -> VARCHAR. Return the uppercase first character of each whitespace-separated word. Empty or whitespace-only input returns an empty string; SQL NULL stays NULL. For example 'Ada Lovelace' returns 'AL' and '  grace   hopper  ' returns 'GH'. Build this locally, verify it through stock DuckDB 2.0.0 with VGI from query_farm, and leave repeatable tests and the exact ATTACH and query commands. Do not publish or deploy."
 result={'agent':agent,'language':language,'agent_version':subprocess.check_output([agent,'--version'],text=True).strip(),'prompt':prompt,'status':'running'}
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');prefix=run/'turn-1'
 turn=execute(command(agent,project,prefix),project,prompt,prefix,1200)
 result.update(turn=turn,status='awaiting_review' if turn['exit_code']==0 else 'agent_error',boundary_unchanged=boundary.read_text()==BOUNDARIES)
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'run':str(run),'agent':agent,'status':result['status'],'seconds':turn['seconds']}),flush=True)
if __name__ == '__main__':
 with ThreadPoolExecutor(max_workers=2) as pool:
  futures=[pool.submit(run,'codex','Python'),pool.submit(run,'claude','TypeScript')]
  for future in futures:future.result()
