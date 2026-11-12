"""The layered gallery leaves a large, complete sightline to the original poster."""
import hashlib
import json
import os
import subprocess

import pytest

from studio.config import Config
from studio.server import ROOT, blender_binary


@pytest.mark.skipif(
    os.environ.get("RUN_BLENDER_TESTS") != "1", reason="actual Blender render"
)
def test_gallery_projection_and_saved_scene(tmp_path):
    config = Config.model_validate_json(
        (ROOT / "configs/autumn-amber-gallery.json").read_text()
    )
    config.render.scale = 0.125
    config.render.samples = 8
    config.render.quality = "quick"
    config_path = tmp_path / "config.json"
    config_path.write_text(config.model_dump_json())
    poster = ROOT / "examples/v2/jiqi-qiuyun/original.png"
    output = tmp_path / "gallery"
    run = subprocess.run(
        [
            blender_binary(),
            "-b",
            "--python-exit-code",
            "1",
            "--python",
            str(ROOT / "studio/blender_render.py"),
            "--",
            "--config",
            str(config_path),
            "--poster",
            str(poster),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    report = json.loads((output / "report.json").read_text())
    assert report["passed"]
    assert report["metrics"]["foreground_coverage"] == 1
    assert (
        report["artwork"]["composition"]["metrics"]["projected_width_fraction"] >= 0.85
    )
    check = subprocess.run(
        [
            blender_binary(),
            "-b",
            str(output / "scene.blend"),
            "--python-exit-code",
            "1",
            "--python",
            str(ROOT / "scripts/verify_amber_gallery.py"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert check.returncode == 0, check.stdout + check.stderr
    result = next(
        line.split(" ", 1)[1]
        for line in check.stdout.splitlines()
        if line.startswith("AMBER_GALLERY_CHECK ")
    )
    evidence = json.loads(result)
    assert (
        evidence["packed_poster_sha256"]
        == hashlib.sha256(poster.read_bytes()).hexdigest()
    )
    assert evidence["maple_surfaces"] == 6
