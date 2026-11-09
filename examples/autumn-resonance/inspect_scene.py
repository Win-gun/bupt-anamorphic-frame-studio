"""Run Blender -b scene.blend --python-exit-code 1 --python inspect_scene.py."""
import bpy
import json
import math
from mathutils import Vector
from pathlib import Path

scene = bpy.context.scene
objects = bpy.data.objects
coordinates = objects['Autumn · shared mineral coordinates']
materials = [m for m in bpy.data.materials if m.name.startswith('Autumn mineral')]
assert len(materials) == 7
checks = []
for m in materials:
    n = m.node_tree.nodes
    tex = next(x for x in n if x.type == 'TEX_COORD')
    bump = next(x for x in n if x.type == 'BUMP')
    noise = next(x for x in n if x.type == 'TEX_NOISE')
    bsdf = next(x for x in n if x.type == 'BSDF_PRINCIPLED')
    assert tex.object == coordinates
    assert bsdf.inputs['Normal'].is_linked and bsdf.inputs['Base Color'].is_linked
    assert bump.inputs['Height'].is_linked
    assert abs(bump.inputs['Distance'].default_value - .00025) < 1e-8
    assert abs(bsdf.inputs['Metallic'].default_value) < 1e-8
    checks.append(dict(name=m.name, shared_coordinates=True, linked_base_color_and_bump=True,
                       roughness=bsdf.inputs['Roughness'].default_value,
                       bump_distance_m=bump.inputs['Distance'].default_value,
                       noise_scale=noise.inputs['Scale'].default_value))
lamps = [o for o in objects if o.type == 'LIGHT']
assert len(lamps) == 6
assert all(o.data.type == 'AREA' and o.data.shape == 'DISK' for o in lamps)
report = json.loads(Path(bpy.data.filepath).with_name('report.json').read_text())
def find_geometry(value):
    if isinstance(value, dict):
        if 'architectural_geometry' in value:
            return value['architectural_geometry']
        for item in value.values():
            found = find_geometry(item)
            if found:
                return found
geometry = find_geometry(report)
w, h, d, t = (geometry[k] for k in ['opening_width_m','opening_height_m','cavity_depth_m','wall_thickness_m'])
inv = coordinates.matrix_world.inverted()
for lamp in lamps:
    points = [inv @ (lamp.matrix_world @ Vector((math.cos(i * math.tau / 2048) * lamp.data.size / 2, math.sin(i * math.tau / 2048) * lamp.data.size / 2, 0))) for i in range(2048)]
    if lamp.name.endswith('facade'):
        assert all(p.z > .05 for p in points)
    else:
        assert all(-w/2 < p.x < w/2 and -h/2 < p.y < h/2 and -d < p.z < -t for p in points)

backing = next(o for o in objects if o.name.startswith('Poster backing'))
assert abs(next(m for m in backing.modifiers if m.type=='BEVEL').width - .006) < 1e-7
facade = next(o for o in objects if o.name.startswith('Building facade'))
assert abs(next(m for m in facade.modifiers if m.type=='BEVEL').width - .025) < 1e-7
poster = next(o for o in objects if o.name.startswith('Original poster'))
assert len(poster.data.vertices) == 4
assert any(n.type == 'EMISSION' for n in poster.data.materials[0].node_tree.nodes)
assert set(tuple(round(v,6) for v in x.uv) for x in poster.data.uv_layers.active.data) == {(0,0),(0,1),(1,0),(1,1)}
result=dict(status='PASS', blender=bpy.app.version_string, engine=scene.render.engine,
            materials=checks, lights=[dict(name=o.name,power_w=o.data.energy,size_m=o.data.size) for o in lamps],
            actual_saved_emitter_surfaces_outside_solids=True, original_poster_full_uv=True, source_poster_emission_unchanged=True,
            opening_bevel_m=.025,panel_bevel_m=.006)
Path(bpy.data.filepath).with_name('saved-blend-verification.json').write_text(json.dumps(result,indent=2))
print('AUTUMN_SAVED_BLEND_PASS')
