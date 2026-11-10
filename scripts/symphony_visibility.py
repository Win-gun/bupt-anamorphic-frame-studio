"""Blender saved-scene diagnostic: actual visible themed geometry inside physical LED.
Run Blender -b scene.blend --python this_file -- --output directory.
Never saves changes back to the original .blend.
"""
import argparse
import json
import sys
from pathlib import Path
import bpy
import numpy as np

args = argparse.ArgumentParser()
args.add_argument("--output", type=Path, required=True)
options = args.parse_args(sys.argv[sys.argv.index("--") + 1 :])
out = options.output
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = 16
scene.render.resolution_percentage = max(
    1, round(100 * 1092 / scene.render.resolution_x)
)
scene.world.use_nodes = True
world = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
world.inputs["Color"].default_value = (0, 0, 0, 1)
world.inputs["Strength"].default_value = 0
colors = {"maple": (1, 0, 0), "sculpture": (0, 1, 0), "wing": (0, 0, 1)}


def material(name, color):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    s = m.node_tree.nodes.new("ShaderNodeEmission")
    o = m.node_tree.nodes.new("ShaderNodeOutputMaterial")
    s.inputs["Color"].default_value = (*color, 1)
    m.node_tree.links.new(s.outputs[0], o.inputs["Surface"])
    return m


black = material("ID black occluders", (0, 0, 0))
mats = {k: material("ID " + k, c) for k, c in colors.items()}
screen = next(o for o in scene.objects if o.name.startswith("Physical LED"))
meshes = [o for o in scene.objects if o.type == "MESH" and o != screen]
for ob in meshes:
    name = ob.name.lower()
    key = (
        "maple"
        if "sculpted maple leaf" in name
        else "wing"
        if "wing" in name
        else "sculpture"
        if any(s in name for s in ["cantabile", "overture", "acoustic wave"])
        else None
    )
    ob.data.materials.clear()
    ob.data.materials.append(mats[key] if key else black)
    for p in ob.data.polygons:
        p.material_index = 0
    ob.hide_render = False
screen.hide_render = True
scene.render.filepath = str(out / "decoration-ids.png")
bpy.ops.render.render(write_still=True)


def pixels(path):
    im = bpy.data.images.load(str(path), check_existing=False)
    im.colorspace_settings.name = "Non-Color"
    return np.array(im.pixels[:]).reshape(im.size[1], im.size[0], 4)[:, :, :3]


ids = pixels(out / "decoration-ids.png")
for ob in meshes:
    ob.hide_render = True
screen.hide_render = False
screen.data.materials.clear()
screen.data.materials.append(material("ID physical coverage", (1, 1, 1)))
scene.render.filepath = str(out / "physical-mask.png")
bpy.ops.render.render(write_still=True)
mask = pixels(out / "physical-mask.png").min(axis=2) > 0.98
counts = {}
for key, color in colors.items():
    hit = np.max(np.abs(ids - np.array(color)), axis=2) < 0.03
    counts[key] = {
        "visible_in_frustum": int(hit.sum()),
        "visible_on_led": int((hit & mask).sum()),
        "led_fraction": float((hit & mask).sum() / max(1, hit.sum())),
    }
assert all(c["visible_on_led"] > 30 for c in counts.values()), counts
(out / "visibility.json").write_text(
    json.dumps(
        {
            "method": "Actual unlit group-ID render of saved geometry intersected with independent physical LED mask; original poster retained as black depth occluder",
            "groups": counts,
            "all_groups_visible_on_led": True,
        },
        indent=2,
    )
    + "\n"
)
print("DECOR_VISIBILITY", json.dumps(counts))
