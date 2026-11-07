#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = ["pillow==13.0.0", "piexif==1.1.3"]
# ///
"""Small original inputs for the onboarding evaluations and photo walkthrough."""
from __future__ import annotations
import argparse
import csv
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT=Path(__file__).resolve().parents[1]
TICKETS=[
 {'ticket_id':101,'customer_id':1,'status':'open','subject':'Login'},
 {'ticket_id':102,'customer_id':2,'status':'closed','subject':'Invoice'},
 {'ticket_id':103,'customer_id':1,'status':'open','subject':'Export'},
 {'ticket_id':104,'customer_id':3,'status':'open','subject':'Setup'},
]

def photo(path,model=None,taken=None,gps=None,color=(64,128,192)):
    from PIL import Image
    import piexif
    path.parent.mkdir(parents=True,exist_ok=True)
    data={'0th':{},'Exif':{},'GPS':{},'1st':{},'thumbnail':None}
    if model:data['0th'][piexif.ImageIFD.Model]=model.encode()
    if taken:data['Exif'][piexif.ExifIFD.DateTimeOriginal]=taken.encode()
    if gps:
        lat,lon=gps
        def dms(value):
            value=abs(value);degrees=int(value);minutes=int((value-degrees)*60)
            seconds=round(((value-degrees)*60-minutes)*60*10000)
            return ((degrees,1),(minutes,1),(seconds,10000))
        data['GPS']={piexif.GPSIFD.GPSLatitudeRef:b'N' if lat>=0 else b'S',piexif.GPSIFD.GPSLatitude:dms(lat),piexif.GPSIFD.GPSLongitudeRef:b'E' if lon>=0 else b'W',piexif.GPSIFD.GPSLongitude:dms(lon)}
    image=Image.new('RGB',(32,24),color)
    image.save(path,'JPEG',exif=piexif.dump(data))

def make_photos(folder):
    folder.mkdir(parents=True,exist_ok=True)
    photo(folder/'north.jpg','Fixture Camera A','2025:01:02 03:04:05',(40.5,-73.75))
    photo(folder/'south.jpg','Fixture Camera B','2024:06:15 12:30:00',(-33.875,151.2),(180,90,40))
    photo(folder/'plain.jpg',color=(130,160,90))
    photo(folder/'nested'/'ignored.jpg','Nested camera','2023:01:01 00:00:00')
    (folder/'broken.jpg').write_bytes(b'This is a deliberately invalid JPEG fixture.\n')
    (folder/'notes.txt').write_text('Original synthetic photos for VGI onboarding tests. No personal data.\n')

def write_csv(path,rows):
    with path.open('w',newline='') as f:csv.writer(f).writerows(rows)

def prepare(run,base_url=None):
    meta=json.loads((run/'conversation.json').read_text());project=run/'project'
    inputs=project/'inputs';inputs.mkdir(exist_ok=True)
    language={'python':'Python','typescript':'TypeScript'}[meta['language']]
    common=f'Use {language}. Keep this local and use stock DuckDB with VGI from query_farm. '
    if meta['case']=='files':
        make_photos(inputs/'photos');(inputs/'empty').mkdir(exist_ok=True)
        reply=common+f'''The photo folder is {inputs/'photos'}. For this first version read .jpg and .jpeg files directly in that folder, without recursing or following symlinks. Keep every input unchanged. Valid photos without EXIF get a row with NULL metadata; skip corrupt files with a diagnostic on stderr.
Expose photos.main.files(folder VARCHAR), with columns path, size_bytes, camera_model, taken_at, latitude, and longitude. NULL folder should return no rows. I want to group photos by camera and year and find ones with GPS coordinates. Include the ATTACH and example queries when it works.'''
    elif meta['case']=='api':
        if not base_url:raise ValueError('API case needs --base-url for the running fixture service')
        write_csv(inputs/'customers.csv',[['customer_id','customer_name'],[1,'Northwind'],[2,'Seabrook'],[3,'Redwood']])
        (inputs/'service.md').write_text(f'''# Support service (local test data)
Base URL: {base_url}/normal
GET <base_url>/tickets?page=1 returns JSON {{"tickets":[{{"ticket_id":101,"customer_id":1,"status":"open","subject":"Login"}}],"next":"<absolute URL or null>"}}.
Follow next until null. IDs are integer; text fields are strings. No authentication. All records are fictional.
Other test base URLs: {base_url}/empty (no tickets), {base_url}/large (10001 tickets over multiple pages), {base_url}/error (503), {base_url}/rate-limit (429), {base_url}/malformed (wrong response shape), {base_url}/loop (repeated pagination URL). Do not treat errors as empty results. Bound pagination and request duration.
''')
        reply=common+f'''Use the support-ticket REST API described in inputs/service.md at {base_url}/normal. This is an authorized local test service with fictional data and no credentials. Join its records to inputs/customers.csv.
Expose support.main.tickets(base_url VARCHAR) with ticket_id BIGINT, customer_id BIGINT, status VARCHAR, and subject VARCHAR. NULL base_url should return no rows. I want the number of open tickets per customer, including customers with zero open tickets. Follow pagination, report upstream errors, and keep requests bounded. Show me ATTACH and that query when it works.'''
    else:
        write_csv(inputs/'products.csv',[['record_id','sku'],[1,'ABC-1234'],[2,'abc-1234'],[3,'QRS-0000'],[4,'ZZZ-9999'],[5,'MNO-5678'],[6,''],[7,'ABC-12']])
        if meta['language']=='python':
            library=inputs/'company_rules.py'
            library.write_text('''"""Existing company SKU rules. Keep this implementation unchanged."""
import re
def is_valid_sku(value: str) -> bool:
    if not isinstance(value, str):
        raise TypeError("SKU must be text")
    return bool(re.fullmatch(r"[A-Z]{3}-[0-9]{4}", value)) and not value.startswith("ZZZ-")
''')
        else:
            library=inputs/'company_rules.mjs'
            library.write_text('''// Existing company SKU rules. Keep this implementation unchanged.
export function is_valid_sku(value) {
  if (typeof value !== 'string') throw new TypeError('SKU must be text');
  return value.length === 8 && /^[A-Z]{3}-[0-9]{4}$/.test(value) && !value.startsWith('ZZZ-');
}
''')
        reply=common+f'''The existing library is {library.relative_to(project)} and its function is is_valid_sku. Reuse that implementation and keep it unchanged. Examples: ABC-1234 and QRS-0000 are valid; abc-1234, ZZZ-9999, and ABC-12 are invalid. The CSV is inputs/products.csv.
Expose validation.main.is_valid_sku(sku VARCHAR) as BOOLEAN, preserving SQL NULL instead of passing it to the library. I want a query listing invalid records from the CSV, with missing values handled separately. Show me ATTACH and the query when it works.'''
    (run/'reply.txt').write_text(reply)
    before={str(p.relative_to(project)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs.rglob('*') if p.is_file()}
    (run/'input-hashes.json').write_text(json.dumps(before,indent=2)+'\n')
    return run/'reply.txt'

class Service(BaseHTTPRequestHandler):
    def log_message(self,format,*args):pass
    def do_GET(self):
        parsed=urlparse(self.path);parts=parsed.path.strip('/').split('/');variant=parts[0]
        if len(parts)!=2 or parts[1]!='tickets':self.send_error(404);return
        page=int(parse_qs(parsed.query).get('page',['1'])[0])
        code=200;next_url=None
        if variant=='error':code=503;body={'error':'Fixture service unavailable'}
        elif variant=='rate-limit':code=429;body={'error':'Fixture rate limit'}
        elif variant=='malformed':body={'tickets':'not an array','next':None}
        else:
            if variant=='large':all_rows=[{'ticket_id':i,'customer_id':1,'status':'open','subject':f'Ticket {i}'} for i in range(1,10002)];size=1000
            elif variant=='empty':all_rows=[];size=2
            elif variant=='holdout':all_rows=[{'ticket_id':907,'customer_id':77,'status':'closed','subject':'Unseen ticket'}];size=2
            else:all_rows=TICKETS;size=2
            rows=all_rows[(page-1)*size:page*size]
            if page*size<len(all_rows):next_url=f'http://127.0.0.1:{self.server.server_port}/{variant}/tickets?page={page+1}'
            if variant=='loop':next_url=f'http://127.0.0.1:{self.server.server_port}/loop/tickets?page=1'
            body={'tickets':rows,'next':next_url}
        encoded=json.dumps(body).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(encoded)));self.end_headers();self.wfile.write(encoded)

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('run',type=Path);prep.add_argument('--base-url')
    photos=sub.add_parser('photos');photos.add_argument('folder',type=Path)
    serve=sub.add_parser('serve');serve.add_argument('--url-file',type=Path,required=True);serve.add_argument('--port',type=int,default=0)
    args=p.parse_args()
    if args.action=='prepare':print(prepare(args.run.resolve(),args.base_url))
    elif args.action=='photos':make_photos(args.folder)
    else:
        server=ThreadingHTTPServer(('127.0.0.1',args.port),Service)
        args.url_file.parent.mkdir(parents=True,exist_ok=True)
        args.url_file.write_text(f'http://127.0.0.1:{server.server_port}')
        print(args.url_file.read_text(),flush=True);server.serve_forever()
if __name__=='__main__':main()
