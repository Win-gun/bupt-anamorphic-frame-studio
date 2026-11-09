"""Run in Blender: actual image differences prove visual controls reach rendering.
This is an engineering wiring check, not an aesthetic score.
"""
import copy, json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "studio"))
import bpy
import numpy as np
from mathutils import Vector
from blender_render import build_target, read_pixels, render
from studio.composition import visible_screen_mask


base = json.loads((ROOT / "configs/bupt-demo.json").read_text())
output = ROOT / "examples/v3/control-probe"
output.mkdir(parents=True, exist_ok=True)
cases = {
    "baseline": None,
    "intensity": ("lighting", "intensity", 0.35),
    "softness": ("lighting", "softness", 0.15),
    "glow": ("lighting", "glow", 0.18),
    "ambient": ("lighting", "ambient", 1.2),
    "shadow_softness": ("lighting", "shadow_softness", 0.15),
    "background_saturation": ("appearance", "saturation", 0),
}
images = {}
exhibition = None
for name, change in cases.items():
    config = copy.deepcopy(base)
    if change:
        config[change[0]][change[1]] = change[2]
    bpy.ops.wm.read_factory_settings(use_empty=False)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.world.use_nodes = True
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.dither_intensity = 0
    scene.render.resolution_x = 560
    scene.render.resolution_y = 400
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    bpy.ops.object.camera_add(location=config["camera"]["position"])
    camera = bpy.context.object
    camera.rotation_euler = (
        (Vector(config["camera"]["target"]) - camera.location)
        .to_track_quat("-Z", "Y")
        .to_euler()
    )
    camera.data.sensor_fit = "HORIZONTAL"
    camera.data.lens = 36 / (
        2 * math.tan(math.radians(config["camera"]["fov_deg"]) / 2)
    )
    scene.camera = camera
    exhibition = build_target(config, ROOT / "examples/v2/jiqi-qiuyun/original.png")
    render(scene, output / (name + ".png"))
    images[name] = read_pixels(output / (name + ".png"))
    if name == "baseline":
        composition = exhibition["report"]["composition"]
# Arrays from Blender use bottom-left. Map the independently ray-cast screen mask to render texel centers.
mask = visible_screen_mask(base, 256)
y = (np.arange(400) + 0.5) * 256 / 400
x = (np.arange(560) + 0.5) * 256 / 560
valid = mask[y.astype(int)[:, None], x.astype(int)[None, :]]
x0, y0, x1, y1 = composition["opening_ndc"]
xx, yy = np.meshgrid(
    (np.arange(560) + 0.5) * 2 / 560 - 1, (np.arange(400) + 0.5) * 2 / 400 - 1
)
poster = (xx > x0 + 0.03) & (xx < x1 - 0.03) & (yy > y0 + 0.03) & (yy < y1 - 0.03)
background = valid & ~(
    (xx > x0 - 0.04) & (xx < x1 + 0.04) & (yy > y0 - 0.04) & (yy < y1 + 0.04)
)
results = {}
for name, image in images.items():
    if name == "baseline":
        continue
    delta = np.abs(image - images["baseline"])
    results[name] = {
        "background_mae_srgb": float(delta[background].mean()),
        "poster_mae_srgb": float(delta[poster].mean()),
        "affects_background": bool(delta[background].mean() > 0.0001),
        "poster_unchanged": bool(delta[poster].mean() < 0.001),
    }
report = {
    "purpose": "Actual Blender render ablation; not an aesthetic acceptance score",
    "cases": results,
    "passed": all(
        item["affects_background"] and item["poster_unchanged"]
        for item in results.values()
    ),
}
(output / "report.json").write_text(json.dumps(report, indent=2))
print("CONTROL_PROBE " + json.dumps(report))
if not report["passed"]:
    raise RuntimeError(
        "One visual control did not affect the LED background, or altered poster color"
    )
