#!/usr/bin/env python3
"""Create deterministic, self-contained walkthrough downloads from reviewed files."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'examples/photo-catalog'
FIXED_TIME=(2026,11,7,0,0,0)

def archive(path,files):
    path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as bundle:
        for name,source in sorted(files.items()):
            info=zipfile.ZipInfo(name,FIXED_TIME);info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            bundle.writestr(info,source.read_bytes())
    return {'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}

def main():
    p=argparse.ArgumentParser();p.add_argument('--website-root',type=Path,required=True);args=p.parse_args()
    output=args.website_root/'public/vgi/agents'
    sample={str(p.relative_to(EXAMPLE)):p for p in (EXAMPLE/'inputs').rglob('*') if p.is_file()}
    sample['LICENSE']=EXAMPLE/'LICENSE'
    names=['README.md','LICENSE','request.txt','reply.txt','provenance.json','demo.py',
           'photo_worker/photo_worker.py','photo_worker/pyproject.toml','photo_worker/uv.lock',
           'photo_worker/vgi-worker.json','photo_worker/tests/make_fixtures.py']
    complete={name:EXAMPLE/name for name in names};complete.update(sample)
    complete['tools/verify_worker.py']=ROOT/'skills/vgi-worker/scripts/verify_worker.py'
    downloads=[archive(output/'photo-catalog-inputs.zip',sample),archive(output/'photo-catalog-example.zip',complete)]
    (output/'photo-catalog-downloads.json').write_text(json.dumps(downloads,indent=2)+'\n')
    result=json.loads((EXAMPLE/'result.json').read_text());proof=json.loads((EXAMPLE/'provenance.json').read_text())
    data={'recordedOn':proof['recorded_on'],'agent':proof['agent'],'language':proof['language'],'runId':proof['run_id'],
          'columns':result['columns'],'rows':result['rows'],'independentChecks':proof['independent_sql_checks'],
          'reply':(EXAMPLE/'reply.txt').read_text().strip(),'workerSourceSha256':proof['worker_source_sha256'],'downloads':downloads}
    (args.website_root/'src/data/vgi-photo-example.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(downloads,indent=2))
if __name__=='__main__':main()
