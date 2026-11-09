"""Pure geometry invariants for the new architectural display, independent of Blender."""
from collections import Counter
import numpy as np
import pytest
from studio.aurora_scene import rounded_panel_mesh, linear_rgb
from studio.scene_design import AURORA_TEMPLATES, LEGACY_TEMPLATES


def test_slab_closed_and_exact_thickness():
    vertices, faces = rounded_panel_mesh(8, 4, 0.035, 0.035)
    edges = Counter(
        tuple(sorted((a, b))) for f in faces for a, b in zip(f, f[1:] + f[:1])
    )
    assert set(edges.values()) == {2}
    assert min(v[2] for v in vertices) == -0.035
    assert max(v[2] for v in vertices) == 0
    volume = 0
    v = np.asarray(vertices)
    for face in faces:
        for i in range(1, len(face) - 1):
            volume += np.dot(v[face[0]], np.cross(v[face[i]], v[face[i + 1]])) / 6
    assert volume > 0


def test_rounded_corner_contained_and_color_linearized():
    vertices, _ = rounded_panel_mesh(8, 4, 0.035, 0.1)
    assert all(abs(x) <= 4 and abs(y) <= 2 for x, y, z in vertices)
    assert not any(abs(x) == 4 and abs(y) == 2 for x, y, z in vertices)
    assert linear_rgb("#FFFFFF") == (1, 1, 1)
    assert linear_rgb("#808080")[0] == pytest.approx(0.21586, abs=0.00001)
    assert not AURORA_TEMPLATES & LEGACY_TEMPLATES
