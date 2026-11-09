"""Real camera close-up of unchanged minerals in the saved exhibition."""
import bpy
from mathutils import Vector
from pathlib import Path
scene = bpy.context.scene
coords = bpy.data.objects['Autumn · shared mineral coordinates']
def point(x,y,z):
    return coords.matrix_world @ Vector((x,y,z))
facade = next(o for o in bpy.data.objects if o.name.startswith('Excavated room · LEFT'))
# Recover the room inner x coordinate, not a second hand-constructed geometry.
inv = coords.matrix_world.inverted()
inner_x = max((inv @ v.co).x for v in facade.data.vertices)
camera = scene.camera
camera.location = point(inner_x + 1.45, -.25, -1.05)
target = point(inner_x, .35, -2.05)
camera.rotation_euler = (target - camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type = 'PERSP'
camera.data.lens = 40
scene.render.resolution_x = 1024
scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.cycles.samples = 128
scene.render.filepath = str(Path(bpy.data.filepath).parents[2] / 'material-left-closeup.png')
bpy.ops.render.render(write_still=True)
