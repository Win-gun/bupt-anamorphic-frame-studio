"""Minimal architectural image display; original image and procedural backdrop are separate."""
import math


def palette_colors(name):
    import json
    from pathlib import Path

    canonical = json.loads(
        (
            Path(__file__).resolve().parent.parent / "configs" / "bupt-curved-led.json"
        ).read_text()
    )
    return canonical["palettes"][name]["colors"]


def linear_rgb(value):
    values = [int(value.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(
        v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values
    )


def rounded_panel_mesh(width, height, thickness, radius, segments=12):
    """Closed rounded slab, camera face +Z. Artwork is a separate full rectangle."""
    radius = min(radius, width / 2, height / 2)
    outline = []
    for cx, cy, start in (
        (width / 2 - radius, height / 2 - radius, 0),
        (-width / 2 + radius, height / 2 - radius, 90),
        (-width / 2 + radius, -height / 2 + radius, 180),
        (width / 2 - radius, -height / 2 + radius, 270),
    ):
        for i in range(segments + 1):
            a = math.radians(start + i * 90 / segments)
            outline.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    n = len(outline)
    vertices = [(x, y, z) for z in (-thickness, 0) for x, y in outline]
    faces = [tuple(reversed(range(n))), tuple(range(n, n * 2))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return vertices, faces


def build_exhibition(config, poster, composition, textured_material):
    import bpy
    from mathutils import Vector, Matrix

    c = composition
    a = config.get("appearance", {})
    p = config.get("panel", {})
    lighting = config.get("lighting", {})
    template = config["frame"].get("template", "aurora_float")
    origin = Vector(c["center"])
    right = Vector(c["right"])
    up = Vector(c["up"])
    normal = Vector(c["normal"])
    basis = Matrix((right, up, normal)).transposed()
    w, h = c["width"], c["height"]
    thickness = p.get("thickness_m", 0.035)
    radius = p.get("corner_radius_m", 0.035)
    distance = p.get("float_distance_m", 0.85)
    objects = []
    root = bpy.data.objects.new("Aurora · floating artwork assembly", None)
    bpy.context.collection.objects.link(root)
    root["template"] = template
    root["composition_json"] = __import__("json").dumps(c)

    def point(v):
        return origin + right * v[0] + up * v[1] + normal * v[2]

    def mesh(name, vertices, faces, mat, moving=False):
        data = bpy.data.meshes.new(name)
        data.from_pydata([point(v) for v in vertices], [], faces)
        data.update()
        data.use_auto_smooth = True
        ob = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(ob)
        data.materials.append(mat)
        if moving:
            ob.parent = root
        objects.append(ob)
        return ob

    def pbr(name, color, rough=0.8, metal=0):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        shader = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        shader.inputs["Base Color"].default_value = (*color, 1)
        shader.inputs["Roughness"].default_value = rough
        shader.inputs["Metallic"].default_value = metal
        return mat

    # Tiny guard band makes rounded backing possible without masking any original corner pixels.
    guard = max(0.002, radius * 0.32)
    body = pbr("Porcelain thin panel edge", linear_rgb("#DAD9DE"), 0.48, 0)
    next(n for n in body.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs[
        "Specular"
    ].default_value = p.get("reflection", 0.025)
    vertices, faces = rounded_panel_mesh(
        w + 2 * guard, h + 2 * guard, thickness, radius
    )
    slab = mesh("Thin rounded panel · physical thickness", vertices, faces, body, True)
    bevel = slab.modifiers.new("Subtle edge chamfer", "BEVEL")
    bevel.width = min(thickness * 0.12, 0.0025)
    bevel.segments = 3
    slab.modifiers.new("Panel weighted normals", "WEIGHTED_NORMAL")
    image = bpy.data.images.load(str(poster), check_existing=True)
    aspect = image.size[0] / image.size[1]
    iw, ih = (
        ((h * aspect, h) if w / h > aspect else (w, w / aspect))
        if c.get("layout") == "manual"
        else (w, h)
    )
    poster_ob = mesh(
        "Original poster · all original rectangular pixels",
        [
            (-iw / 2, -ih / 2, 0.0005),
            (iw / 2, -ih / 2, 0.0005),
            (iw / 2, ih / 2, 0.0005),
            (-iw / 2, ih / 2, 0.0005),
        ],
        [(0, 1, 2, 3)],
        textured_material(poster, "Original artwork · untouched"),
        True,
    )
    poster_ob.data.uv_layers.new()
    u0, v0, u1, v1 = c.get("uv_crop", [0, 0, 1, 1])
    for loop, uv in zip(
        poster_ob.data.uv_layers.active.data, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    ):
        loop.uv = uv
    # A broad genuine curved surface, parameterized in local architectural metres.
    span = max(w, h) * 2.5
    back_z = -distance - thickness
    vertices = []
    faces = []
    n = 256 if template == "soft_depth" else 48
    for iy in range(n + 1):
        y = (iy / n * 2 - 1) * span
        for ix in range(n + 1):
            x = (ix / n * 2 - 1) * span
            z = back_z + 0.20 * (x / span) ** 2 + 0.30 * (y / span) ** 2
            if template == "soft_depth":
                # A single continuous superellipse recess; no freestanding thick frame.
                r = ((abs(x) / (w * 0.60)) ** 8 + (abs(y) / (h * 0.69)) ** 8) ** 0.125
                t = max(0, min(1, (r - 0.85) / 0.28))
                t = t * t * (3 - 2 * t)
                z += min(0.65, distance * 0.7) * t
            vertices.append((x, y, z))
    for iy in range(n):
        for ix in range(n):
            j = iy * (n + 1) + ix
            faces.append((j, j + 1, j + n + 2, j + n + 1))
    backdrop_mat = pbr("Aurora · procedural architectural gradient", (0.5, 0.5, 0.5))
    nodes = backdrop_mat.node_tree.nodes
    links = backdrop_mat.node_tree.links
    shader = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Roughness"].default_value = 0.94
    tex = nodes.new("ShaderNodeTexCoord")
    tex.name = "Backdrop generated coordinates"
    separate = nodes.new("ShaderNodeSeparateXYZ")
    links.new(tex.outputs["Generated"], separate.inputs[0])
    angle = math.radians(a.get("direction_deg", 25))

    def mathnode(operation, *values):
        node = nodes.new("ShaderNodeMath")
        node.operation = operation
        for i, value in enumerate(values):
            if isinstance(value, (float, int)):
                node.inputs[i].default_value = value
            else:
                links.new(value, node.inputs[i])
        return node.outputs[0]

    # Expanded central coverage: gradient spans the visible composition, not the oversized mesh bounds.
    x = mathnode("MULTIPLY", mathnode("SUBTRACT", separate.outputs["X"], 0.5), 3.0)
    y = mathnode("MULTIPLY", mathnode("SUBTRACT", separate.outputs["Y"], 0.5), 3.0)
    mode = a.get("gradient_type", "dual")
    if mode == "radial":
        factor = mathnode(
            "SQRT",
            mathnode("ADD", mathnode("MULTIPLY", x, x), mathnode("MULTIPLY", y, y)),
        )
    else:
        factor = mathnode(
            "ADD",
            0.5,
            mathnode(
                "ADD",
                mathnode("MULTIPLY", x, math.cos(angle)),
                mathnode("MULTIPLY", y, math.sin(angle)),
            ),
        )
        if mode in ("dual", "multi"):
            wave = mathnode(
                "SINE",
                mathnode(
                    "ADD", mathnode("MULTIPLY", x, 2.4), mathnode("MULTIPLY", y, -2.1)
                ),
            )
            factor = mathnode(
                "ADD",
                factor,
                mathnode("MULTIPLY", wave, 0.16 if mode == "dual" else 0.3),
            )
    transition = a.get("transition", 0.5)
    factor = mathnode(
        "ADD",
        0.5,
        mathnode("MULTIPLY", mathnode("SUBTRACT", factor, 0.5), 1.6 - transition),
    )
    noise = nodes.new("ShaderNodeTexNoise")
    noise.name = "Background only · fine dither"
    noise.inputs["Scale"].default_value = 650
    links.new(tex.outputs["Generated"], noise.inputs["Vector"])
    factor = mathnode(
        "ADD",
        factor,
        mathnode(
            "MULTIPLY",
            mathnode("SUBTRACT", noise.outputs["Fac"], 0.5),
            a.get("noise_strength", 0.006),
        ),
    )
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.name = "Aurora palette · user colors and stops"
    ramp.color_ramp.interpolation = "B_SPLINE"
    colors = a.get("colors", palette_colors(a.get("palette", "aurora")))
    stops = a.get("stops", [i / (len(colors) - 1) for i in range(len(colors))])
    for element in list(ramp.color_ramp.elements)[2:]:
        ramp.color_ramp.elements.remove(element)
    for i, (color, stop) in enumerate(zip(colors, stops)):
        element = (
            ramp.color_ramp.elements[i] if i < 2 else ramp.color_ramp.elements.new(stop)
        )
        element.position = stop
        element.color = (*linear_rgb(color), 1)
    links.new(factor, ramp.inputs["Fac"])
    hue = nodes.new("ShaderNodeHueSaturation")
    hue.name = "Background only · saturation brightness"
    hue.inputs["Saturation"].default_value = a.get("saturation", 0.72)
    hue.inputs["Value"].default_value = a.get("brightness", 1)
    links.new(ramp.outputs["Color"], hue.inputs["Color"])
    links.new(hue.outputs["Color"], shader.inputs["Base Color"])
    links.new(hue.outputs["Color"], shader.inputs["Emission"])
    shader.inputs["Emission Strength"].default_value = lighting.get("glow", 0.025)
    backdrop = mesh("Continuous curved Aurora backdrop", vertices, faces, backdrop_mat)
    backdrop.data.auto_smooth_angle = math.pi
    for polygon in backdrop.data.polygons:
        polygon.use_smooth = True
    if template == "glass_layers":
        for index, (ox, oy, z, tint) in enumerate(
            (
                (-w * 0.055, h * 0.055, -distance * 0.35, "#B9BFCE"),
                (w * 0.055, -h * 0.05, -distance * 0.68, "#D6C6CE"),
            )
        ):
            mat = pbr("Frosted architectural layer %d" % index, linear_rgb(tint), 0.42)
            shader = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            shader.inputs["Transmission"].default_value = 0.22
            shader.inputs["IOR"].default_value = 1.44
            shader.inputs["Alpha"].default_value = 0.62
            mat.blend_method = "BLEND"
            mat.use_screen_refraction = True
            vv, ff = rounded_panel_mesh(w * 1.08, h * 1.14, 0.018, 0.10)
            pane = mesh(
                "Frosted layer %d · behind original" % (index + 1),
                [(x + ox, y + oy, zz + z) for x, y, zz in vv],
                ff,
                mat,
            )
            modifier = pane.modifiers.new("Glass edge radius", "BEVEL")
            modifier.width = 0.004
            modifier.segments = 3
        scene = bpy.context.scene
        scene.eevee.use_ssr = True
        scene.eevee.use_ssr_refraction = True
    elif template == "embedded_cube":
        # Four real solid architectural reveals around an excavated volume.
        wall = pbr("Excavated pale lavender mineral", linear_rgb("#B6B4C1"), 0.88)
        halfw = w * 0.65
        halfh = h * 0.74
        front = min(1.3, distance * 1.5)
        back = back_z + 0.02

        def solid(name, center, size):
            x, y, z = center
            sx, sy, sz = (v / 2 for v in size)
            vv = [
                (x + dx * sx, y + dy * sy, z + dz * sz)
                for dz in (-1, 1)
                for dy in (-1, 1)
                for dx in (-1, 1)
            ]
            ff = [
                (0, 2, 3, 1),
                (4, 5, 7, 6),
                (0, 1, 5, 4),
                (2, 6, 7, 3),
                (0, 4, 6, 2),
                (1, 3, 7, 5),
            ]
            ob = mesh(name, vv, ff, wall)
            bevel = ob.modifiers.new("Soft architectural arris", "BEVEL")
            bevel.width = 0.035
            bevel.segments = 4
            ob.modifiers.new("Architectural weighted normals", "WEIGHTED_NORMAL")

        for side in (-1, 1):
            solid(
                "Excavated volume · side wall",
                (side * halfw, 0, (front + back) / 2),
                (0.12, halfh * 2, front - back),
            )
            solid(
                "Excavated volume · floor"
                if side < 0
                else "Excavated volume · ceiling",
                (0, side * halfh, (front + back) / 2),
                (halfw * 2, 0.12, front - back),
            )

    def light(name, position, energy, size, color):
        bpy.ops.object.light_add(type="AREA", location=point(position))
        ob = bpy.context.object
        ob.name = name
        ob.data.energy = energy * lighting.get("intensity", 1)
        ob.data.shape = "DISK"
        ob.data.size = size
        ob.data.color = color
        ob.rotation_euler = (
            (point((position[0], position[1], back_z)) - ob.location)
            .to_track_quat("-Z", "Y")
            .to_euler()
        )
        ob.data.use_shadow = True
        ob.data.use_contact_shadow = False
        return ob

    softness = lighting.get("softness", 0.8)
    shadow_soft = lighting.get("shadow_softness", 0.8)
    key = light(
        "Aurora · broad soft key",
        (-w * 0.30, h * 0.65, 8.0),
        1200,
        w * (0.25 + softness * 0.7 + shadow_soft * 0.3),
        (1, 0.94, 0.90),
    )
    fill = light(
        "Aurora · lavender diffuse fill",
        (w * 0.30, h * 0.15, 8.0),
        800 * (0.5 + lighting.get("ambient", 0.5)),
        w * (0.5 + softness),
        (0.86, 0.90, 1),
    )
    scene = bpy.context.scene
    scene.eevee.use_gtao = True
    scene.eevee.gtao_distance = min(0.35, distance * 0.45)
    scene.eevee.gtao_factor = 0.55
    scene.eevee.use_soft_shadows = True
    scene.eevee.shadow_cube_size = "2048"
    world = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    world.inputs["Color"].default_value = (0.65, 0.65, 0.68, 1)
    world.inputs["Strength"].default_value = lighting.get("ambient", 0.5)
    image = bpy.data.images.load(str(poster), check_existing=True)
    return {
        "root": root,
        "objects": objects,
        "poster_object": poster_ob,
        "key_light": key,
        "report": {
            "template": template,
            "material": "minimal_matte_panel",
            "poster_original_pixels": list(image.size),
            "poster_display_metres": [iw, ih],
            "poster_aspect_preserved": c.get("layout") != "fill",
            "source_aspect": image.size[0] / image.size[1],
            "display_aspect": iw / ih,
            "uv_crop": c.get("uv_crop", [0, 0, 1, 1]),
            "effective_frame_position": list(origin),
            "composition": c,
            "continuous_ring_count": 0,
            "profile_stations": 0,
            "profile_faces": 0,
            "mesh_count": len(objects),
            "panel": {
                "thickness_m": thickness,
                "corner_radius_m": radius,
                "float_distance_m": distance,
                "guard_band_m": guard,
                "full_rectangular_original": c.get("layout") != "fill",
                "reflection_target": "body_edge_specular",
            },
            "backdrop": {
                "curved_mesh": True,
                "vertices": len(vertices),
                "faces": len(faces),
                "center_depth_m": back_z,
                "procedural_nodes": len(nodes),
                "appearance": a,
                "glb_material": "procedural Blender shader; GLB uses neutral fallback",
            },
            "lighting": {
                "controls": lighting,
                "key_energy_w": key.data.energy,
                "key_size_m": key.data.size,
                "fill_energy_w": fill.data.energy,
                "ambient_strength": world.inputs["Strength"].default_value,
            },
            "architectural_geometry": {
                "style": template,
                "continuous_alcove": template == "soft_depth",
                "frosted_layers": 2 if template == "glass_layers" else 0,
                "excavated_reveals": 4 if template == "embedded_cube" else 0,
            },
            "human_visual_judgment": "PENDING",
        },
    }
