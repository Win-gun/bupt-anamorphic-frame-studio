"""An opening cut into a solid facade, with a real five-sided recessed room.

Geometry planning is NumPy-only so opening safety, depth and original-image
aspect can be verified without Blender. Local +Z faces the design camera.
"""
import copy
import numpy as np
from studio.composition import solve_composition, project_points, camera_basis


def architecture_plan(config, poster_size):
    cfg = copy.deepcopy(config)
    cube = cfg.get("cube", {})
    cfg["frame"].update(
        template="aurora_float",
        layout="fill",
        width_m=1.5,
        height_m=1,
        scale=cube.get("opening_scale", 0.94),
    )
    opening = solve_composition(cfg, poster_size)
    w, h = opening["width"], opening["height"]
    depth = cube.get("depth_m", 3.0)
    wall = cube.get("wall_thickness_m", 0.32)
    layout = cube.get("layout", "floating")
    if layout not in ("floating", "back_wall"):
        raise ValueError("Unknown embedded cube layout: " + layout)
    poster_z = (
        -depth + 0.055
        if layout == "back_wall"
        else -depth * cube.get("poster_depth_fraction", 0.62)
    )
    ratio = poster_size[0] / poster_size[1]
    scale = min(
        0.9, cube.get("poster_scale", 0.82) * config["frame"].get("scale", 0.86) / 0.86
    )
    # Physical fitting inside room, with full original image and a generous gap.
    iw, ih = min(w * scale, h * scale * ratio), min(h * scale, w * scale / ratio)
    # Preserve physical dimensions/position in manual mode, while fitting inside
    # the architectural room and preserving source ratio.
    if config["frame"].get("layout") == "manual":
        requested_w = config["frame"]["width_m"]
        requested_h = config["frame"]["height_m"]
        fit = min(1.0, requested_w / iw, requested_h / ih)
        iw, ih = iw * fit, ih * fit
    center = np.array(opening["center"]) + np.array(opening["normal"]) * poster_z
    c = copy.deepcopy(opening)
    c.update(
        layout=config["frame"].get("layout", "auto_fit"),
        center=center.tolist(),
        width=iw,
        height=ih,
        width_m=iw,
        height_m=ih,
        depth=opening["depth"] - poster_z,
        uv_crop=[0.0, 0.0, 1.0, 1.0],
    )
    ndc, _ = project_points(center, config)
    _, _, _, _, tx, ty = camera_basis(config)
    half = np.array([iw / tx, ih / ty]) / c["depth"] / 2
    c["opening_ndc"] = np.r_[ndc - half, ndc + half].tolist()
    c["metrics"]["projected_width_fraction"] = float(
        2 * half[0] / (c["screen_bbox_ndc"][2] - c["screen_bbox_ndc"][0])
    )
    # Since all original poster corners are contained in the safe front opening,
    # the poster is also safe under this same ray projection.
    box = np.array(c["opening_ndc"])
    obox = np.array(opening["opening_ndc"])
    c["metrics"]["opening_safe"] = bool(
        opening["metrics"]["opening_safe"]
        and np.all(box[:2] >= obox[:2])
        and np.all(box[2:] <= obox[2:])
    )
    return dict(
        opening=opening,
        composition=c,
        width=w,
        height=h,
        depth=depth,
        wall_thickness=wall,
        poster_z=poster_z,
        poster_width=iw,
        poster_height=ih,
        layout=layout,
    )


def facade_mesh(width, height, margin, wall):
    """One closed connected solid annulus: front, rear, throat and outside.

    This is the actual remaining facade around a rectangular excavation, with
    shared corner indices and physical cut thickness, rather than four bars.
    """
    inner = [
        (-width / 2, -height / 2),
        (width / 2, -height / 2),
        (width / 2, height / 2),
        (-width / 2, height / 2),
    ]
    outer = [
        (-width / 2 - margin, -height / 2 - margin),
        (width / 2 + margin, -height / 2 - margin),
        (width / 2 + margin, height / 2 + margin),
        (-width / 2 - margin, height / 2 + margin),
    ]
    vertices = [
        (x, y, z) for z in (0.0, -wall) for loop in (outer, inner) for x, y in loop
    ]
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces.extend(
            [
                (i, j, 4 + j, 4 + i),
                (8 + i, 12 + i, 12 + j, 8 + j),
                (4 + i, 4 + j, 12 + j, 12 + i),
                (i, 8 + i, 8 + j, j),
            ]
        )
    return vertices, faces


def build_exhibition(config, poster, composition, textured_material):
    import bpy
    from mathutils import Vector

    image = bpy.data.images.load(str(poster), check_existing=True)
    plan = architecture_plan(config, tuple(image.size))
    c = plan["composition"]
    room = plan["opening"]
    w, h, d = plan["width"], plan["height"], plan["depth"]
    t = plan["wall_thickness"]
    cube = config.get("cube", {})
    origin = Vector(room["center"])
    right = Vector(room["right"])
    up = Vector(room["up"])
    normal = Vector(room["normal"])
    objects = []
    root = bpy.data.objects.new("Embedded Cube · poster assembly", None)
    bpy.context.collection.objects.link(root)
    root["composition_json"] = __import__("json").dumps(c)
    root["template"] = "embedded_cube_architecture"

    def point(p):
        return origin + right * p[0] + up * p[1] + normal * p[2]

    def mat(name, color, rough=0.9):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        shader = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        shader.inputs["Base Color"].default_value = (*color, 1)
        shader.inputs["Roughness"].default_value = rough
        shader.inputs["Specular"].default_value = 0.14
        return m

    facade = mat("Mineral facade · cool pale stone", (0.49, 0.51, 0.55))
    cut = mat("Fresh mineral cut · physical wall thickness", (0.30, 0.33, 0.39))
    left = mat("Room left · pale desaturated lavender", (0.43, 0.39, 0.49))
    right_mat = mat("Room right · pale grey blue", (0.34, 0.43, 0.52))
    top = mat("Room ceiling · quiet mist", (0.49, 0.52, 0.58))
    bottom = mat("Room floor · mineral grey", (0.40, 0.44, 0.49))
    back = mat("Room rear · warm grey", (0.50, 0.48, 0.47))

    def mesh(name, verts, faces, material, moving=False):
        data = bpy.data.meshes.new(name)
        data.from_pydata([point(v) for v in verts], [], faces)
        data.update()
        data.use_auto_smooth = True
        ob = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(ob)
        data.materials.append(material)
        if moving:
            ob.parent = root
        objects.append(ob)
        return ob

    def box(name, lo, hi, material, moving=False, bevel=0):
        x, y, z = lo
        X, Y, Z = hi
        ob = mesh(
            name,
            [
                (x, y, z),
                (X, y, z),
                (X, Y, z),
                (x, Y, z),
                (x, y, Z),
                (X, y, Z),
                (X, Y, Z),
                (x, Y, Z),
            ],
            [
                (3, 2, 1, 0),
                (4, 5, 6, 7),
                (0, 1, 5, 4),
                (1, 2, 6, 5),
                (2, 3, 7, 6),
                (3, 0, 4, 7),
            ],
            material,
            moving,
        )
        if bevel:
            mod = ob.modifiers.new("Small architectural edge bevel", "BEVEL")
            mod.width = bevel
            mod.segments = 3
            ob.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
        return ob

    # Facade is larger than the entire LED frustum: never a free-standing box.
    _, _, _, _, tx, ty = camera_basis(config)
    ndc_mid = (
        np.array(room["opening_ndc"][:2]) + np.array(room["opening_ndc"][2:])
    ) / 2
    # Cover the complete design-camera frustum with a further exterior margin.
    margin = max(
        room["depth"] * tx * (1 + abs(ndc_mid[0])) - w / 2,
        room["depth"] * ty * (1 + abs(ndc_mid[1])) - h / 2,
        0,
    ) + cube.get("facade_margin_m", 1.2)
    verts, faces = facade_mesh(w, h, margin, t)
    surround = mesh(
        "Building facade · continuous solid wall with excavated opening",
        verts,
        faces,
        facade,
    )
    surround.data.materials.append(cut)
    for i, p in enumerate(surround.data.polygons):
        p.material_index = 1 if i % 4 == 2 else 0
    bevel = surround.modifiers.new("Mineral opening chamfer · 20 mm", "BEVEL")
    bevel.width = 0.02
    bevel.segments = 3
    # Five actual volumetric walls. The inner surfaces are x=±w/2,
    # y=±h/2 and z=-depth, continuously joined to the facade throat.
    box(
        "Excavated room · LEFT wall",
        (-w / 2 - t, -h / 2 - t, -d - t),
        (-w / 2, h / 2 + t, -t),
        left,
    )
    box(
        "Excavated room · RIGHT wall",
        (w / 2, -h / 2 - t, -d - t),
        (w / 2 + t, h / 2 + t, -t),
        right_mat,
    )
    box(
        "Excavated room · CEILING", (-w / 2, h / 2, -d - t), (w / 2, h / 2 + t, -t), top
    )
    box(
        "Excavated room · FLOOR",
        (-w / 2, -h / 2 - t, -d - t),
        (w / 2, -h / 2, -t),
        bottom,
    )
    rear = box(
        "Excavated room · REAR wall", (-w / 2, -h / 2, -d - t), (w / 2, h / 2, -d), back
    )
    # A soft spatial colour drift on the wall is independent of the artwork.
    nodes = back.node_tree.nodes
    links = back.node_tree.links
    tex = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    ramp = nodes.new("ShaderNodeValToRGB")
    links.new(tex.outputs["Generated"], sep.inputs[0])
    links.new(sep.outputs["Y"], ramp.inputs[0])
    ramp.color_ramp.elements[0].color = (0.39, 0.43, 0.49, 1)
    ramp.color_ramp.elements[1].color = (0.57, 0.52, 0.49, 1)
    links.new(
        ramp.outputs[0],
        next(n for n in nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"],
    )
    iw, ih, z = plan["poster_width"], plan["poster_height"], plan["poster_z"]
    backing = mat("Poster thin neutral backing", (0.65, 0.65, 0.66), 0.8)
    box(
        "Poster backing · 25 mm",
        (-iw / 2 - 0.008, -ih / 2 - 0.008, z - 0.025),
        (iw / 2 + 0.008, ih / 2 + 0.008, z - 0.001),
        backing,
        True,
        0.002,
    )
    artwork = mesh(
        "Original poster · complete unmodified rectangle",
        [
            (-iw / 2, -ih / 2, z),
            (iw / 2, -ih / 2, z),
            (iw / 2, ih / 2, z),
            (-iw / 2, ih / 2, z),
        ],
        [(0, 1, 2, 3)],
        textured_material(poster, "Original poster · untouched full UV"),
        True,
    )
    artwork.data.uv_layers.new()
    for loop, uv in zip(
        artwork.data.uv_layers.active.data, [(0, 0), (1, 0), (1, 1), (0, 1)]
    ):
        loop.uv = uv

    def light(name, position, target, power, size, color):
        data = bpy.data.lights.new(name, "AREA")
        ob = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(ob)
        ob.location = point(position)
        ob.rotation_euler = (
            (point(target) - ob.location).to_track_quat("-Z", "Y").to_euler()
        )
        lighting = config.get("lighting", {})
        data.energy = power * lighting.get("intensity", 1)
        data.shape = "DISK"
        data.size = (
            size
            * (
                0.6
                + 0.5 * lighting.get("softness", 0.8)
                + 0.2 * lighting.get("shadow_softness", 0.8)
            )
            / 1.16
        )
        data.color = color
        data.use_shadow = True
        return ob

    key = light(
        "Room ceiling · soft recessed wash",
        (0, h * 0.28, -d * 0.25),
        (0, 0, -d),
        200,
        max(0.6, h * 0.3),
        (1, 0.94, 0.88),
    )
    side = light(
        "Room left · broad blue bounce",
        (-w * 0.30, 0, -d * 0.32),
        (w * 0.15, 0, -d * 0.75),
        100,
        max(0.6, h * 0.35),
        (0.79, 0.87, 1),
    )
    floor = light(
        "Room floor · subtle reflected light",
        (0, -h * 0.29, -d * 0.24),
        (0, h * 0.2, -d * 0.8),
        60,
        max(0.6, h * 0.3),
        (0.92, 0.92, 1),
    )
    facade_light = light(
        "Building facade · broad daylight",
        (-w * 0.4, h * 0.65, 7),
        (-w * 0.4, h * 0.65, 0),
        850 * (0.5 + config.get("lighting", {}).get("ambient", 0.5)),
        max(w, h) * 1.7,
        (0.95, 0.97, 1),
    )
    scene = bpy.context.scene
    scene.eevee.use_gtao = True
    scene.eevee.gtao_distance = 0.7
    scene.eevee.gtao_factor = 1.15
    scene.eevee.use_soft_shadows = True
    world = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    world.inputs["Color"].default_value = (0.60, 0.63, 0.70, 1)
    world.inputs["Strength"].default_value = (
        0.28 * config.get("lighting", {}).get("ambient", 0.5) / 0.5
    )
    report = dict(
        template="embedded_cube_architecture",
        material="excavated_mineral_architecture",
        poster_original_pixels=list(image.size),
        poster_display_metres=[iw, ih],
        poster_aspect_preserved=True,
        source_aspect=image.size[0] / image.size[1],
        display_aspect=iw / ih,
        uv_crop=[0, 0, 1, 1],
        effective_frame_position=c["center"],
        composition=c,
        continuous_ring_count=0,
        profile_stations=0,
        profile_faces=0,
        mesh_count=len(objects),
        human_visual_judgment="PENDING",
    )
    report["architectural_geometry"] = dict(
        style="building_facade_excavated_room",
        layout=plan["layout"],
        opening_width_m=w,
        opening_height_m=h,
        opening_ndc=room["opening_ndc"],
        opening_safe=room["metrics"]["opening_safe"],
        wall_thickness_m=t,
        cavity_depth_m=d,
        poster_distance_from_front_m=-z,
        poster_gap_to_rear_wall_m=d + z,
        solid_interior_walls=5,
        excavated_reveals=4,
        continuous_facade=True,
        facade_margin_m=margin,
        opening_chamfer_m=0.02,
        front_plane_center=room["center"],
        interior_faces=["left", "right", "ceiling", "floor", "rear"],
    )
    report["lighting"] = dict(
        ceiling_wash_w=key.data.energy,
        side_bounce_w=side.data.energy,
        floor_bounce_w=floor.data.energy,
        facade_daylight_w=facade_light.data.energy,
        ambient_strength=world.inputs["Strength"].default_value,
        controls=config.get("lighting", {}),
    )
    return dict(
        root=root, objects=objects, poster_object=artwork, key_light=key, report=report
    )
