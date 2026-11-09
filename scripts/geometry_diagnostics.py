#!/usr/bin/env python3
"""Run with Blender --background --python scripts/geometry_diagnostics.py.

Creates actual single-sided geometry renders for both curvature hypotheses and
an orthographic top view. These are synthetic sign checks, NOT site calibration.
"""
import json
import math
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bpy
import numpy as np
from mathutils import Vector
from studio.geometry import dimensions, surface_grid, visible_points

OUT = ROOT/'examples/v2/diagnostics'
OUT.mkdir(parents=True, exist_ok=True)


def material(name, color, one_sided=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nodes = m.node_tree.nodes; nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    emission = nodes.new('ShaderNodeEmission'); emission.inputs['Color'].default_value = (*color,1)
    if one_sided:
        geometry = nodes.new('ShaderNodeNewGeometry'); transparent = nodes.new('ShaderNodeBsdfTransparent')
        mix = nodes.new('ShaderNodeMixShader')
        m.node_tree.links.new(geometry.outputs['Backfacing'], mix.inputs[0])
        m.node_tree.links.new(emission.outputs[0], mix.inputs[1]); m.node_tree.links.new(transparent.outputs[0], mix.inputs[2])
        m.node_tree.links.new(mix.outputs[0], out.inputs[0])
    else: m.node_tree.links.new(emission.outputs[0], out.inputs[0])
    return m


def line(name, points, mat, radius=.012):
    curve = bpy.data.curves.new(name, 'CURVE'); curve.dimensions = '3D'; curve.bevel_depth = radius; curve.bevel_resolution = 1
    spline = curve.splines.new('POLY'); spline.points.add(len(points)-1)
    for p, co in zip(spline.points, points): p.co = (*co, 1)
    obj = bpy.data.objects.new(name, curve); bpy.context.collection.objects.link(obj); obj.data.materials.append(mat)
    return obj


def camera(position, target, top=False):
    data = bpy.data.cameras.new('Diagnostic camera'); obj = bpy.data.objects.new('Diagnostic camera', data)
    bpy.context.collection.objects.link(obj); obj.location = position
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    if top: data.type = 'ORTHO'; data.ortho_scale = 18
    else: data.lens = 36/(2*math.tan(math.radians(65)/2)); data.sensor_width = 36
    bpy.context.scene.camera = obj


def render(path):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'; scene.cycles.samples = 8
    scene.render.resolution_x = 1200; scene.render.resolution_y = 1000; scene.render.resolution_percentage = 100
    scene.world.color = (.015,.015,.015)
    scene.view_settings.view_transform = 'Standard'
    scene.render.filepath = str(path); bpy.ops.render.render(write_still=True)


report = {'purpose':'Synthetic geometry sign/visibility diagnostics; site curvature and yaw remain unverified', 'cases':[]}
for curvature, pose in [('concave',[-2,-14,2]), ('convex',[12,-14,2])]:
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    screen = json.loads((ROOT/'configs/bupt-curved-led.json').read_text())['screen']
    screen.update(curvature=curvature, yaw_deg=0)
    d = dimensions(screen)
    mats = [material('Left red',(.65,.12,.08), True), material('Arc green',(.12,.65,.2), True), material('Right blue',(.1,.3,.85),True)]
    white = material('Grid',(.5,.55,.6)); yellow = material('Front normal',(1,.75,.05))
    boundaries = [0,d['left'],d['left']+d['arc'],d['length']]
    for segment in range(3):
        ss = np.linspace(boundaries[segment],boundaries[segment+1],121)
        lower,_ = surface_grid(ss,-d['height']/2,screen); upper,_ = surface_grid(ss,d['height']/2,screen)
        vertices = np.concatenate([lower,upper]).tolist(); count = len(ss)
        faces = [(i,i+1,i+1+count,i+count) for i in range(count-1)]
        mesh = bpy.data.meshes.new('Single sided surface'); mesh.from_pydata(vertices,[],faces); mesh.update()
        obj = bpy.data.objects.new(['Left','Arc','Right'][segment],mesh); bpy.context.collection.objects.link(obj); obj.data.materials.append(mats[segment])
    ss = np.linspace(0,d['length'],301)
    for z in np.arange(-d['height']/2,d['height']/2+.01,.6):
        pp,nn = surface_grid(ss,z,screen); line('Horizontal grid', pp+nn*.008,white,.006)
    for s in np.arange(0,d['length']+.01,.6):
        pp,nn=surface_grid([s,s],[-d['height']/2,d['height']/2],screen)
        line('Vertical grid',pp+nn*.008,white,.006)
    samples = [d['left']/2,d['left']+d['arc']/2,d['length']-.5]
    pp,nn = surface_grid(samples,0,screen)
    for p,n in zip(pp,nn): line('Front normal',[p,p+n*1.2],yellow,.035)
    camera(pose,[0,0,0]); render(OUT/f'{curvature}-front.png')
    # Footprint is shown independently from the zero-thickness panel top edge.
    pp_top,nn_top = surface_grid(ss,d['height']/2+.08,screen)
    for i,(start,end) in enumerate(zip(boundaries[:-1],boundaries[1:])):
        p,_=surface_grid(np.linspace(start,end,121),d['height']/2+.08,screen)
        line('Top footprint',p,material('Footprint '+str(i),[(.9,.15,.1),(.1,.9,.25),(.15,.4,1)][i]),.055)
    p,n=surface_grid(samples,d['height']/2+.08,screen)
    for a,b in zip(p,n): line('Top front normal',[a,a+b*1.3],yellow,.045)
    camera([0,2 if curvature == 'convex' else -2,22],[0,2 if curvature == 'convex' else -2,0],top=True); render(OUT/f'{curvature}-top.png')
    report['cases'].append({'curvature':curvature,'yaw_deg':0,'camera_position':pose,'camera_target':[0,0,0],
                            'segment_samples_s':samples,'points':pp.tolist(),'front_normals':nn.tolist(),
                            'sample_front_visible':visible_points(pp,nn,pose,screen).tolist(),
                            'renders':[f'{curvature}-front.png',f'{curvature}-top.png']})
(OUT/'geometry-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('GEOMETRY_DIAGNOSTICS_COMPLETE',OUT)
