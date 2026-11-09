"""Real API -> Blender -> compare -> optional FFmpeg acceptance; save all evidence."""
import argparse
import json
import sys
import time
from pathlib import Path
import urllib.request
import urllib.error
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from studio.server import app
from studio.config import Config
parser=argparse.ArgumentParser()
parser.add_argument('--scale',type=float,default=.125)
parser.add_argument('--template',choices=['deep','float','glass'],default='deep')
parser.add_argument('--video',action='store_true')
args=parser.parse_args()
c=Config(); c.render.scale=args.scale; c.render.samples=8; c.render.video=args.video; c.frame.template=args.template
client=TestClient(app)
with (ROOT/'examples/poster.png').open('rb') as poster:
    response=client.post('/api/jobs',data={'config':c.model_dump_json()},files={'file':('poster.png',poster,'image/png')})
response.raise_for_status()
identifier=response.json()['id']; print(identifier,flush=True)
start=time.monotonic()
while time.monotonic()-start<3600:
    job=client.get('/api/jobs/'+identifier).json()
    if job['status'] in ('completed','failed','validation_failed'):
        print(json.dumps(job,ensure_ascii=False,indent=2),flush=True)
        sys.exit(0 if job['status']=='completed' else 1)
    time.sleep(2)
raise TimeoutError(identifier)
