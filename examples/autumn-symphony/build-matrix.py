"""Real Blender build-only matrix; no extra image fixtures or poster replacements."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'studio'))
import bpy
from studio.composition import solve_composition
from studio.symphony_scene import build_exhibition
from blender_render import textured_material
config=json.loads((ROOT/'configs/autumn-symphony.json').read_text())
poster=ROOT/'examples/v2/jiqi-qiuyun/original.png'
results=[]
for aspect,size in [('16:9',(4535,2551)),('square',(1000,1000)),('portrait',(800,1200))]:
 for scale in [.1,.5,.88,1.0]:
  bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
  bpy.context.scene.world.use_nodes=True
  config['frame']['scale']=scale
  try:
   c=solve_composition(config,size)
   out=build_exhibition(config,poster,c,textured_material)
   wings=[o for o in out['objects'] if 'rear architectural wing' in o.name]
   max_local_z=max((v.co-__import__('mathutils').Vector(c['center'])).dot(__import__('mathutils').Vector(c['normal'])) for o in wings for v in o.data.vertices)
   assert max_local_z<-.2
   results.append({'aspect':aspect,'scale':scale,'status':'PASS','decor_guard_all_pass':out['report']['architectural_geometry']['projected_decoration_guard_all_pass'],'rear_wing_max_local_z':max_local_z,'meshes':len(out['objects'])})
  except Exception as e:results.append({'aspect':aspect,'scale':scale,'status':'FAIL','error':str(e)})
(ROOT/'examples/autumn-symphony/build-matrix.json').write_text(json.dumps(results,indent=2))
print('SYMPHONY_BUILD_MATRIX',json.dumps(results))
assert all(x['status']=='PASS' for x in results)
