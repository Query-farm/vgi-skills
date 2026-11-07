#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = ["duckdb==2.0.0"]
# ///
"""Recheck an agent-built starter and verify initials with independent SQL."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import time

import duckdb


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    meta = json.loads((run / 'result.json').read_text())
    if meta['status'] == 'running':
        raise SystemExit('Wait for the agent to finish before verifying its project')
    candidates = [p for p in (run / 'project').rglob('.vgi-starter.json')
                  if not any(x in p.parts for x in ('.agents', '.claude', 'node_modules', '.venv'))]
    if len(candidates) != 1:
        raise SystemExit(f'Expected one initialized starter, found {len(candidates)}')
    project = candidates[0].parent
    provenance = json.loads(candidates[0].read_text())
    language = meta['language'].lower()
    if provenance.get('name') != 'badge' or provenance.get('lang') != language:
        raise SystemExit(f'Wrong catalog or language in starter provenance: {provenance}')

    started = time.monotonic()
    with (run / 'independent-make-check.log').open('w') as log:
        check = subprocess.run(['make', 'check'], cwd=project, stdout=log,
                               stderr=subprocess.STDOUT, timeout=600)
    report = {'language': language, 'starter': provenance['template'],
              'template_version': provenance['template_version'],
              'make_check_exit_code': check.returncode,
              'make_check_seconds': round(time.monotonic() - started, 2),
              'engine': duckdb.__version__, 'checks': []}
    worker = subprocess.check_output(
        ['make', '-s', '-f', 'Makefile', '-f', '-', 'vgi-eval-worker'],
        input='vgi-eval-worker:\n\t@echo $(WORKER)\n', cwd=project, text=True).strip()
    cases = [
        ('catalog discovery', "SELECT count(*) FROM information_schema.schemata WHERE catalog_name='badge' AND schema_name='main'", [(1,)]),
        ('provided examples', "SELECT badge.main.initials('Ada Lovelace'),badge.main.initials('  grace   hopper  ')", [('AL', 'GH')]),
        ('unseen names and whitespace', "SELECT badge.main.initials('katherine' || chr(9) || 'coleman' || chr(10) || 'johnson'),badge.main.initials('mIxEd')", [('KCJ', 'M')]),
        ('empty input', "SELECT badge.main.initials(''),badge.main.initials('   ')", [('', '')]),
        ('NULL propagation', 'SELECT badge.main.initials(NULL::VARCHAR)', [(None,)]),
        ('multiple batches', "SELECT count(*) FROM range(10000) WHERE badge.main.initials('Ada Lovelace ' || range::VARCHAR) = 'AL' || left(range::VARCHAR,1)", [(10000,)]),
        ('result type', "SELECT typeof(badge.main.initials('Ada Lovelace'))", [('VARCHAR',)]),
    ]
    try:
        with tempfile.TemporaryDirectory(prefix='starter-agent-repositories-') as repos:
            con = duckdb.connect(':memory:', config={'extension_repository_directory': repos})
            try:
                con.execute("SET allow_extension_repositories='allowed'; CREATE EXTENSION REPOSITORY query_farm WITH PREFIX 'https://duckdb-extensions.query.farm'; INSTALL vgi FROM query_farm; LOAD vgi FROM query_farm;")
                report['extension'] = con.execute("SELECT extension_version FROM duckdb_extensions() WHERE extension_name='vgi'").fetchone()[0]
                con.execute(f"ATTACH 'badge' AS badge (TYPE vgi, LOCATION {quote(shlex.quote(worker))})")
                for name, sql, expected in cases:
                    rows = con.execute(sql).fetchall()
                    report['checks'].append({'name': name, 'sql': sql, 'rows': rows,
                                             'status': 'passed' if rows == expected else 'failed'})
                con.execute('DETACH badge')
            finally:
                con.close()
    except Exception as exc:
        report['error'] = str(exc)
    report['status'] = 'passed' if (not report.get('error') and check.returncode == 0
                                   and len(report['checks']) == len(cases)
                                   and all(c['status'] == 'passed' for c in report['checks'])) else 'failed'
    (run / 'independent-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
