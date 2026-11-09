import numpy as np
import pytest
from studio.config import Config
from studio.composition import solve_composition, visible_screen_mask, camera_basis, project_points


@pytest.mark.parametrize('curvature,camera', [('concave', [-2,-14,2]), ('convex', [12,-14,2])])
@pytest.mark.parametrize('size', [(1920,1080), (1080,1920), (1000,1000), (3000,1000)])
def test_fit_preserves_image_and_stays_in_real_screen(curvature, camera, size):
    config = Config().model_dump()
    config['screen']['curvature'] = curvature
    config['camera']['position'] = camera
    config['frame'].update(layout='auto_fit', position=[0,0,0])
    r = solve_composition(config, size)
    assert r['width']/r['height'] == pytest.approx(size[0]/size[1])
    assert r['uv_crop'] == [0,0,1,1]
    assert r['metrics']['opening_safe']
    # Independent higher-resolution rays detect silhouette leaks between samples.
    mask = visible_screen_mask(config, 1024)
    box = (np.asarray(r['opening_ndc'])+1)*512
    x0,y0 = np.floor(box[:2]).astype(int); x1,y1 = np.ceil(box[2:]).astype(int)
    assert mask[y0:y1,x0:x1].all()
    if size == (1920,1080): assert r['metrics']['projected_width_fraction'] >= .5
    center = np.array(r['center']); right = np.array(r['right']); up = np.array(r['up'])
    corners = np.array([center-right*r['width']/2-up*r['height']/2,
                        center+right*r['width']/2+up*r['height']/2])
    projected, _ = project_points(corners, config)
    assert np.allclose(projected.ravel(), r['opening_ndc'])


def test_camera_and_yaw_recompute_composition():
    c = Config().model_dump(); c['frame']['position'] = [0,0,0]
    a = solve_composition(c, (1920,1080))
    c['camera']['position'] = [-5,-18,3]
    c['screen']['yaw_deg'] = 15
    b = solve_composition(c, (1920,1080))
    assert b['metrics']['opening_safe']
    assert not np.allclose(a['center'], b['center'])
    assert not np.allclose(a['opening_ndc'], b['opening_ndc'])


def test_fill_crop_and_manual_absolute_pose():
    c = Config().model_dump(); c['frame'].update(layout='fill', position=[0,0,0], width_m=4, height_m=4)
    r = solve_composition(c, (1920,1080))
    assert r['width']/r['height'] == pytest.approx(1)
    assert r['uv_crop'] == pytest.approx([.21875, 0, .78125, 1])
    c['frame'].update(layout='manual', position=[1,0,1], width_m=3, height_m=2)
    r = solve_composition(c, (1920,1080))
    assert r['center'] == [1,0,1]
    assert (r['width'], r['height']) == (3,2)


def test_unusable_camera_fails_explicitly():
    c = Config().model_dump(); c['camera']['position'] = [0,20,0]
    with pytest.raises(ValueError, match='front-visible|behind'):
        solve_composition(c, (1920,1080))


def test_virtual_depth_moves_main_frame_against_static_room():
    c = Config().model_dump(); c['frame'].update(position=[0,0,0], virtual_depth_m=0)
    a = solve_composition(c, (1920,1080))
    c['frame']['virtual_depth_m'] = 1.5
    b = solve_composition(c, (1920,1080))
    assert np.allclose(a['stage_center'], b['stage_center'])
    for key in ['static_depth', 'stage_width', 'stage_height', 'stage_outer_width', 'stage_outer_height']:
        assert a[key] == pytest.approx(b[key])
    assert np.dot(np.array(b['center'])-np.array(a['center']), b['normal']) == pytest.approx(-1.5)
    assert b['main_frame_offset'][2] == pytest.approx(-1.5)
    assert np.allclose(a['opening_ndc'], b['opening_ndc'])


@pytest.mark.parametrize('template', ['cinema','deep','float','glass'])
def test_forward_auto_offset_cannot_enter_static_back_wall(template):
    c = Config().model_dump()
    c['frame'].update(layout='auto_fit', template=template, position=[0,0,3])
    with pytest.raises(ValueError, match='后墙'):
        solve_composition(c, (1920,1080))


def test_absolute_manual_world_position_cannot_enter_back_wall():
    c = Config().model_dump()
    c['frame'].update(layout='manual', position=[0,0,0])
    baseline = solve_composition(c, (1920,1080))
    forward = -np.asarray(baseline['normal'])
    c['frame']['position'] = (np.asarray(baseline['stage_center'])+forward*3).tolist()
    with pytest.raises(ValueError, match='后墙'):
        solve_composition(c, (1920,1080))


def test_float_backing_rear_extent_is_checked_even_with_thin_main_frame():
    c = Config().model_dump()
    c['frame'].update(template='float', position=[0,0,.1], depth_m=.02, border_m=.01, portal_depth_m=.5)
    with pytest.raises(ValueError, match='后墙'):
        solve_composition(c, (1920,1080))
