import io
import json
import math
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError
from studio.config import Config
from studio import server


def test_pixel_units_and_radius_consistency():
    config=Config()
    assert config.screen.calibrated is False
    radius=416*.003/math.radians(90)
    assert radius==pytest.approx(.7945014759)
    config.screen.radius_m=radius
    assert Config.model_validate(config.model_dump()).screen.radius_m==radius
    data=config.model_dump()
    data['screen']['radius_m']=4
    with pytest.raises(ValidationError): Config.model_validate(data)

@pytest.mark.parametrize('section,key,value',[
    ('screen','pitch_mm',0),('screen','angle_deg',180),('screen','pixels',[2704,400,1248]),
    ('render','scale',2),('render','samples',0),('camera','position',[1.5,-0.5,0]),
    ('frame','border_m',5),('frame','color','invalid'),('frame','depth_m',float('nan')),
])
def test_invalid_inputs(section,key,value):
    data=Config().model_dump()
    data[section][key]=value
    with pytest.raises(ValidationError): Config.model_validate(data)


def test_upload_validation_and_queue(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'OUTPUTS',tmp_path)
    monkeypatch.setattr(server,'jobs',{})
    client=TestClient(server.app)
    assert client.get('/api/config').status_code==200
    assert client.get('/api/jobs/unknown').status_code==404
    assert client.post('/api/jobs',data={'config':'{}'},files={'file':('bad.png',b'garbage')}).status_code==400
    assert client.post('/api/jobs',data={'config':'{"render":{"scale":4}}'},files={'file':('bad.png',b'x')}).status_code==422
    image=Image.new('RGB',(190,90),'red')
    raw=io.BytesIO(); image.save(raw,format='PNG')
    with patch.object(server.pool,'submit') as submit:
        result=client.post('/api/jobs',data={'config':Config().model_dump_json()},files={'file':('poster.png',raw.getvalue(),'image/png')})
        assert result.status_code==202
        identifier=result.json()['id']
        submit.assert_called_once_with(server.run_job,identifier)
    assert Image.open(tmp_path/identifier/'original.png').size==(190,90)
    assert client.get('/api/jobs/'+identifier).json()['status']=='queued'
    assert len(client.get('/api/jobs').json())==1


def test_failed_render_persists_error_and_queue_can_continue(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'OUTPUTS',tmp_path)
    monkeypatch.setattr(server,'jobs',{})
    monkeypatch.setattr(server,'blender_binary',lambda:'/usr/bin/false')
    for identifier in ['failure1','failure2']:
        directory=tmp_path/identifier;directory.mkdir()
        server.jobs[identifier]={'id':identifier,'status':'queued','progress':0}
        # Actual process fails, then another task runs on the same serialized executor.
        server.pool.submit(server.run_job,identifier).result(timeout=10)
        persisted=json.loads((directory/'job.json').read_text())
        assert persisted['status']=='failed'
        assert 'non-zero exit status' in persisted['error']
