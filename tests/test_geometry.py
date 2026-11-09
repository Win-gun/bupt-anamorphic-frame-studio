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

@pytest.mark.parametrize('curvature', ['concave', 'convex'])
@pytest.mark.parametrize('yaw', [-45, 0, 37])
def test_both_curvatures_yaw_normals_and_visibility(curvature, yaw):
    screen = Config().screen.model_dump()
    screen.update(curvature=curvature, yaw_deg=yaw)
    d = dimensions(screen)
    ss = np.linspace(.001, d['length']-.001, 501)
    pts, normals = surface_grid(ss, .2, screen)
    derivative = (np.array([surface_point(s+1e-5, .2, screen) for s in ss])-
                  np.array([surface_point(s-1e-5, .2, screen) for s in ss]))/2e-5
    assert np.allclose(np.linalg.norm(derivative, axis=-1), 1, atol=1e-5)
    assert np.allclose(np.sum(derivative*normals, axis=-1), 0, atol=1e-5)
    assert np.allclose(np.cross(derivative, [0, 0, 1]), normals, atol=1e-5)
    angle = math.radians(yaw)
    rotation = np.array([[math.cos(angle), -math.sin(angle), 0],
                         [math.sin(angle), math.cos(angle), 0], [0, 0, 1]])
    camera = np.array([-2,-14,2] if curvature == 'concave' else [12,-14,2]) @ rotation.T
    assert visible_points(pts, normals, camera, screen).all()
    unrotated = dict(screen, yaw_deg=0)
    pp, nn = surface_grid(ss, .2, unrotated)
    assert np.allclose(pts, pp @ rotation.T)
    assert np.array_equal(visible_points(pts, normals, camera, screen),
                          visible_points(pp, nn, camera @ rotation, unrotated))


def test_convex_back_and_finite_height_occlusion():
    from studio.geometry import ray_surface_hit
    screen = Config().screen.model_dump(); screen['curvature'] = 'convex'
    d = dimensions(screen)
    p, n = surface_grid(d['length']-.1, 0, screen)
    assert not visible_points(p, n, [-2, -14, 2], screen)
    assert visible_points(p, n, [12, -14, 2], screen)
    hits, _ = ray_surface_hit([0, -14, 100], [[0, 1, 0]], screen)
    assert not np.isfinite(hits).any()

@pytest.mark.parametrize('yaw', [0, 37])
def test_concave_front_can_be_occluded_but_ray_above_panel_is_clear(yaw):
    screen = Config().screen.model_dump(); screen.update(curvature='concave', yaw_deg=yaw)
    a=math.radians(yaw)
    rotation=np.array([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1]])
    point, normal=surface_grid(.1,0,screen)
    blocked=np.array([8,-6,0]) @ rotation.T
    above=np.array([8,-6,100]) @ rotation.T
    assert np.dot(normal,blocked-point)>0
    assert not visible_points(point,normal,blocked,screen)
    assert visible_points(point,normal,above,screen)
