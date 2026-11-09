import math
import numpy as np
import pytest
from studio.config import Config
from studio.geometry import dimensions,surface_point,surface_grid,visible_points

@pytest.mark.parametrize('angle',[30,90,150])
def test_joints_are_position_and_tangent_continuous(angle):
    screen=Config().screen.model_dump(); screen['angle_deg']=angle
    d=dimensions(screen); eps=1e-6
    for joint in (d['left'],d['left']+d['arc']):
        p=np.array(surface_point(joint,0,screen))
        before=np.array(surface_point(joint-eps,0,screen))
        after=np.array(surface_point(joint+eps,0,screen))
        assert np.linalg.norm(p-before)==pytest.approx(eps,rel=1e-4)
        assert np.allclose((p-before)/eps,(after-p)/eps,atol=3e-6)

@pytest.mark.parametrize('angle',[30,90,150])
def test_vectorization_and_arc_length(angle):
    screen=Config().screen.model_dump();screen['angle_deg']=angle;d=dimensions(screen)
    ss=np.linspace(0,d['length'],10001)
    pts,normals=surface_grid(ss,1,screen)
    assert np.allclose(pts[::100],[surface_point(float(s),1,screen) for s in ss[::100]])
    assert np.allclose(np.linalg.norm(normals,axis=-1),1)
    assert np.linalg.norm(np.diff(pts,axis=0),axis=-1).sum()==pytest.approx(d['length'],rel=1e-5)
    # UV is globally proportional to developed distance; boundaries match pixel fractions.
    assert d['left']/d['length']==pytest.approx(2704/4368)
    assert (d['left']+d['arc'])/d['length']==pytest.approx(3120/4368)


def test_front_back_and_self_occlusion():
    screen=Config().screen.model_dump(); d=dimensions(screen)
    ss=np.array([d['left']/2,d['left']+d['arc']/2,d['length']-.5])
    pts,normals=surface_grid(ss,0,screen)
    assert visible_points(pts,normals,[-2,-10,1],screen).all()
    assert not visible_points(pts[:1],normals[:1],[-2,10,1],screen).any()
    # Looking from behind right panel must not consider its back face visible.
    assert not visible_points(pts[-1:],normals[-1:],[20,-2,0],screen).any()
