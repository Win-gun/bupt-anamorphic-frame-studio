"""Loopback-only local render queue; Blender processes are serialized."""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import ValidationError
from .config import Config

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / 'outputs'
OUTPUTS.mkdir(exist_ok=True)
app = FastAPI(title='BUPT Anamorphic Frame Studio')
pool = ThreadPoolExecutor(max_workers=1)
lock = threading.Lock()
jobs = {}
MAX_UPLOAD = 40 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 50_000_000


def blender_binary():
    override = os.environ.get('BLENDER_BIN')
    path = override or shutil.which('blender') or '/Applications/Blender.app/Contents/MacOS/Blender'
    if not Path(path).is_file():
        raise RuntimeError('找不到 Blender；请设置 BLENDER_BIN')
    return path


def update(identifier, **changes):
    with lock:
        jobs[identifier].update(changes)
        directory = OUTPUTS / identifier
        temporary = directory / 'job.tmp'
        temporary.write_text(json.dumps(jobs[identifier], ensure_ascii=False, indent=2))
        temporary.replace(directory / 'job.json')


def run_job(identifier):
    directory = OUTPUTS / identifier
    try:
        update(identifier, status='running', progress=10)
        command = [blender_binary(), '-b', '--python-exit-code', '1', '--python',
                   str(ROOT/'studio/blender_render.py'), '--', '--config', str(directory/'config.json'),
                   '--poster', str(directory/'original.png'), '--output', str(directory)]
        with (directory/'render.log').open('w') as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=3600)
        update(identifier, progress=90)
        required = {'original':'original.png','scene':'scene.png','atlas':'atlas.png',
                    'simulation':'simulation.png','difference':'difference.png','mask':'mask.png',
                    'calibration':'calibration.png','blend':'scene.blend','report':'report.json','config':'config.json','log':'render.log'}
        for filename in required.values():
            if not (directory/filename).is_file():
                raise RuntimeError('渲染缺少输出：'+filename)
        report = json.loads((directory/'report.json').read_text())
        config = Config.model_validate_json((directory/'config.json').read_text())
        if config.render.video:
            # Explicitly a held still, not an animated 3D scene. Encode the mapped LED canvas.
            subprocess.run(['ffmpeg','-y','-loop','1','-i',str(directory/'atlas.png'),'-t',str(config.render.duration),
                '-r',str(config.render.fps),'-c:v','libx264','-pix_fmt','yuv420p','-vf',
                'pad=ceil(iw/2)*2:ceil(ih/2)*2','-movflags','+faststart',str(directory/'led.mp4')],
                stdout=subprocess.DEVNULL, stderr=(directory/'encode.log').open('w'),check=True,timeout=600)
            probe = subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(directory/'led.mp4')],
                                   capture_output=True,text=True,check=True)
            (directory/'video-probe.json').write_text(probe.stdout)
            data = json.loads(probe.stdout)
            stream = next(s for s in data['streams'] if s['codec_type']=='video')
            with Image.open(directory/'atlas.png') as atlas:
                expected = tuple(v + v%2 for v in atlas.size)
            if (stream['width'],stream['height']) != expected or stream['pix_fmt'] != 'yuv420p':
                raise RuntimeError('视频输出规格检查失败')
            required.update(video='led.mp4',video_probe='video-probe.json')
        urls = {key:f'/outputs/{identifier}/{name}' for key,name in required.items()}
        passed = report.get('passed',report.get('validation',{}).get('passed',False))
        update(identifier,status='completed' if passed else 'validation_failed',progress=100,
               outputs=urls,metrics=report, error=None if passed else '回贴验证未通过，请检查报告和差异图')
    except Exception as exc:
        update(identifier,status='failed',progress=100,error=str(exc))


@app.get('/api/config')
def default_config():
    return Config().model_dump()

@app.get('/api/health')
def health():
    try:
        binary = blender_binary()
    except RuntimeError:
        binary = None
    return {'blender':binary, 'ffmpeg':shutil.which('ffmpeg'),'ffprobe':shutil.which('ffprobe'),
            'calibrated':False,'queue_workers':1}

@app.get('/api/jobs')
def list_jobs():
    with lock:
        return list(reversed(list(jobs.values())))

@app.get('/api/jobs/{identifier}')
def get_job(identifier: str):
    with lock:
        if identifier not in jobs:
            raise HTTPException(404,'任务不存在')
        return dict(jobs[identifier])

@app.post('/api/jobs',status_code=202)
async def create_job(file: UploadFile = File(...), config: str = Form(...)):
    try:
        parsed = Config.model_validate_json(config)
    except ValidationError as exc:
        raise HTTPException(422,str(exc))
    raw = await file.read(MAX_UPLOAD+1)
    if len(raw)>MAX_UPLOAD:
        raise HTTPException(413,'图片不能超过 40 MB')
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
        image = ImageOps.exif_transpose(image).convert('RGBA')
        background = Image.new('RGBA',image.size,'white')
        background.alpha_composite(image)
        image = background.convert('RGB')
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError):
        raise HTTPException(400,'仅支持有效的 PNG/JPEG/WebP 等光栅图片')
    identifier = uuid4().hex
    directory = OUTPUTS/identifier
    directory.mkdir()
    image.save(directory/'original.png')
    (directory/'config.json').write_text(parsed.model_dump_json(indent=2))
    with lock:
        jobs[identifier]={'id':identifier,'status':'queued','progress':0}
    update(identifier)
    pool.submit(run_job,identifier)
    return {'id':identifier}

# Recover persisted results; interrupted renders are never silently resumed.
for path in sorted(OUTPUTS.glob('*/job.json')):
    try:
        job = json.loads(path.read_text())
        if job['status'] in ('queued','running'):
            job.update(status='failed',error='服务重启中断了任务，请重新提交')
        jobs[job['id']] = job
    except (ValueError,KeyError):
        pass

app.mount('/outputs',StaticFiles(directory=OUTPUTS),name='outputs')
if (ROOT/'frontend/dist').exists():
    app.mount('/',StaticFiles(directory=ROOT/'frontend/dist',html=True),name='frontend')
