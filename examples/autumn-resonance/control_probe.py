import bpy,json,sys
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root));sys.path.insert(0,str(root/'studio'))
from studio.blender_render import build_target
base=json.loads((root/'configs/autumn-resonance.json').read_text())
poster=root/'examples/v2/jiqi-qiuyun/original.png'
def snapshot(settings):
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 bpy.context.scene.world.use_nodes=True
 c=json.loads(json.dumps(base));c['autumn'].update(settings)
 e=build_target(c,poster)
 m=next(o for o in e['objects'] if o.name.startswith('Excavated room · REAR')).data.materials[0]
 n=m.node_tree.nodes;shader=next(n for n in n if n.type=='BSDF_PRINCIPLED')
 ramp=next(n for n in n if n.type=='VALTORGB' and 'spatial' in n.label)
 facade=next(o for o in e['objects'] if o.name.startswith('Building facade'))
 backing=next(o for o in e['objects'] if o.name.startswith('Poster backing'))
 bg=next(n for n in bpy.context.scene.world.node_tree.nodes if n.type=='BACKGROUND')
 return dict(energies=[o.data.energy for o in e['lights']],sizes=[o.data.size for o in e['lights']],
  bump=next(n for n in n if n.type=='BUMP').inputs['Distance'].default_value,
  ramp=[list(x.color) for x in ramp.color_ramp.elements],world=bg.inputs['Strength'].default_value,
  specular=shader.inputs['Specular'].default_value,
  depth=e['report']['architectural_geometry']['poster_distance_from_front_m'],
  opening_bevel=next(m for m in facade.modifiers if m.type=='BEVEL').width,
  panel_bevel=next(m for m in backing.modifiers if m.type=='BEVEL').width)
original=snapshot({}); cases={'light_intensity':(1.3,'energies'),'softness':(.3,'sizes'),
 'texture_strength_m':(.0001,'bump'),'gradient_strength':(.5,'ramp'),
 'ambient':(.6,'world'),'shadow_strength':(.1,'world'),'edge_highlight':(.3,'specular'),
 'poster_depth_fraction':(.6,'depth'),'opening_bevel_m':(.015,'opening_bevel'),
 'panel_bevel_m':(.003,'panel_bevel'),'variant':('warm','energies')}
results={}
for key,(value,measured) in cases.items():
 changed=snapshot({key:value});assert changed[measured]!=original[measured],(key,measured)
 results[key]=dict(input=value,actual_socket_or_geometry=measured,before=original[measured],after=changed[measured],changed=True)
p=root/'examples/autumn-resonance/control-bindings.json';p.write_text(json.dumps(dict(blender=bpy.app.version_string,passed=True,method='Rebuild real Blender objects; inspect actual linked sockets, modifiers, physical poster positions and lamp values',checks=results),indent=2));print('CONTROL_BINDINGS_PASS',len(results))
