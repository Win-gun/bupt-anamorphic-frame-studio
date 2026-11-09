"""Render independent visibility evidence from the saved actual scene geometry.
All materials become unlit IDs, while the original poster remains an occluder.
"""
import sys, json
from pathlib import Path
import bpy
import numpy as np

base = Path(__file__).resolve().parents[1] / "examples/embedded-cube"
for layout in ("floating", "back_wall"):
    directory = base / layout
    bpy.ops.wm.open_mainfile(filepath=str(directory / "scene.blend"))
    scene = bpy.context.scene
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    colors = {
        "LEFT": (1, 0, 0),
        "RIGHT": (0, 1, 0),
        "CEILING": (0, 0, 1),
        "FLOOR": (1, 1, 0),
        "REAR": (1, 0, 1),
    }

    def emission(name, color):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        n = m.node_tree.nodes
        n.clear()
        out = n.new("ShaderNodeOutputMaterial")
        shader = n.new("ShaderNodeEmission")
        shader.inputs["Color"].default_value = (*color, 1)
        m.node_tree.links.new(shader.outputs[0], out.inputs[0])
        return m

    black = emission("Diagnostic black occluder", (0, 0, 0))
    for ob in scene.objects:
        if ob.type != "MESH":
            continue
        face = next(
            (
                key
                for key in colors
                if ("· " + key + " wall" in ob.name or "· " + key in ob.name)
            ),
            None,
        )
        m = emission("Diagnostic " + face, colors[face]) if face else black
        ob.data.materials.clear()
        ob.data.materials.append(m)
        for p in ob.data.polygons:
            p.material_index = 0
    scene.world.node_tree.nodes.clear()
    n = scene.world.node_tree.nodes
    out = n.new("ShaderNodeOutputWorld")
    bg = n.new("ShaderNodeBackground")
    bg.inputs[0].default_value = (0, 0, 0, 1)
    bg.inputs[1].default_value = 0
    scene.world.node_tree.links.new(bg.outputs[0], out.inputs[0])
    scene.render.filepath = str(directory / "face-visibility.png")
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(
        str(directory / "face-visibility.png"), check_existing=False
    )
    pixels = np.array(image.pixels[:]).reshape(-1, 4)[:, :3]
    counts = {
        key: int((np.max(np.abs(pixels - np.array(col)), axis=1) < 0.05).sum())
        for key, col in colors.items()
    }
    report = {
        "method": "Independent unlit ID render of saved solid meshes; poster remains black depth occluder",
        "pixels": counts,
        "visible_faces": sum(count > 50 for count in counts.values()),
        "threshold_pixels": 50,
        "all_five_visible": all(count > 50 for count in counts.values()),
        "rgb_ids": colors,
        "render_resolution": list(image.size),
    }
    (directory / "face-visibility.json").write_text(json.dumps(report, indent=2))
    print("FACE_VISIBILITY", layout, json.dumps(report))
