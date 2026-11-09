"""Real Blender renderer and camera-to-physical-LED inverse projection.
Run: Blender -b --python studio/blender_render.py -- --config C --poster P --output O
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geometry import dimensions, surface_grid, surface_point, visible_points


def material(name, color, emission=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes
    n.clear()
    out = n.new('ShaderNodeOutputMaterial')
    shader = n.new('ShaderNodeEmission' if emission else 'ShaderNodeBsdfPrincipled')
    shader.inputs['Color' if emission else 'Base Color'].default_value = (*color, 1)
    if not emission:
        shader.inputs['Roughness'].default_value = .27
        shader.inputs['Metallic'].default_value = .35
    m.node_tree.links.new(shader.outputs[0], out.inputs['Surface'])
    return m


def cube(name, location, size, mat, bevel=.04):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    ob = bpy.context.object
    ob.name = name
    ob.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(mat)
    if bevel:
        mod = ob.modifiers.new('Machined edges', 'BEVEL'); mod.width = min(bevel, min(size)/4); mod.segments = 3
        ob.data.use_auto_smooth = True
        ob.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return ob


def save_pixels(path, pixels):
    """Arrays use bottom-left origin, matching Blender's image pixels and UVs."""
    h, w = pixels.shape[:2]
    rgba = np.ones((h, w, 4), np.float32); rgba[:, :, :3] = np.clip(pixels[:, :, :3], 0, 1)
    im = bpy.data.images.new(path.stem, width=w, height=h, alpha=False)
    im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = str(path); im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)


def read_pixels(path):
    im = bpy.data.images.load(str(path), check_existing=False)
    im.colorspace_settings.name = 'Non-Color'
    a = np.empty(im.size[0]*im.size[1]*4, np.float32)
    im.pixels.foreach_get(a)
    a = a.reshape(im.size[1], im.size[0], 4)[:, :, :3].copy()
    bpy.data.images.remove(im)
    return a


def render(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def textured_material(path, name):
    m = material(name, (1, 1, 1), True)
    tex = m.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(path), check_existing=False)
    tex.image.colorspace_settings.name = 'sRGB'
    tex.interpolation = 'Linear'; tex.extension = 'CLIP'
    shader = next(n for n in m.node_tree.nodes if n.type == 'EMISSION')
    m.node_tree.links.new(tex.outputs['Color'], shader.inputs['Color'])
    return m


def build_target(config, poster):
    f = config['frame']; w, h, dep, b = [f[k] for k in ('width_m', 'height_m', 'depth_m', 'border_m')]
    x, y, z = f.get('position', [0, .7, 0])
    template = f.get('template', 'deep')
    if template == 'float': y -= dep
    rail_depth = dep*.35 if template == 'float' else dep
    color = f.get('color', '#234863').lstrip('#')
    rgb = tuple((int(color[i:i+2], 16)/255)**2.2 for i in (0, 2, 4))
    metal = material('Anodized frame', rgb)
    dark = material('Recess shadow', (.012, .018, .026))
    template = f.get('template', 'deep')
    cube('Deep back enclosure', (x, y+dep*.9, z), (w, max(.001, dep*.12), h), dark)
    for side in (-1, 1):
        cube('Vertical frame rail', (x+side*(w-b)/2, y, z), (b, rail_depth, h), metal)
        cube('Horizontal frame rail', (x, y, z+side*(h-b)/2), (w-2*b, rail_depth, b), metal)
    image = bpy.data.images.load(str(poster), check_existing=False)
    aspect = image.size[0]/image.size[1]
    iw, ih = w-2.2*b, h-2.2*b
    if iw/ih > aspect: iw = ih*aspect
    else: ih = iw/aspect
    inset = .08*dep if template == 'float' else .28*dep
    # Face in the XZ plane. UV does not crop or stretch the original poster.
    verts = [(x-iw/2,y+inset,z-ih/2),(x+iw/2,y+inset,z-ih/2),(x+iw/2,y+inset,z+ih/2),(x-iw/2,y+inset,z+ih/2)]
    me = bpy.data.meshes.new('Original poster mesh'); me.from_pydata(verts, [], [(0,1,2,3)]); me.uv_layers.new()
    for loop, uv in zip(me.uv_layers.active.data, [(0,0),(1,0),(1,1),(0,1)]): loop.uv = uv
    ob = bpy.data.objects.new('Original poster · aspect preserved', me); bpy.context.collection.objects.link(ob)
    me.materials.append(textured_material(poster, 'Original artwork'))
    if template == 'float':
        accent = material('Floating luminous rim', (.06,.5,.7), True)
        for side in (-1,1): cube('Floating spacer', (x+side*(iw/2+.04),y+inset+.02,z), (.035,.04,ih), accent, .01)
    elif template == 'glass':
        glass = material('Optical glass', (.55,.8,.9))
        node = next(n for n in glass.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        node.inputs['Transmission'].default_value = .2; node.inputs['Roughness'].default_value = .09
        node.inputs['Alpha'].default_value = .12
        glass.blend_method = 'BLEND'; glass.use_screen_refraction = True
        bpy.context.scene.eevee.use_ssr = True; bpy.context.scene.eevee.use_ssr_refraction = True
        node.inputs['IOR'].default_value = 1.45
        cube('Protective glazing', (x,y-.05,z),(w-2*b,.025,h-2*b),glass,.015)
    for pos, power, size in [((-4,-6,7),1800,6),((6,-2,3),1300,5)]:
        bpy.ops.object.light_add(type='AREA', location=pos)
        light = bpy.context.object; light.data.energy=power; light.data.shape='DISK'; light.data.size=size
        light.rotation_euler=(Vector((x,y,z))-light.location).to_track_quat('-Z','Y').to_euler()
    return {'poster_original_pixels':list(image.size), 'poster_display_metres':[iw,ih], 'poster_aspect_preserved':True,'effective_frame_position':[x,y,z]}


def build_screen(config, atlas):
    s=config['screen']; d=dimensions(s)
    # Pixel boundaries at joints; 1 degree tessellation or finer on the arc.
    segments=max(96, math.ceil(s['pixels'][1]*config['render']['scale']))
    ss=[0,d['left']]+[d['left']+d['arc']*i/segments for i in range(1,segments+1)]+[d['length']]
    verts=[]
    for v in ss:
        verts.extend([surface_point(v,-d['height']/2,s),surface_point(v,d['height']/2,s)])
    faces=[(2*i,2*i+2,2*i+3,2*i+1) for i in range(len(ss)-1)]
    mesh=bpy.data.meshes.new('Continuous LED geometry'); mesh.from_pydata(verts,[],faces); mesh.uv_layers.new()
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            vi=mesh.loops[li].vertex_index
            mesh.uv_layers.active.data[li].uv=(ss[vi//2]/d['length'],vi%2)
    ob=bpy.data.objects.new('Physical LED · planar arc planar',mesh); bpy.context.collection.objects.link(ob)
    led_mat=textured_material(atlas,'LED emission atlas'); led_mat.use_backface_culling=True
    mesh.materials.append(led_mat)
    return ob


def main():
    started=time.time()
    parser=argparse.ArgumentParser(); parser.add_argument('--config',required=True); parser.add_argument('--poster',required=True); parser.add_argument('--output',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    config=json.loads(Path(args.config).read_text()); out=Path(args.output).resolve(); out.mkdir(parents=True,exist_ok=True)
    poster=Path(args.poster).resolve(); s=config['screen']; d=dimensions(s); r=config['render']
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene; scene.render.engine='BLENDER_EEVEE'; scene.eevee.taa_render_samples=r.get('samples',16)
    scene.view_settings.view_transform='Standard'; scene.view_settings.look='None'
    scene.view_settings.look='None'; scene.view_settings.exposure=0; scene.view_settings.gamma=1
    scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'; scene.render.film_transparent=False
    scene.world.color=(.008,.008,.008)
    aw=max(32,round(sum(s['pixels'])*r['scale'])); ah=max(32,round(s['height_px']*r['scale']))
    scene.render.resolution_x=aw; scene.render.resolution_y=ah; scene.render.resolution_percentage=100
    scene.render.dither_intensity=0
    bpy.ops.object.camera_add(location=config['camera']['position']); camera=bpy.context.object
    camera.rotation_euler=(Vector(config['camera']['target'])-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='PERSP'; camera.data.sensor_fit='HORIZONTAL'; camera.data.lens=36/(2*math.tan(math.radians(config['camera']['fov_deg'])/2)); scene.camera=camera
    artwork=build_target(config,poster); target_objects=list(scene.objects)
    render(scene,out/'scene.png'); target=read_pixels(out/'scene.png')
    # project each physical LED texel through the actual Blender perspective camera
    bpy.context.view_layer.update()
    matrix=np.asarray(camera.matrix_world.inverted(),dtype=float)
    atlas=np.zeros((ah,aw,3),np.float32); valid_count=0
    fx=.5/math.tan(math.radians(config['camera']['fov_deg'])/2); fy=fx*aw/ah
    for row in range(0,ah,96):
        end=min(ah,row+96)
        u=(np.arange(aw)+.5)/aw; v=(np.arange(row,end)+.5)/ah
        points,normals=surface_grid(u[None,:]*d['length'],(v[:,None]-.5)*d['height'],s)
        local=points@matrix[:3,:3].T+matrix[:3,3]
        depth=-local[:,:,2]
        with np.errstate(divide='ignore',invalid='ignore'):
            pu=.5+fx*local[:,:,0]/depth; pv=.5+fy*local[:,:,1]/depth
        valid=(depth>0)&(pu>=0)&(pu<=1)&(pv>=0)&(pv<=1)&visible_points(points,normals,list(camera.location),s)
        xx=np.nan_to_num(np.clip(pu*aw-.5,0,aw-1),nan=0); yy=np.nan_to_num(np.clip(pv*ah-.5,0,ah-1),nan=0)
        x0=np.floor(xx).astype(int); y0=np.floor(yy).astype(int); x1=np.minimum(x0+1,aw-1); y1=np.minimum(y0+1,ah-1)
        wx=(xx-x0)[...,None]; wy=(yy-y0)[...,None]
        sample=(target[y0,x0]*(1-wx)+target[y0,x1]*wx)*(1-wy)+(target[y1,x0]*(1-wx)+target[y1,x1]*wx)*wy
        atlas[row:end]=np.where(valid[...,None],sample,0); valid_count+=int(valid.sum())
    save_pixels(out/'atlas.png',atlas)
    for ob in target_objects:
        if ob.type!='CAMERA': ob.hide_render=True
    screen=build_screen(config,out/'atlas.png')
    render(scene,out/'simulation.png'); simulated=read_pixels(out/'simulation.png')
    original_mat=screen.data.materials[0]; screen.data.materials[0]=material('Visibility mask',(1,1,1),True)
    screen.data.materials[0].use_backface_culling=True
    world_color=scene.world.color[:]; scene.world.color=(0,0,0)
    render(scene,out/'mask.png'); mask_rgb=read_pixels(out/'mask.png'); mask=mask_rgb.min(axis=2)>.98
    # Conservative edge removal excludes raster anti-alias coverage, not content errors.
    inner=mask.copy()
    for dy,dx in ((0,1),(0,-1),(1,0),(-1,0)):
        inner &= np.roll(mask,(dy,dx),(0,1))
    inner[[0,-1],:]=False; inner[:,[0,-1]]=False
    err=np.abs(simulated-target); diff=np.where(mask[...,None],err,0)
    save_pixels(out/'difference.png',diff)
    check=atlas.copy(); yy,xx=np.indices((ah,aw)); grid=((xx%(max(8,aw//32))<1)|(yy%(max(8,ah//24))<1))
    check[grid]=(.2,.85,1)
    for joint in np.cumsum(s['pixels'])[:-1]:
        col=round(joint/sum(s['pixels'])*aw); check[:,max(0,col-1):col+2]=(1,.25,.05)
    save_pixels(out/'calibration.png',check)
    screen.data.materials[0]=original_mat; scene.world.color=world_color
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
    values=err[inner]; mse=float(np.mean(values**2)) if values.size else None
    mae=float(np.mean(values)) if values.size else None
    full_mae=float(err[mask].mean()) if mask.any() else None
    foreground=np.max(np.abs(target-target[0,0]),axis=2)>.025
    foreground_visible=foreground & inner
    foreground_mae=float(err[foreground_visible].mean()) if foreground_visible.any() else None
    coverage=float((foreground & mask).sum()/max(1,foreground.sum()))
    passed=bool(mae is not None and mae<=.04 and foreground_mae is not None and foreground_mae<=.04 and coverage>=.98 and inner.sum()>100)
    report={'passed':passed,'engine':'Blender '+bpy.app.version_string+' EEVEE','method':'3D physical continuous surface, perspective inverse projection, bilinear texture sampling, analytic front-face and self-occlusion tests, independent Blender camera re-render',
        'physical':d,'atlas_pixels':[aw,ah],'nominal_atlas_pixels':[sum(s['pixels']),s['height_px']], 'scale':r['scale'],
        'calibration_status':'MEASURED_INPUT' if s.get('calibrated') else 'NOMINAL_UNCALIBRATED',
        'metrics':{'mae_srgb':mae,'full_mask_mae_srgb':full_mae,'interior_mae_srgb':mae,'foreground_mae_srgb':foreground_mae,'foreground_coverage':coverage,'foreground_pixels':int(foreground_visible.sum()),'rmse_srgb':math.sqrt(mse) if mse is not None else None,'psnr_db':-10*math.log10(max(mse,1e-12)) if mse is not None else None,'p95_absolute_error':float(np.quantile(values,.95)) if values.size else None,'mask_pixels':int(inner.sum()),'visible_screen_fraction':float(mask.mean()),'valid_atlas_fraction':valid_count/(aw*ah)},
        'verification':{'criterion':'interior and foreground mean absolute sRGB error <= 0.04; >=98% target foreground covered by actual visible screen','threshold_mae':.04,'pass':passed},
        'limitations':['Nominal geometry is not field calibration; measured camera pose, lens distortion and LED transfer response are required on site.','Pixels outside the camera frustum or occluded/back-facing physical surface are black.','Comparison excludes a one-pixel raster boundary; texture resampling and finite curved mesh tessellation contribute remaining error.'],
        'coordinate_system':'metres; Z up; left Y=0; arc Y=R(cos(theta)-1); right tangent (cos(theta),-sin(theta)); centered surface X bounds',
        'artwork':artwork,'elapsed_seconds':time.time()-started,'config':config}
    (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print('RENDER_REPORT '+json.dumps(report['metrics']))

if __name__=='__main__':
    main()
