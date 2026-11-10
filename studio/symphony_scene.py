"""Bespoke autumn stage: curved mineral shell, folded satin ribbons and veined leaves.

Pure mesh functions remain importable outside Blender for geometric acceptance.
The original artwork is a separate emission quad with full rectangular UVs.
"""

import math
import numpy as np

from studio.aurora_scene import linear_rgb, rounded_panel_mesh
from studio.composition import project_points


def ribbon_mesh(path, width, twist=0.5, sections=8):
    """Swept open ribbon with a curved cross section; consistent camera-facing winding."""
    path = np.asarray(path, dtype=float)
    tangents = np.gradient(path, axis=0)
    side = np.stack([-tangents[:, 1], tangents[:, 0], np.zeros(len(path))], axis=1)
    side /= np.linalg.norm(side, axis=1)[:, None]
    verts = []
    for i, center in enumerate(path):
        t = i / (len(path) - 1)
        angle = twist * math.sin(t * math.pi * 2 + 0.3)
        cross = side[i] * math.cos(angle) + np.array([0, 0, math.sin(angle)])
        taper = 0.12 + 0.88 * math.sin(math.pi * t) ** 0.5
        for j in range(sections + 1):
            u = j / sections * 2 - 1
            verts.append(
                (
                    center
                    + cross * u * width * taper / 2
                    + np.array([0, 0, width * 0.15 * (1 - u * u)])
                ).tolist()
            )
    faces = []
    for i in range(len(path) - 1):
        for j in range(sections):
            k = i * (sections + 1) + j
            faces.append((k, k + sections + 1, k + sections + 2, k + 1))
    return verts, faces


def maple_leaf_mesh(size=1.0, curl=0.18):
    """Five deeply incised lobes with serrated margins and a raised central rib."""
    # Stem base clockwise around the botanical outline; tip points upwards.
    outline = [
        (0, -0.48),
        (-0.17, -0.25),
        (-0.43, -0.31),
        (-0.38, -0.13),
        (-0.70, 0.02),
        (-0.49, 0.12),
        (-0.66, 0.32),
        (-0.34, 0.30),
        (-0.38, 0.62),
        (-0.17, 0.47),
        (0, 0.95),
        (0.17, 0.47),
        (0.38, 0.62),
        (0.34, 0.30),
        (0.66, 0.32),
        (0.49, 0.12),
        (0.70, 0.02),
        (0.38, -0.13),
        (0.43, -0.31),
        (0.17, -0.25),
    ]
    # Multiple concentric rings make the surface genuinely curved rather than a planar fan.
    verts = [(0, 0, curl * size)]
    n = len(outline)
    for ring in range(1, 5):
        r = ring / 4
        for x, y in outline:
            z = curl * (1 - r * r) + 0.10 * r * r * math.sin(x * 7 + y * 4)
            verts.append((x * r * size, y * r * size, z * size))
    faces = [(0, 1 + (i + 1) % n, 1 + i) for i in range(n)]
    for ring in range(3):
        a = 1 + ring * n
        b = a + n
        for i in range(n):
            faces.append((a + i, a + (i + 1) % n, b + (i + 1) % n, b + i))
    return verts, faces


def projected_decoration_safe(vertices, config, composition, margin=0.018):
    """Conservative projected bounding box test, including actual front depth."""
    v = np.asarray(vertices)
    world = (
        np.asarray(composition["center"])
        + v[:, 0, None] * np.asarray(composition["right"])
        + v[:, 1, None] * np.asarray(composition["up"])
        + v[:, 2, None] * np.asarray(composition["normal"])
    )
    ndc, depth = project_points(world, config)
    x0, y0, x1, y1 = composition["opening_ndc"]
    return bool(
        np.all(depth > 0)
        and (
            ndc[:, 0].max() < x0 - margin
            or ndc[:, 0].min() > x1 + margin
            or ndc[:, 1].max() < y0 - margin
            or ndc[:, 1].min() > y1 + margin
        )
    )


def decoration_layout(config, composition):
    """One shared mapping per canopy/floor keeps leaves and their veins attached.

    Check conservative bounds at front AND rear depth; move the entire group
    outward if tiny/portrait layouts leave insufficient perspective guard space.
    """
    sx = composition["width"] / 9.69675559638062
    sy = composition["height"] / 5.454558660720388
    offsets = {}
    for group, edge, direction in [("top", 3.0, 1), ("bottom", -3.20, -1)]:
        offset = 0.0
        for _ in range(400):
            bounds = [
                (x * sx, edge * sy + offset, z)
                for x in (-8, 8)
                for z in ((-0.55, 0.7) if group == "top" else (-1.5, 1.5))
            ]
            if projected_decoration_safe(bounds, config, composition, margin=0.022):
                break
            offset += direction * 0.05
        else:
            raise ValueError("Unable to place safe autumn decoration")
        offsets[group] = offset
    return sx, sy, offsets


def build_exhibition(config, poster, composition, textured_material):
    import bpy
    from mathutils import Vector
    import json

    c = composition
    w, h = c["width"], c["height"]
    p = config.get("panel", {})
    lighting = config.get("lighting", {})
    origin = Vector(c["center"])
    right = Vector(c["right"])
    up = Vector(c["up"])
    normal = Vector(c["normal"])
    objects = []
    decorations = []
    decor_sx, decor_sy, decor_offsets = decoration_layout(config, c)
    root = bpy.data.objects.new("秋韵 · original artwork assembly", None)
    bpy.context.collection.objects.link(root)
    root["template"] = "autumn_symphony"
    root["composition_json"] = json.dumps(c)

    def point(v):
        return origin + right * v[0] + up * v[1] + normal * v[2]

    def mat(name, color, rough=0.6, metal=0, emission=0.0):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        s = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        rgb = linear_rgb(color)
        s.inputs["Base Color"].default_value = (*rgb, 1)
        s.inputs["Roughness"].default_value = rough
        s.inputs["Metallic"].default_value = metal
        s.inputs["Emission"].default_value = (*rgb, 1)
        s.inputs["Emission Strength"].default_value = emission
        return m

    def mesh(name, v, f, m, moving=False, smooth=True, safe=False):
        if safe:
            group = "top" if sum(q[1] for q in v) / len(v) > 0 else "bottom"
            v = [
                (q[0] * decor_sx, q[1] * decor_sy + decor_offsets[group], q[2])
                for q in v
            ]
        if safe and not projected_decoration_safe(v, config, c):
            raise ValueError("Decoration enters original poster guard: " + name)
        data = bpy.data.meshes.new(name)
        data.from_pydata([point(x) for x in v], [], f)
        data.update()
        ob = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(ob)
        data.materials.append(m)
        for poly in data.polygons:
            poly.use_smooth = smooth
        if moving:
            ob.parent = root
        objects.append(ob)
        if safe:
            decorations.append(
                {
                    "name": name,
                    "vertices": len(v),
                    "depth_range_m": [min(x[2] for x in v), max(x[2] for x in v)],
                    "projected_guard_pass": True,
                }
            )
        return ob

    bronze = mat("Brushed champagne · satin bronze", "#9C7957", 0.56, 0.32)
    copper = mat("Autumn copper · matte leaf", "#A95030", 0.79, 0.10)
    honey = mat("Maple honey · restrained gold", "#B88343", 0.78, 0.12)
    wine = mat("Maple garnet", "#8D3D38", 0.64, 0.18)
    vein = mat("Leaf vein · pale bronze", "#8D5737", 0.82, 0.08)
    shell = mat("Deep plum architectural mineral", "#241B36", 0.9, 0, 0.08)
    foldmat = mat("Silken indigo acoustic folds", "#443651", 0.72, 0.12, 0.06)
    edge = mat("Original poster thin plum edge", "#251D32", 0.5, 0.12)
    thick = p.get("thickness_m", 0.035)
    vv, ff = rounded_panel_mesh(w + 0.025, h + 0.025, thick, 0.01)
    mesh("Original poster · physical thin backing", vv, ff, edge, True)
    image = bpy.data.images.load(str(poster), check_existing=True)
    iw, ih = w, h
    if c.get("layout") == "manual":
        ar = image.size[0] / image.size[1]
        iw, ih = (h * ar, h) if w / h > ar else (w, w / ar)
    ob = mesh(
        "Original poster · untouched complete rectangle",
        [
            (-iw / 2, -ih / 2, 0.001),
            (iw / 2, -ih / 2, 0.001),
            (iw / 2, ih / 2, 0.001),
            (-iw / 2, ih / 2, 0.001),
        ],
        [(0, 1, 2, 3)],
        textured_material(poster, "Original artwork · untouched"),
        True,
        False,
    )
    ob.data.uv_layers.new()
    u0, v0, u1, v1 = c.get("uv_crop", [0, 0, 1, 1])
    for loop, uv in zip(
        ob.data.uv_layers.active.data, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    ):
        loop.uv = uv
    # A continuous concave architectural shell, with diagonal carved curvature.
    span = max(c["outer_width"], c["outer_height"]) * 1.5
    n = 96
    vv = []
    ff = []
    for iy in range(n + 1):
        y = (iy / n * 2 - 1) * span
        for ix in range(n + 1):
            x = (ix / n * 2 - 1) * span
            z = (
                -2.0
                + 0.010 * x * x
                + 0.016 * y * y
                + 0.23 * math.sin(x * 0.45 + y * 0.24)
            )
            vv.append((x, y, z))
    for iy in range(n):
        for ix in range(n):
            k = iy * (n + 1) + ix
            ff.append((k, k + 1, k + n + 2, k + n + 1))
    backdrop = mesh("Continuous sculpted plum cyclorama", vv, ff, shell)
    # Procedural broad spatial plum/rose/indigo variation stays on architecture only.
    nodes = shell.node_tree.nodes
    links = shell.node_tree.links
    s = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tex = nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 0.16
    tex.inputs["Detail"].default_value = 1.2
    coord = nodes.new("ShaderNodeTexCoord")
    links.new(
        (
            coord.outputs["Geometry"]
            if "Geometry" in coord.outputs
            else coord.outputs["Object"]
        ),
        tex.inputs["Vector"],
    )
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.20
    ramp.color_ramp.elements[0].color = (*linear_rgb("#0F142A"), 1)
    ramp.color_ramp.elements[1].position = 0.83
    ramp.color_ramp.elements[1].color = (*linear_rgb("#39283F"), 1)
    links.new(tex.outputs["Fac"], ramp.inputs[0])
    links.new(ramp.outputs[0], s.inputs["Base Color"])
    links.new(ramp.outputs[0], s.inputs["Emission"])
    # Rear architectural wings form genuinely tilted/curved interior walls. They may
    # project behind the original, but every vertex is behind its opaque quad.
    wing_materials = [
        mat("Indigo wing · brushed mineral", "#24283F", 0.78, 0.12),
        mat("Plum wing · warm satin mineral", "#3A2944", 0.80, 0.08),
    ]
    for side in (-1, 1):
        wing_v = []
        wing_f = []
        rows = 96
        cols = 24
        for row in range(rows + 1):
            t = row / rows
            y = -7.8 + 12.4 * t
            sweep = 0.55 * math.sin(t * math.pi * 1.5 + side * 0.4)
            for col in range(cols + 1):
                u = col / cols
                x = side * (6.9 - 2.75 * u + sweep)
                z = (
                    -1.85
                    + 1.0 * math.sin(u * math.pi) * math.sin(math.pi * t) ** 0.45
                    - 0.25 * u
                )
                wing_v.append((x, y, z))
        for row in range(rows):
            for col in range(cols):
                j = row * (cols + 1) + col
                wing_f.append(
                    (j, j + 1, j + cols + 2, j + cols + 1)
                    if side < 0
                    else (j + 1, j, j + cols + 1, j + cols + 2)
                )
        wing = mesh(
            "Sculpted rear architectural wing " + str(side),
            wing_v,
            wing_f,
            wing_materials[0 if side < 0 else 1],
        )
        solid = wing.modifiers.new("Mineral wing physical thickness", "SOLIDIFY")
        solid.thickness = 0.04
        assert max(q[2] for q in wing_v) < -0.5
    # Open sculptural arcs continue the musical flourishes in the poster, without enclosing it.
    ribbon_specs = [
        ("Lower champagne cantabile", (-6.8, 6.5), -0.0, 0.18, bronze),
        ("Lower indigo folded acoustic wave", (-7.4, 7.0), -0.60, 1.85, foldmat),
        ("Upper bronze rising overture", (-5.4, 5.0), 0, 0.13, bronze),
    ]
    for idx, (name, ab, offset, width, material) in enumerate(ribbon_specs):
        path = []
        for t in np.linspace(0, 1, 180):
            x = ab[0] + (ab[1] - ab[0]) * t
            if idx < 2:
                y = -4.10 + offset + 0.52 * math.sin(t * math.pi * 2 + 0.8)
                z = -0.35 + 0.52 * math.sin(t * math.pi * 2)
            else:
                y = 3.58 + 0.22 * math.sin(t * math.pi)
                z = -0.25 + 0.32 * math.sin(t * math.pi * 2)
            path.append((x, y, z))
        v, f = ribbon_mesh(path, width, 0.85 if idx < 2 else 0.65)
        rib = mesh(name, v, f, material, safe=True)
        solid = rib.modifiers.new("Physical folded ribbon thickness", "SOLIDIFY")
        solid.thickness = 0.022

    def tube(name, points, radius, material, safe=True):
        # Mesh tube permits export and supplies actual branch/vein silhouette.
        v = []
        f = []
        pts = np.asarray(points)
        tangent = np.gradient(pts, axis=0)
        for i, q in enumerate(pts):
            t = tangent[i] / np.linalg.norm(tangent[i])
            a = np.cross(t, [0, 0, 1])
            if np.linalg.norm(a) < 0.01:
                a = np.cross(t, [0, 1, 0])
            a /= np.linalg.norm(a)
            b = np.cross(t, a)
            for j in range(8):
                v.append(
                    (
                        q
                        + radius
                        * (
                            math.cos(j * math.tau / 8) * a
                            + math.sin(j * math.tau / 8) * b
                        )
                    ).tolist()
                )
        for i in range(len(pts) - 1):
            for j in range(8):
                k = i * 8 + j
                f.append((k, i * 8 + (j + 1) % 8, (i + 1) * 8 + (j + 1) % 8, k + 8))
        return mesh(name, v, f, material, safe=safe)

    # Leaves are hand arranged, asymmetrical, individually curled and rotated.
    leaves = [
        (-4.05, 3.35, 0.22, 0.49, -0.40),
        (-3.18, 3.40, -0.12, 0.45, 0.30),
        (-4.95, 3.35, 0.10, 0.43, -0.8),
        (-2.28, 3.48, -0.4, 0.46, 0.65),
        (-4.45, 3.55, -0.18, 0.40, -0.20),
        (-5.10, 3.52, -0.35, 0.35, 0.70),
        (4.85, -4.23, 0.25, 0.79, 2.2),
        (3.80, -4.65, -0.35, 0.54, 2.6),
        (5.70, -5.15, -0.1, 0.58, 1.6),
    ]
    for i, (x, y, z, size, angle) in enumerate(leaves):
        vv, ff = maple_leaf_mesh(size, 0.16 + 0.04 * (i % 3))
        ca, sa = math.cos(angle), math.sin(angle)

        def transform(q):
            return (x + q[0] * ca - q[1] * sa, y + q[0] * sa + q[1] * ca, z + q[2])

        vv = [transform(q) for q in vv]
        leaf = mesh(
            "Sculpted maple leaf %02d" % i,
            vv,
            ff,
            [honey, copper, wine][i % 3],
            safe=True,
        )
        solid = leaf.modifiers.new("Maple lamina thickness", "SOLIDIFY")
        solid.thickness = 0.012
        for j, tip in enumerate(
            [(0, 0.82), (-0.34, 0.51), (0.34, 0.51), (-0.58, 0.10), (0.58, 0.10)]
        ):
            pts = []
            for t in np.linspace(0, 1, 15):
                q = (
                    tip[0] * size * t,
                    (-0.35 * (1 - t) + tip[1] * t) * size,
                    (0.18 * (1 - t * t) + 0.012) * size,
                )
                pts.append(transform(q))
            tube("Raised maple vein %02d.%d" % (i, j), pts, 0.009 * size, vein)
    tube(
        "Upper canopy · flowing bronze branch",
        [
            (-5.4 + 4.3 * t, 3.38 + 0.27 * math.sin(t * 2), -0.25 + 0.3 * t)
            for t in np.linspace(0, 1, 80)
        ],
        0.035,
        bronze,
    )
    # Lower architectural ripples are inlaid sculptural strokes, no stage plinth.
    for i in range(3):
        pts = [
            (
                -7 + 14 * t,
                -6.1 - i * 0.29 + 0.28 * math.sin(t * math.pi * 1.5),
                -1.0 + i * 0.1,
            )
            for t in np.linspace(0, 1, 120)
        ]
        tube("Quiet acoustic ripple %d" % i, pts, 0.018 if i else 0.03, bronze)

    def light(name, pos, target, power, size, color):
        bpy.ops.object.light_add(type="AREA", location=point(pos))
        l = bpy.context.object
        l.name = name
        l.data.energy = power * lighting.get("intensity", 1)
        l.data.shape = "DISK"
        l.data.size = size * (0.35 + lighting.get("softness", 0.8))
        l.data.color = color
        l.rotation_euler = (
            (point(target) - l.location).to_track_quat("-Z", "Y").to_euler()
        )
        return l

    key = light(
        "Autumn · warm sculptural key",
        (-4, 5, 6),
        (-3, 2, -1),
        1700,
        5,
        (1, 0.72, 0.47),
    )
    fill = light(
        "Autumn · rose atmospheric wash",
        (5, -3, 4),
        (3, -4, -1),
        1250,
        5,
        (1, 0.49, 0.42),
    )
    light(
        "Autumn · cool mineral bounce", (1, 6, 4), (1, 4, -1), 1100, 5, (0.53, 0.58, 1)
    )
    world = next(
        n for n in bpy.context.scene.world.node_tree.nodes if n.type == "BACKGROUND"
    )
    world.inputs["Color"].default_value = (0.10, 0.09, 0.19, 1)
    world.inputs["Strength"].default_value = lighting.get("ambient", 0.5)
    bpy.context.scene.eevee.use_gtao = True
    bpy.context.scene.eevee.gtao_distance = 0.4
    bpy.context.scene.eevee.gtao_factor = 1.15
    report = {
        "template": "autumn_symphony",
        "material": "bespoke_plum_bronze_maple",
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
            "thickness_m": thick,
            "full_rectangular_original": c.get("layout") != "fill",
            "guard_band_m": 0.0125,
        },
        "backdrop": {
            "curved_mesh": True,
            "vertices": len(backdrop.data.vertices),
            "faces": len(backdrop.data.polygons),
            "center_depth_m": -2,
            "procedural_nodes": len(nodes),
        },
        "lighting": {
            "controls": lighting,
            "key_energy_w": key.data.energy,
            "key_size_m": key.data.size,
            "fill_energy_w": fill.data.energy,
            "ambient_strength": world.inputs["Strength"].default_value,
        },
        "architectural_geometry": {
            "style": "autumn_symphony",
            "sculpted_maple_count": len(leaves),
            "open_satin_ribbons": 3,
            "rear_architectural_wings": 2,
            "rear_wing_max_front_depth_m": max(q[2] for q in wing_v),
            "acoustic_ripples": 3,
            "projected_decoration_guard_all_pass": True,
            "decorations": decorations,
        },
        "human_visual_judgment": "PENDING",
    }
    return {
        "root": root,
        "objects": objects,
        "poster_object": ob,
        "key_light": key,
        "report": report,
    }
