#!/usr/bin/env python3
"""Publish reviewed onboarding evidence without raw events or session IDs."""
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'evals/onboarding'
CRITERIA = (
    'skill_read', 'asked_language_and_source', 'used_chosen_language',
    'used_supplied_source', 'ran_sql_checks', 'usable_sql_handoff',
)


def portable(text, project):
    text = text.replace(str(project), '<project>')
    text = re.sub(r'/Users/[^/\s]+', '<home>', text)
    return re.sub(r'http://127\.0\.0\.1:\d+', 'http://127.0.0.1:<port>', text)


def main():
    reviews = json.loads((DEST / 'reviews.json').read_text())
    runs = []
    for path in sorted((ROOT / '.eval-runs/onboarding').glob('*/conversation.json')):
        meta = json.loads(path.read_text())
        run = path.parent
        if meta['status'] == 'running':
            raise SystemExit(f'Run still active: {run.name}')
        if run.name not in reviews:
            raise SystemExit(f'Missing manual review: {run.name}')
        review = reviews[run.name]
        if set(review['criteria']) != set(CRITERIA):
            raise SystemExit(f'Incomplete review: {run.name}')
        oracle_path = run / 'oracle.json'
        oracle = json.loads(oracle_path.read_text()) if oracle_path.exists() else {'status': 'not_run'}
        turns = meta['turns']
        no_early_writes = not (meta.get('files_created_before_language') or meta.get('files_changed_before_language'))
        passed = (len(turns) == 2 and all(t['exit_code'] == 0 for t in turns)
                  and no_early_writes and all(review['criteria'].values())
                  and oracle['status'] == 'passed')
        runs.append({
            'run_id': run.name, 'agent': meta['agent'], 'agent_version': meta['agent_version'],
            'case': meta['case'], 'language': meta['language'], 'attempt': meta['attempt'],
            'status': 'passed' if passed else 'failed',
            'model': next((t['model'] for t in turns if t.get('model')), 'configured default; not reported in captured events'),
            'opening_request_sha256': meta['website_prompt_sha256'],
            'skill_entrypoint_sha256': meta['skill_sha256'],
            'turn_seconds': [t['seconds'] for t in turns],
            'first_response': portable(turns[0]['response'], run / 'project') if turns else '',
            'no_files_written_before_language_choice': no_early_writes,
            'language_label_in_run_directory': meta['language'] in run.name,
            'review': review,
            'independent_verification': {
                'status': oracle['status'], 'engine': oracle.get('engine_version'),
                'extension': oracle.get('extension_version'),
                'checks': [{k: check[k] for k in ('name', 'status')} for check in oracle.get('checks', [])],
                'error': portable(oracle.get('error', ''), run / 'project'),
            },
        })
    if not runs:
        raise SystemExit('No runs found')
    passed = sum(r['status'] == 'passed' for r in runs)
    report = {'recorded_on': '2026-11-07', 'passed': passed, 'total': len(runs), 'runs': runs}
    (DEST / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    checks = sum(len(r['independent_verification']['checks']) for r in runs)
    lines = [
        '# Website onboarding results', '',
        f'Recorded November 7, 2026. **{passed}/{len(runs)} reviewed two-turn conversations passed**, with {checks} independent SQL/input-preservation checks.', '',
        'The first turn was the exact website request. Both agents had to ask for the language and source before receiving the second turn. No worker implementation, verification manifest, or oracle answers were supplied. Generated workers were not manually repaired.', '',
        '| Agent | Request | Chosen language | Outcome | Independent checks |',
        '| --- | --- | --- | --- | --- |',
    ]
    for r in sorted(runs, key=lambda x: (x['case'], x['language'], x['agent'], x['run_id'])):
        count = len(r['independent_verification']['checks'])
        lines.append(f"| {r['agent']} | {r['case']} | {r['language']} | {r['status']} | {count} |")
    lines += [
        '', '## What was reviewed', '',
        'Skill discovery, language/source questions before implementation, the chosen language, reuse of supplied data or library code, real SQL execution, repeatable tests, and the final ATTACH/query handoff were reviewed in the saved conversations and artifacts. The independent oracle checked the generated workers against expectations outside their projects.', '',
        'The [machine-readable results](results.json) include opening responses, individual check outcomes, CLI versions, recorded models, timings, prompt hashes, skill-entrypoint hashes, and review notes. Raw session events and account identifiers remain local.', '',
        'The exact private feature-branch installation command was also tested in a fresh project for Codex and Claude Code; installed entrypoints, verifier, and engine reference matched the source.', '',
        '## Findings and corrections', '',
        '- The agents honored the developer’s language choice and paused for missing source information.',
        '- Claude identified an incorrect DuckDB CLI launch example in the skill reference. Both builder/test skills now use the directly tested `uvx --from duckdb-cli==2.0.0 duckdb` command. The reference was corrected during this sweep; the earlier runs recovered without human help. No worker-source repair was needed.',
        '- The independent verifier accepts a worker in a nested project directory. This accommodates a valid generated layout without changing its implementation.',
        '- One Codex run reported that an initial CLI probe may have registered `query_farm` in DuckDB’s default local repository directory. Its final runner uses project-local storage. The harness isolates projects by instruction; it is not a filesystem sandbox.',
        '- The Claude/Python photo build is preserved as the [downloadable worked example](../../examples/photo-catalog/), including unchanged generated worker source and nine agent-written SQL assertions. Its nine independent checks passed; the packaged download also reproduced from a fresh directory containing spaces.',
        '', '## Scope', '',
        'Each of three requests was exercised with Codex and Claude in Python and TypeScript. This is one run per agent/request/language combination, not a success-rate estimate or speed comparison. The configured defaults were used, with shared toolchains/package caches on macOS. The API is a deterministic loopback fixture, not a production integration. Other languages and other coding agents are outside this new conversational matrix. See the [method, commands, and limitations](README.md) and [earlier evaluations](../RESULTS.md).', '',
        'The opening requests omitted a language, but this sweep’s run-directory names included the intended language label. Every agent still explicitly asked and waited for the reply. The driver now uses opaque run suffixes so future projects do not expose that hint. This sweep is evidence of the requested conversation flow, not a blinded language-selection experiment.', '',
        '## Remaining release check', '',
        'The new photo reproduction is included in the Linux CI workflow, but [GitHub Actions did not start the job](https://github.com/Query-farm/vgi-skills/actions/runs/42392619898) because of the account billing/spending-limit restriction. These additions have local macOS verification; a passing Linux run is still required after that restriction is resolved. The repository remains private during review.', '',
    ]
    (DEST / 'RESULTS.md').write_text('\n'.join(lines))
    print(f'Published {passed}/{len(runs)} reviewed conversations and {checks} independent checks')
    return 0 if passed == len(runs) else 1


if __name__ == '__main__':
    raise SystemExit(main())
