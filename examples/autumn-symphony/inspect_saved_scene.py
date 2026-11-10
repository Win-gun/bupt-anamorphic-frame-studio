"""Reopen the final .blend; inspect the actual saved meshes and original packed image."""
import bpy,json,hashlib
import numpy as np
from pathlib import Path
scene=bpy.context.scene
root=next(o for o in scene.objects if o.get('template')=='autumn_symphony')
c=json.loads(root['composition_json']);origin=np.array(c['center']);normal=np.array(c['normal'])
poster=next(o for o in scene.objects if o.name=='Original poster · untouched complete rectangle')
world=np.array([poster.matrix_world @ v.co for v in poster.data.vertices]);local_depth=(world-origin)@normal
assert np.ptp(local_depth)<1e-5
assert {tuple(round(x,6) for x in loop.uv) for loop in poster.data.uv_layers.active.data}=={(0,0),(0,1),(1,0),(1,1)}
material=poster.data.materials[0];assert any(n.type=='EMISSION' for n in material.node_tree.nodes)
tex=next(n for n in material.node_tree.nodes if n.type=='TEX_IMAGE');assert list(tex.image.size)==[4535,2551]
source=Path(__file__).resolve().parents[2]/'examples/v2/jiqi-qiuyun/original.png'
packed_hash=hashlib.sha256(bytes(tex.image.packed_file.data)).hexdigest();assert packed_hash==hashlib.sha256(source.read_bytes()).hexdigest()
leaves=[o for o in scene.objects if o.name.startswith('Sculpted maple leaf')];assert len(leaves)==9
wings=[o for o in scene.objects if o.name.startswith('Sculpted rear architectural wing')];assert len(wings)==2
wing_fronts={o.name:float(max(np.dot(np.array(o.matrix_world@v.co)-origin,normal) for v in o.data.vertices)) for o in wings}
assert all(z<-.5 for z in wing_fronts.values())
result={'passed':True,'blender':bpy.app.version_string,'engine':scene.render.engine,'poster_flat_depth_range_m':float(np.ptp(local_depth)),'poster_complete_uv':True,'packed_original_png_sha256':packed_hash,'packed_png_identical_to_original':True,'sculpted_maple_leaves':len(leaves),'curved_architectural_wings':len(wings),'wings_max_front_depth_m':wing_fronts,'actual_mesh_count':len([o for o in scene.objects if o.type=='MESH' and not o.name.startswith('Physical LED')])}
(Path(bpy.data.filepath).parent/'saved-scene-verification.json').write_text(json.dumps(result,indent=2)+'\n');print('SAVED_SCENE_PASS',json.dumps(result))
