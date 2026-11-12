"""Check the packed poster and sightlines in a saved Amber Gallery scene."""
import hashlib
import json

import bpy


scene = bpy.context.scene
poster = bpy.data.objects["Original poster · full image"]
depsgraph = bpy.context.evaluated_depsgraph_get()
camera_position = scene.camera.matrix_world.translation
bottom_left, bottom_right, _, top_left = [
    poster.matrix_world @ vertex.co for vertex in poster.data.vertices
]
unobstructed = 0
samples = 0
for row in range(17):
    for col in range(31):
        u = (col + 0.5) / 31
        v = (row + 0.5) / 17
        point = (
            bottom_left
            + (bottom_right - bottom_left) * u
            + (top_left - bottom_left) * v
        )
        direction = (point - camera_position).normalized()
        hit, _, _, _, obj, _ = scene.ray_cast(depsgraph, camera_position, direction)
        samples += 1
        unobstructed += bool(hit and obj.name == poster.name)

image = next(
    node.image
    for node in poster.data.materials[0].node_tree.nodes
    if node.type == "TEX_IMAGE"
)
uv = {tuple(loop.uv) for loop in poster.data.uv_layers.active.data}
assert uv == {(0, 0), (0, 1), (1, 0), (1, 1)}
assert unobstructed == samples, f"{samples - unobstructed} poster rays obstructed"
print(
    "AMBER_GALLERY_CHECK",
    json.dumps(
        {
            "poster_rays_unobstructed": unobstructed,
            "poster_rays_tested": samples,
            "full_uv": True,
            "packed_poster_sha256": hashlib.sha256(
                bytes(image.packed_file.data)
            ).hexdigest(),
            "maple_surfaces": sum(
                o.name.startswith("Folded maple") and "vein" not in o.name
                for o in scene.objects
            ),
        }
    ),
)
