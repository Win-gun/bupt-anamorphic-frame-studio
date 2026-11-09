"""Actual local HTTP upload/render/FFmpeg acceptance for the V2 motion test."""
import argparse,json,time,shutil
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8001');a=p.parse_args()
with httpx.Client(base_url=a.base_url,timeout=60) as client:
 c=client.get('/api/config').json()
 c['render'].update(scale=.125,samples=16,duration=1,fps=6,light_sweep=True)
 with (ROOT/'examples/v2/poster-16x9.png').open('rb') as im:
  r=client.post('/api/jobs',data={'config':json.dumps(c)},files={'file':('poster.png',im,'image/png')});r.raise_for_status()
 identifier=r.json()['id'];print(identifier,flush=True)
 for _ in range(180):
  job=client.get('/api/jobs/'+identifier).json()
  if job['status'] not in ('queued','running'):break
  time.sleep(2)
 else:raise TimeoutError(identifier)
 target=ROOT/'examples/v2/animation-api';target.mkdir(exist_ok=True)
 (target/'job.json').write_text(json.dumps(job,ensure_ascii=False,indent=2))
 source=ROOT/'outputs'/identifier
 for name in ['led.mp4','video-probe.json','report.json','config.json','animation.json']:
  if (source/name).exists():shutil.copy2(source/name,target/name)
 assert job['status']=='completed',job.get('error')
 assert job['metrics']['dynamics']['passed']
 assert job['metrics']['config']['render']['animation']
 assert job['metrics']['config']['render']['light_sweep']
 from PIL import Image,ImageDraw
 frames=sorted((source/'frames').glob('led_*.png'))
 assert len(frames)==6
 montage=Image.new('RGB',(546*3,390*2),'black')
 for i,frame in enumerate(frames):montage.paste(Image.open(frame),((i%3)*546,(i//3)*390))
 montage.save(target/'mapped-motion-frames.png')
 print(json.dumps({'status':job['status'],'frames':len(frames),'checks':job['metrics']['dynamics']['verification']},indent=2))
