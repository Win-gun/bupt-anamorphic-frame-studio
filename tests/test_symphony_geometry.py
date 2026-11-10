"""Pure geometry and perspective safety checks for the bespoke autumn stage."""

import json
from pathlib import Path

import numpy as np

from studio.composition import solve_composition
from studio.symphony_scene import (
    maple_leaf_mesh,
    projected_decoration_safe,
    ribbon_mesh,
)

ROOT = Path(__file__).resolve().parents[1]


def composition():
    config = json.loads((ROOT / "configs/autumn-symphony.json").read_text())
    return config, solve_composition(config, (4535, 2551))


def test_maple_has_incised_lobes_and_curved_surface():
    vertices, faces = maple_leaf_mesh()
    v = np.asarray(vertices)
    assert len(vertices) == 81 and len(faces) == 80
    assert np.ptp(v[:, 2]) > 0.15
    # Tips of the five botanical lobes, versus their deeply cut sinuses.
    outline = v[-20:]
    assert outline[10, 1] > 0.9
    assert outline[8, 1] > outline[9, 1]
    assert outline[12, 1] > outline[11, 1]
    assert outline[6, 0] < outline[7, 0]
    assert outline[14, 0] > outline[13, 0]
    # Every face has area; curled geometry has actual differing normals.
    normals = []
    for face in faces:
        a, b, c = v[list(face[:3])]
        cross = np.cross(b - a, c - a)
        assert np.linalg.norm(cross) > 1e-5
        assert cross[2] > 0
        normals.append(cross / np.linalg.norm(cross))
    assert np.ptp(np.asarray(normals)[:, 0]) > 0.3


def test_satin_ribbon_normals_and_twisted_relief():
    path = [
        (t * 6, 0.3 * np.sin(t * np.pi), 0.4 * np.sin(t * 4))
        for t in np.linspace(0, 1, 80)
    ]
    vertices, faces = ribbon_mesh(path, 0.7, 0.8)
    v = np.asarray(vertices)
    assert len(vertices) == 80 * 9 and len(faces) == 79 * 8
    assert np.ptp(v[:, 2]) > 0.5
    for face in faces:
        a, b, c = v[list(face[:3])]
        cross = np.cross(b - a, c - a)
        assert np.linalg.norm(cross) > 1e-6
        assert cross[2] > 0
    # Open ends taper, so this is a sculptural arc rather than a rectangular ring.
    assert np.linalg.norm(v[0] - v[8]) < np.linalg.norm(v[40 * 9] - v[40 * 9 + 8]) * 0.2


def test_guard_uses_projected_front_depth_not_flat_xy():
    config, c = composition()
    half = c["width"] / 2
    vertices = [(half + 0.15, y, 0) for y in [-0.5, 0.5]]
    assert projected_decoration_safe(vertices, config, c, margin=0)
    # The same local coordinates move inwards across the right edge when behind.
    behind = [(x, y, -4) for x, y, z in vertices]
    assert not projected_decoration_safe(behind, config, c, margin=0)
    assert not projected_decoration_safe([(-1, -1, 0.5), (1, 1, 0.5)], config, c)
    assert projected_decoration_safe([(-2, -5, 0.6), (2, -4, 0.6)], config, c)


def test_full_artwork_default_is_safe_and_preserves_aspect():
    config, c = composition()
    assert c["metrics"]["opening_safe"]
    assert c["uv_crop"] == [0, 0, 1, 1]
    assert abs(c["width"] / c["height"] - 4535 / 2551) < 1e-12
    assert c["metrics"]["projected_width_fraction"] > 0.75


def test_shared_decoration_layout_handles_scale_and_image_aspect():
    from studio.symphony_scene import decoration_layout

    config, _ = composition()
    for size in [(4535, 2551), (1000, 1000), (800, 1200)]:
        for scale in [0.1, 0.5, 0.88, 1.0]:
            config["frame"]["scale"] = scale
            c = solve_composition(config, size)
            sx, sy, offsets = decoration_layout(config, c)
            # Conservative extremities contain every real canopy/floor object.
            top = [
                (x * sx, 3.0 * sy + offsets["top"], z)
                for x in [-8, 8]
                for z in [-0.55, 0.7]
            ]
            floor = [
                (x * sx, -3.2 * sy + offsets["bottom"], z)
                for x in [-8, 8]
                for z in [-1.5, 1.5]
            ]
            assert projected_decoration_safe(top, config, c)
            assert projected_decoration_safe(floor, config, c)
            assert abs(c["width"] / c["height"] - size[0] / size[1]) < 1e-12
            assert c["uv_crop"] == [0, 0, 1, 1]
