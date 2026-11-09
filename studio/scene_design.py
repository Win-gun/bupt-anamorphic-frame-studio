"""Camera-aligned exhibition architecture. Artwork is the unmodified source texture.
The frame is a swept, closed rectangular cross-section, with mitered corners.
"""
import math

# (outward offset / border, front depth / border): a closed machined section.
FRAME_PROFILE = [(0, -.34), (0, .08), (.08, .18), (.18, .18), (.23, .09),
                 (.31, .09), (.38, .26), (.72, .26), (.88, .15), (1, .02),
                 (1, -.48), (.9, -.58), (.12, -.58)]
PRESETS = {
    'gold': ((.48,.29,.085), .88, .24),
    'brushed_metal': ((.44,.49,.54), .94, .32),
    'black_titanium': ((.035,.042,.055), .85, .24),
    'lacquer': ((.22,.025,.055), .25, .16),
    'glass': ((.44,.65,.72), .0, .1),
    'emissive': ((.64,.36,.11), .45, .24),
}


def ring_mesh(width, height, border, profile=FRAME_PROFILE):
    """Continuous mitered swept profile, four vertices per section station."""
    vertices=[]
    for offset, depth in profile:
        x=width/2+offset*border; y=height/2+offset*border
        vertices.extend([(-x,-y,depth*border),(x,-y,depth*border),
                         (x,y,depth*border),(-x,y,depth*border)])
    faces=[]
    for j in range(len(profile)):
        for i in range(4):
            faces.append((j*4+i,j*4+(i+1)%4,((j+1)%len(profile))*4+(i+1)%4,((j+1)%len(profile))*4+i))
    return vertices,[tuple(reversed(face)) for face in faces]


def artwork_size(width,height,aspect,layout):
    if layout=='fill': return width,height
    return (height*aspect,height) if width/height>aspect else (width,width/aspect)


def build_exhibition(config, poster, composition, textured_material):
    import bpy
    from mathutils import Vector, Matrix
    from pathlib import Path
    f=config['frame']; c=composition
    origin=Vector(c['center']); right=Vector(c['right']); up=Vector(c['up']); normal=Vector(c['normal'])
    basis=Matrix((right,up,normal)).transposed()
    w,h=c['width'],c['height']; b=min(f['border_m'],min(w,h)*.12)
    portal_depth=f.get('portal_depth_m',3); template=f.get('template','cinema')
    if template=='deep': template='cinema'
    root=bpy.data.objects.new('Exhibition · animated assembly',None); bpy.context.collection.objects.link(root)
    objs=[]; rings=[]
    def point(p): return origin+right*p[0]+up*p[1]+normal*p[2]
    def pbr(name,color,metal=.0,rough=.4,emission=0,glass=False):
        mat=bpy.data.materials.new(name); mat.use_nodes=True
        node=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        node.inputs['Base Color'].default_value=(*color,1); node.inputs['Metallic'].default_value=metal
        node.inputs['Roughness'].default_value=rough
        if emission:
            node.inputs['Emission'].default_value=(*color,1); node.inputs['Emission Strength'].default_value=emission
        if glass:
            node.inputs['Transmission'].default_value=.65; node.inputs['Alpha'].default_value=.25
            node.inputs['IOR'].default_value=1.46; mat.blend_method='BLEND'; mat.use_screen_refraction=True
            mat.show_transparent_back=False
        return mat
    rgb,metal,rough=PRESETS.get(f.get('material','gold'),PRESETS['gold'])
    # Color is a real base-color control; presets retain physically distinct roughness/metalness.
    hexcolor=f.get('color','#b8945c').lstrip('#')
    if f.get('material','gold') in ('gold','lacquer','emissive'):
        rgb=tuple((int(hexcolor[i:i+2],16)/255)**2.2 for i in (0,2,4))
    gold=pbr('Satin champagne · machined metal',rgb,metal,rough,emission=.65 if f.get('material')=='emissive' else 0,glass=f.get('material')=='glass')
    trim=pbr('Polished champagne fillet',(.55,.34,.105),.92,.19)
    dark=pbr('Velvet aubergine architecture',(.065,.025,.105),.15,.42)
    black=pbr('Blackened metal reveal',(.008,.007,.013),.55,.31)
    floor=pbr('Smoked stone stage',(.065,.035,.085),.35,.3)
    warm=pbr('Warm linear diffuser',(1,.57,.2),.0,.4,emission=2.5)
    glass=pbr('Museum optical glass',(.34,.48,.52),0,.1,glass=True)
    def mesh(name,vertices,faces,mat):
        data=bpy.data.meshes.new(name); data.from_pydata([point(v) for v in vertices],[],faces); data.update(); data.use_auto_smooth=True
        ob=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(ob); data.materials.append(mat)
        ob.parent=root; objs.append(ob); return ob
    def box(name,p,size,mat,bevel=.025):
        bpy.ops.mesh.primitive_cube_add(size=1,location=point(p)); ob=bpy.context.object; ob.name=name
        ob.rotation_euler=basis.to_euler(); ob.dimensions=size
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); ob.data.materials.append(mat); ob.data.use_auto_smooth=True
        if bevel:
            mod=ob.modifiers.new('Soft manufactured arris','BEVEL'); mod.width=min(bevel,min(size)*.2); mod.segments=3
            ob.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
        ob.parent=root; objs.append(ob); return ob
    def ring(name,rw,rh,rb,z,mat,depth_scale=1):
        vv,ff=ring_mesh(rw,rh,rb); vv=[(x,y,z+zz*depth_scale) for x,y,zz in vv]
        ob=mesh(name,vv,ff,mat)
        mod=ob.modifiers.new('Micro bevel highlights','BEVEL'); mod.width=rb*.025; mod.segments=2
        ob.modifiers.new('Machined normals','WEIGHTED_NORMAL'); rings.append(ob)
        return ob
    # Deep, continuous profiles with independent black reveal and polished inner fillet.
    ring('Hero frame · swept 13-step miter profile',w,h,b,.03,gold,depth_scale=f.get('depth_m',.65)/(b*.84))
    ring('Inner polished fillet',w*.998,h*.998,b*.12,.08,trim)
    ring('Recessed black shadow reveal',w+2*b,h+2*b,b*.44,-b*.4,black)
    # Artwork stays face-on. fit uses full original UV; fill uses composition crop, never stretch.
    source_image=bpy.data.images.load(str(poster),check_existing=True)
    iw,ih=artwork_size(w,h,source_image.size[0]/source_image.size[1],c.get('layout','auto_fit'))
    if c.get('layout')=='manual': box('Artwork black containment matte',(0,0,-.015),(w,h,.02),black,.002)
    poster_ob=mesh('Original poster · original aspect', [(-iw/2,-ih/2,0),(iw/2,-ih/2,0),(iw/2,ih/2,0),(-iw/2,ih/2,0)],[(0,1,2,3)],textured_material(poster,'Original artwork · untouched'))
    poster_ob.data.uv_layers.new(); u0,v0,u1,v1=c.get('uv_crop',[0,0,1,1])
    for loop,uv in zip(poster_ob.data.uv_layers.active.data,[(u0,v0),(u1,v0),(u1,v1),(u0,v1)]): loop.uv=uv
    hero_origin=origin.copy(); hero_size=(w,h)
    w,h=c.get('stage_width',w),c.get('stage_height',h)
    origin=Vector(c.get('stage_center',list(origin+normal*f.get('virtual_depth_m',0))))
    if template=='cinema':
        # A real recessed theatre: side walls, soffit and floor bridge nested portal mouths.
        front=.75; back=-portal_depth; ow=w*1.16; oh=h*1.65
        for side in (-1,1):
            box('Portal side wall', (side*ow/2,0,(front+back)/2),(.15,oh,front-back),dark)
        box('Portal ceiling',(0,oh/2,(front+back)/2),(ow,.15,front-back),dark)
        box('Portal stage floor',(0,-oh/2,(front+back)/2),(ow,.16,front-back),floor)
        box('Aubergine back wall',(0,0,back-.08),(ow,oh,.15),dark)
        for i,z in enumerate((.72,-1.35)):
            ring('Architectural portal %02d'%i,ow*.96,oh*.96,b*.72,z,black)
            ring('Champagne portal edge %02d'%i,ow*.96,oh*.96,b*.075,z+.025,trim)
        box('Low exhibition plinth',(0,-h*.70,-.1),(w*1.04,h*.25,1.1),floor)
        box('Plinth champagne nose',(0,-h*.577,.47),(w*1.04,.025,.04),trim,.005)
        # Warm floor rails lead into depth; no lights cross the artwork text.
        for side in (-1,1):
            box('Stage guide light',(side*w*.53,-oh/2+.095,(front+back)/2),(.018,.016,front-back),warm,.002)
            box('Foreground threshold block',(side*w*.54,-h*.73,.9),(w*.15,h*.08,.34),black)
            box('Threshold luminaire',(side*w*.54,-h*.73+.05,.99),(w*.09,.018,.12),trim,.008)
    elif template=='float':
        # Gallery suspension plus forward plinth and luminous halo, distinct silhouette.
        ring('Floating halo',w*1.14,h*1.20,b*.055,-.25,warm)
        box('Floating backing',(0,0,-.3),(w+2*b,h+2*b,.12),black)
        for side in (-1,1):
            box('Suspension cable',(side*w*.38,h*.88,-.1),(.012,h*.7,.012),trim,.002)
        box('Forward floating plinth',(0,-h*.79,.28),(w*1.12,h*.16,.9),floor)
        box('Plinth inlaid light',(0,-h*.70,.75),(w*.94,.018,.012),warm,.002)
        box('Gallery background',(0,0,-portal_depth),(w*2,h*2.5,.15),dark)
        box('Gallery floor',(0,-h*.9,-portal_depth*.35),(w*2,.12,portal_depth*1.5),floor)
    else:
        bpy.context.scene.eevee.use_ssr=True; bpy.context.scene.eevee.use_ssr_refraction=True
        # Glazing is limited to side wings and canopy, keeping poster lettering unobstructed.
        box('Museum podium',(0,-h*.72,.16),(w*1.22,h*.24,.85),floor)
        for side in (-1,1):
            box('Showcase bronze post',(side*w*.54,0,.02),(.045,h*1.33,.045),trim,.008)
            box('Showcase side glazing',(side*w*.545,0,-.08),(.022,h*1.32,.68),glass,.003)
        box('Showcase canopy',(0,h*.63,-.08),(w*1.25,.025,.68),glass,.004)
        ring('Showcase upper/lower frame',w*1.08,h*1.26,b*.14,.06,trim)
        box('Museum background',(0,0,-portal_depth),(w*2,h*2.5,.15),dark)
        box('Museum floor',(0,-h*.9,-.7),(w*2,.12,portal_depth*2),floor)
    origin=hero_origin; w,h=hero_size
    if f.get('edge_light',True):
        # Small inset line, below outer molding and clear of source artwork.
        ring('Inset warm edge diffuser',w+b*1.15,h+b*1.15,b*.025,.04,warm)
    def light(name,pos,power,size,color,target=(0,0,0)):
        bpy.ops.object.light_add(type='AREA',location=point(pos)); ob=bpy.context.object; ob.name=name
        ob.data.energy=power; ob.data.shape='DISK'; ob.data.size=size; ob.data.color=color
        ob.rotation_euler=(point(target)-ob.location).to_track_quat('-Z','Y').to_euler()
        ob.data.use_shadow=True; ob.data.use_contact_shadow=True
        return ob
    key=light('Warm softbox · key',(-w*.48,h*.82,2.6),1100,max(2,w*.6),(1,.77,.47))
    light('Cool violet rim',(w*.7,h*.35,-.45),1100,max(1,h*.5),(.48,.35,1))
    light('Stage floor soft wash',(0,-h*.15,2.4),950,max(1,w*.45),(.68,.48,1),(0,-h*.78,-1.4))
    light('Right wall violet bounce',(w*.25,0,1.5),650,max(1,h*.6),(.62,.37,1),(w*.62,0,-1.5))
    light('Top gallery wash',(0,h*.8,1.1),900,max(1,w*.45),(1,.87,.65),(0,-h*.4,-.7))
    bpy.context.scene.eevee.use_gtao=True; bpy.context.scene.eevee.gtao_distance=3; bpy.context.scene.eevee.gtao_factor=1.35
    bpy.context.scene.eevee.use_soft_shadows=True
    for ob in objs:
        if not ob.name.startswith(('Hero frame','Inner polished','Recessed black','Original poster','Artwork black','Inset warm','Floating halo','Floating backing')):
            ob.parent=None
    image=bpy.data.images.load(str(poster),check_existing=True)
    return {'root':root,'objects':objs,'poster_object':poster_ob,'key_light':key,
        'report':{'poster_original_pixels':list(image.size),'poster_display_metres':[iw,ih],
        'poster_aspect_preserved':c.get('layout')!='fill','source_aspect':image.size[0]/image.size[1],
        'display_aspect':iw/ih,'uv_crop':c.get('uv_crop',[0,0,1,1]),'effective_frame_position':list(origin),
        'template':template,'material':f.get('material','gold'),'continuous_ring_count':len(rings),
        'profile_stations':len(FRAME_PROFILE),'profile_faces':len(FRAME_PROFILE)*4,
        'mesh_count':len(objs),'composition':c}}
