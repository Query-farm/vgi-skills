#!/usr/bin/env python3
"""Recheck completed agent-generated workers against a selected SQL engine."""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=['duckdb', 'haybarn'], default='duckdb')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    package = 'duckdb==2.0.0' if args.engine == 'duckdb' else 'haybarn==2.0.0rc11'
    results = []
    for result_file in sorted((ROOT / '.eval-runs').glob('*/result.json')):
        run = json.loads(result_file.read_text())
        if not run['with_skill'] or not run['case'].endswith('-build') or run['status'] != 'passed':
            continue
        project = result_file.parent / 'project'
        completed = subprocess.run(['uv', 'run', '--with', package, 'python',
                                    str(ROOT / 'skills/vgi-worker/scripts/verify_worker.py'),
                                    '--project', str(project), '--engine', args.engine],
                                   capture_output=True, text=True, timeout=180)
        try:
            report = json.loads(completed.stdout)
        except json.JSONDecodeError:
            report = {'status': 'failed', 'error': 'Verifier did not return JSON'}
        # Worker launch paths and stderr can reveal local account data; do not publish them.
        public = {key: value for key, value in report.items() if key in {
            'status', 'engine', 'engine_version', 'extension_version', 'extension_repository',
            'platform', 'checks', 'elapsed_seconds', 'error_type', 'timeout_seconds'}}
        results.append({'run_id': result_file.parent.name, 'agent': run['agent'], 'case': run['case'],
                        'exit_code': completed.returncode, **public})
        print(f"{run['agent']} {run['case']}: {report['status']}", flush=True)
    summary = {'recorded_at': dt.datetime.now(dt.timezone.utc).isoformat(),
               'method': 'Reverification of previously agent-generated workers, without code changes. These timings are SQL rechecks, not new agent build timings.',
               'results': results}
    args.output.write_text(json.dumps(summary, indent=2) + '\n')
    return 0 if results and all(item['exit_code'] == 0 and item['status'] == 'passed' for item in results) else 1


if __name__ == '__main__':
    sys.exit(main())
