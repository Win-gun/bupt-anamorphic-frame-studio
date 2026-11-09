"""Read-only tool availability and version report."""
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from studio.server import blender_binary

def version(command):
    try:
        r=subprocess.run(command,capture_output=True,text=True,timeout=20)
        return {'ok':r.returncode==0,'version':(r.stdout or r.stderr).splitlines()[:3]}
    except (OSError,subprocess.TimeoutExpired) as exc:
        return {'ok':False,'error':str(exc)}
node= '/opt/homebrew/opt/node@20/bin/node' if Path('/opt/homebrew/opt/node@20/bin/node').exists() else 'node'
report={'platform':platform.platform(),'machine':platform.machine(), 'python':sys.version,
        'blender':version([blender_binary(),'--version']),'node':version([node,'--version']),
        'ffmpeg':version(['ffmpeg','-version']),'ffprobe':version(['ffprobe','-version'])}
print(json.dumps(report,indent=2))
if not all(report[k]['ok'] for k in ['blender','node','ffmpeg','ffprobe']):
    sys.exit(1)
