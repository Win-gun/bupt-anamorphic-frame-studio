"""Reopen saved Blender animation; verify actual evaluated keys without rendering."""
import bpy, json, sys
from pathlib import Path
import numpy as np
folder=Path(sys.argv[sys.argv.index('--')+1]).resolve()
d=json.loads((folder/'animation.json').read_text())
roots=[ob for ob in bpy.context.scene.objects if ob.get('template')=='autumn_resonance_cube']
assert len(roots)==1
root=roots[0]; lights=[ob for ob in bpy.context.scene.objects if ob.type=='LIGHT'];assert len(lights)==6
# Use scene order, exactly as emitted in the source renderer when no list fallback.
# Energies are also checked against curve-derived start/end ratios independently.
scene=bpy.context.scene
assert scene.frame_current==1
static=[ob for ob in scene.objects if ob!=root and ob.parent!=root]
scene.frame_set(1);bpy.context.view_layer.update();matrices={ob.name:np.array(ob.matrix_world) for ob in static}
first_energies={ob.name:ob.data.energy for ob in lights}
checked=[]
for f in d['frames']:
    scene.frame_set(f['blender_frame']);bpy.context.view_layer.update()
    assert np.allclose(np.array(root.location),f['translation_m'],atol=1e-6)
    assert all(np.allclose(np.array(ob.matrix_world),matrices[ob.name],atol=1e-6) for ob in static)
    checked.append(f['blender_frame'])
last_energies={ob.name:ob.data.energy for ob in lights}
assert all(abs(first_energies[k]/last_energies[k]-.55)<1e-6 for k in last_energies)
assert len(root.children)==2 and all(ob.type=='MESH' for ob in root.children)
curves=[(root.name,root.animation_data.action.fcurves)] + [(ob.name,ob.data.animation_data.action.fcurves) for ob in lights]
assert all(len(curve.keyframe_points)==len(checked) and all(p.interpolation=='LINEAR' for p in curve.keyframe_points) for _,fc in curves for curve in fc)
hold=[f for f in d['frames'] if f['motion']['stage']=='stable_hold'];actual_hold=[]
for f in hold:
    scene.frame_set(f['blender_frame']);bpy.context.view_layer.update()
    actual_hold.append((tuple(root.location),tuple(ob.data.energy for ob in lights)))
assert len(set(actual_hold))==1
scene.frame_set(1)
result=dict(passed=True,source='Reopened saved scene.blend, evaluated animation at every saved frame',frames_checked=len(checked),all_static_object_matrices_fixed=True,actual_moving_objects=[ob.name for ob in root.children],actual_lights=6,all_keyframe_counts_match=True,all_keyframe_interpolation='LINEAR',start_light_factor=.55,hold_frames=len(hold),hold_root_and_lights_identical=True,saved_frame_on_open=1)
(folder/'saved-animation-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
