#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = ["duckdb==2.0.0"]
# ///
"""Reproduce the saved agent build's checks and photo catalog query."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import duckdb

ROOT=Path(__file__).resolve().parent
WORKER=ROOT/'photo_worker'

def quote(value):return "'"+str(value).replace("'","''")+"'"

def main():
    verifier=ROOT/'tools/verify_worker.py'
    if not verifier.exists():verifier=ROOT.parents[1]/'skills/vgi-worker/scripts/verify_worker.py'
    subprocess.run(['uv','run','--frozen','python','tests/make_fixtures.py'],cwd=WORKER,check=True)
    subprocess.run([sys.executable,str(verifier),'--project',str(WORKER),'--output',str(ROOT/'verification.json')],check=True)
    argv=['uv','run','--frozen','--project',str(WORKER),'python',str(WORKER/'photo_worker.py')]
    attach=f"ATTACH 'photos' AS photos (TYPE vgi, LOCATION {quote(shlex.join(argv))});"
    query=f"SELECT coalesce(camera_model, '(unknown)') AS camera, year(taken_at) AS year, count(*) AS photos FROM photos.main.files({quote(ROOT/'inputs/photos')}) GROUP BY ALL ORDER BY camera;"
    with tempfile.TemporaryDirectory(prefix='photo-demo-repository-') as directory:
        con=duckdb.connect(':memory:',config={'extension_repository_directory':directory})
        try:
            con.execute("SET allow_extension_repositories='allowed'; CREATE EXTENSION REPOSITORY query_farm WITH PREFIX 'https://duckdb-extensions.query.farm'; INSTALL vgi FROM query_farm; LOAD vgi FROM query_farm;")
            con.execute(attach)
            rows=con.execute(query).fetchall()
            expected=[('(unknown)',None,1),('Fixture Camera A',2025,1),('Fixture Camera B',2024,1)]
            if rows!=expected:raise AssertionError(f'Unexpected photo result: {rows}')
            report={'columns':['camera','year','photos'],'rows':rows,'attach_sql':attach,'sql':query,'status':'passed'}
            (ROOT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(report,indent=2))
            con.execute('DETACH photos')
        finally:con.close()
if __name__=='__main__':main()
