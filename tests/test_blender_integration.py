"""Opt-in real Blender regressions, no simulated renderer results."""
import json
import os
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image
import pytest
from studio.config import Config
from studio.server import blender_binary,ROOT

pytestmark=pytest.mark.skipif(os.environ.get('RUN_BLENDER_TESTS')!='1',reason='set RUN_BLENDER_TESTS=1 for actual Blender renders')

@pytest.mark.parametrize('template,angle,depth,ratio',[
    ('deep',90,.02,(600,200)),('float',90,.02,(200,600)),('glass',90,.02,(400,400)),
    ('deep',5,.65,(200,300)),('deep',170,.65,(200,300)),
])
def test_real_renderer_extremes(tmp_path,template,angle,depth,ratio):
    c=Config();c.frame.template=template;c.frame.depth_m=depth;c.screen.angle_deg=angle;c.render.scale=.125;c.render.samples=8
    (tmp_path/'config.json').write_text(c.model_dump_json())
    # Large colored field makes hiding/loss distinguishable from an empty background.
    Image.new('RGB',ratio,(220,30,70)).save(tmp_path/'poster.png')
    output=tmp_path/'render'
    run=subprocess.run([blender_binary(),'-b','--python-exit-code','1','--python',str(ROOT/'studio/blender_render.py'),'--',
        '--config',str(tmp_path/'config.json'),'--poster',str(tmp_path/'poster.png'),'--output',str(output)],capture_output=True,text=True,timeout=120)
    assert run.returncode==0,run.stdout+run.stderr
    report=json.loads((output/'report.json').read_text())
    display=report['artwork']['poster_display_metres']
    assert display[0]/display[1]==pytest.approx(ratio[0]/ratio[1])
    target=np.asarray(Image.open(output/'scene.png'))
    red=(target[:,:,0]>target[:,:,1]*1.5)&(target[:,:,0]>120)
    assert red.sum()>200,'original poster hidden by geometry or glass'
    assert Image.open(output/'atlas.png').size==(546,390)
    if angle==90: assert report['passed'],report['metrics']
