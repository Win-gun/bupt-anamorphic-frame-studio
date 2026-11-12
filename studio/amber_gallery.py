"""A layered bronze and mineral gallery for the Ji Qi Qiu Yun poster."""
import math

import numpy as np

from studio.aurora_scene import linear_rgb, rounded_panel_mesh
from studio.composition import camera_basis, project_points
from studio.symphony_scene import maple_leaf_mesh


TEMPLATE = "autumn_amber_gallery"


def patch(rows, cols, point):
    vertices = [
        point(i / rows, j / cols) for i in range(rows + 1) for j in range(cols + 1)
    ]
    faces = []
    for i in range(rows):
        for j in range(cols):
            a = i * (cols + 1) + j
            faces.append((a, a + 1, a + cols + 2, a + cols + 1))
    return vertices, faces


def tube(points, radius):
    """Closed, softly tapered molding with a circular section."""
    points = np.asarray(points)
    directions = np.gradient(points, axis=0)
    vertices = []
    sides = 10
    for i, (point, direction) in enumerate(zip(points, directions)):
        direction /= np.linalg.norm(direction)
        axis = np.array([0.0, 0.0, 1.0])
        if abs(direction @ axis) > 0.94:
            axis = np.array([1.0, 0.0, 0.0])
        across = np.cross(direction, axis)
        across /= np.linalg.norm(across)
        up = np.cross(direction, across)
        t = i / (len(points) - 1)
        r = radius * (0.36 + 0.64 * math.sin(math.pi * t) ** 0.28)
        for j in range(sides):
            angle = j * math.tau / sides
            vertices.append(
                point + r * (across * math.cos(angle) + up * math.sin(angle))
            )
    faces = [tuple(reversed(range(sides)))]
    for i in range(len(points) - 1):
        for j in range(sides):
            a = i * sides + j
            b = i * sides + (j + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.append(tuple(range(len(vertices) - sides, len(vertices))))
    return vertices, faces


def build_exhibition(config, poster, composition, textured_material):
    import bpy
    from mathutils import Euler, Vector

    c = composition
    width, height = c["width"], c["height"]
    origin = np.array(c["center"])
    basis = np.array([c["right"], c["up"], c["normal"]])
    camera, *_ = camera_basis(config)
    depth = c["depth"]
    relief_scale = min(1, depth / 9)
    objects = []
    sculptures = []
    root = bpy.data.objects.new("琥珀回廊 · poster", None)
    bpy.context.collection.objects.link(root)
    root["template"] = TEMPLATE
    lighting = config["lighting"]

    def world(xyz):
        return np.asarray(xyz) @ basis + origin

    def on_ray(x, y, z):
        plane = world((x, y, 0))
        return camera + (plane - camera) * (1 - z * relief_scale / depth)

    def material(name, color, roughness, metallic=0, texture=0, emission=0):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.diffuse_color = (*linear_rgb(color), 1)
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        shader = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
        shader.inputs["Base Color"].default_value = mat.diffuse_color
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Metallic"].default_value = metallic
        shader.inputs["Anisotropic"].default_value = 0.32 if metallic else 0
        shader.inputs["Emission"].default_value = mat.diffuse_color
        shader.inputs["Emission Strength"].default_value = emission
        if texture:
            noise = nodes.new("ShaderNodeTexNoise")
            noise.inputs["Scale"].default_value = 95 if metallic else 67
            noise.inputs["Detail"].default_value = 2
            coords = nodes.new("ShaderNodeTexCoord")
            links.new(coords.outputs["Object"], noise.inputs["Vector"])
            bump = nodes.new("ShaderNodeBump")
            bump.inputs["Strength"].default_value = 0.24
            bump.inputs["Distance"].default_value = texture
            links.new(noise.outputs["Fac"], bump.inputs["Height"])
            links.new(bump.outputs["Normal"], shader.inputs["Normal"])
            variation = nodes.new("ShaderNodeMath")
            variation.operation = "MULTIPLY_ADD"
            variation.inputs[1].default_value = 0.13
            variation.inputs[2].default_value = roughness - 0.065
            links.new(noise.outputs["Fac"], variation.inputs[0])
            links.new(variation.outputs[0], shader.inputs["Roughness"])
        return mat

    def mesh(name, vertices, faces, mat, thickness=0, moving=False, surface=True):
        data = bpy.data.meshes.new(name)
        data.from_pydata(vertices, [], faces)
        data.update()
        ob = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(ob)
        data.materials.append(mat)
        for face in data.polygons:
            face.use_smooth = surface
        if thickness:
            modifier = ob.modifiers.new("Solid material thickness", "SOLIDIFY")
            modifier.thickness = thickness
        if moving:
            ob.parent = root
        objects.append(ob)
        return ob

    bronze = material("Satin champagne bronze", "#A36C3B", 0.35, 0.72, 0.003)
    dark = material("Indigo mineral plaster", "#28223E", 0.66, 0.07, 0.005, 0.035)
    plum = material("Plum ceramic glaze", "#514262", 0.46, 0.15, 0.003, 0.03)
    underside = material("Aubergine satin", "#382742", 0.45, 0.26, 0.004, 0.04)
    warm = material("Amber ceramic maple", "#D28131", 0.34, 0.26, 0.004)
    red = material("Oxide copper maple", "#B54C37", 0.4, 0.32, 0.004)
    vein_mat = material("Bronze maple veins", "#A86C36", 0.49, 0.46)
    inlay = material("Recessed warm inlay", "#FFCA82", 0.38, 0.15, emission=0.12)
    backing = material("Poster edge", "#261D30", 0.48, 0.12)
    thick = config["panel"]["thickness_m"]
    vertices, faces = rounded_panel_mesh(width + 0.026, height + 0.026, thick, 0.012)
    mesh("Original poster backing", world(vertices), faces, backing, moving=True)

    image = bpy.data.images.load(str(poster), check_existing=True)
    iw, ih = width, height
    if c["layout"] == "manual":
        ratio = image.size[0] / image.size[1]
        iw, ih = min(width, height * ratio), min(height, width / ratio)
    u0, v0, u1, v1 = c["uv_crop"]
    poster_quad = mesh(
        "Original poster · full image",
        world(
            [
                (-iw / 2, -ih / 2, 0.002),
                (iw / 2, -ih / 2, 0.002),
                (iw / 2, ih / 2, 0.002),
                (-iw / 2, ih / 2, 0.002),
            ]
        ),
        [(0, 1, 2, 3)],
        textured_material(poster, "Original poster emission"),
        moving=True,
        surface=False,
    )
    uv_layer = poster_quad.data.uv_layers.new()
    for loop, uv in zip(uv_layer.data, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]):
        loop.uv = uv

    span = max(c["outer_width"], c["outer_height"]) * 1.3
    verts, faces = patch(
        12, 16, lambda u, v: world(((u - 0.5) * span * 2, (v - 0.5) * span * 2, -3.6))
    )
    mesh("Deep violet gallery back", verts, faces, dark)

    # Continuous lofts curl forward into the viewing space. Their silhouettes
    # are controlled in the poster plane to keep the original artwork clear.
    def canopy(u, t, relief=0):
        x = (u - 0.5) * c["outer_width"] * 1.32
        y = (
            height / 2
            + 0.28
            + 0.40 * math.sin(math.pi * u)
            + t * c["outer_height"] * 0.26
        )
        z = -2.4 + 4.25 * t + 0.16 * math.sin(u * math.tau * 17) * math.sin(math.pi * t)
        return on_ray(x, y, z + relief)

    verts, faces = patch(160, 24, canopy)
    mesh("Fluted curved ceiling", verts, faces, plum, 0.08)
    for start, end, mat in [(0.08, 0.115, bronze), (0.29, 0.302, inlay)]:
        verts, faces = patch(
            160,
            3,
            lambda u, v: canopy(0.035 + 0.93 * u, start + (end - start) * v, 0.14),
        )
        mesh("Ceiling inset molding", verts, faces, mat, 0.022)

    for side in (-1, 1):

        def wing(u, t):
            y = (u - 0.5) * c["outer_height"] * 1.28
            x = side * (
                width / 2
                + 0.20
                + t * 0.23 * c["outer_width"]
                + 0.08 * math.cos(math.tau * u)
            )
            z = (
                -2.5
                + 4 * t
                + 0.14 * math.sin(math.tau * u * 14) * math.sin(math.pi * t)
            )
            return on_ray(x, y, z)

        verts, faces = patch(150, 24, wing)
        mesh("Sculpted mineral side reveal", verts, faces, dark, 0.07)
        verts, faces = tube(
            [wing(u, 0.22) for u in np.linspace(0.03, 0.97, 120)], 0.022
        )
        mesh("Side satin bronze bead", verts, faces, bronze)

    for index, (name, mat) in enumerate(
        [
            ("Recessed aubergine lower fold", underside),
            ("Champagne folded edge", bronze),
            ("Foreground sculpted plum fold", plum),
        ]
    ):

        def fold(u, t):
            x = (u - 0.5) * c["outer_width"] * 1.30
            bow = 0.25 * math.sin(math.tau * u + 0.4) + 0.45 * (u - 0.5)
            near = [0.7, 1.6, 2.65][index]
            y = -height / 2 - 0.64 - 0.27 * index + bow
            y -= t * (0.30 if index == 1 else 0.89)
            z = (
                near
                + (t - 0.5) * 1.30
                + 0.42 * math.sin(math.tau * u - 0.7)
                + 0.39 * math.sin(math.pi * t)
            )
            return on_ray(x, y, z)

        verts, faces = patch(144, 24, fold)
        mesh(name, verts, faces, mat, 0.095)
        verts, faces = tube(
            [fold(u, 0.06) for u in np.linspace(0.035, 0.965, 120)], 0.023
        )
        mesh(name + " · rolled edge", verts, faces, bronze)

    # A folded leaf is a small relief sculpture. Each vein follows the same
    # surface coordinates as the leaf, and all parts share its tilt in depth.
    outline = np.asarray(maple_leaf_mesh()[0][-20:])[:, :2]

    def leaf_surface(x, y, r):
        return np.array(
            [
                x,
                y,
                0.27 * (1 - r * r)
                + 0.12 * r * r * math.sin(5 * x + 3 * y)
                - 0.14 * y * y,
            ]
        )

    def leaf(name, x, y, z, size, rotation, mat):
        matrix = np.asarray(Euler(rotation).to_matrix())
        anchor = on_ray(x, y, z)

        def transform(p):
            return anchor + world(np.asarray(p) @ matrix.T * size) - origin

        ring = []
        for i, a in enumerate(outline):
            b = outline[(i + 1) % len(outline)]
            for t in (0, 0.24, 0.5, 0.76):
                q = (1 - t) * a + t * b
                if t == 0.5:
                    q *= 1.035
                ring.append(q)
        count = len(ring)
        leaf_vertices = [transform(leaf_surface(0, 0, 0))]
        for r in np.linspace(0.125, 1, 8):
            leaf_vertices.extend(
                transform(leaf_surface(x * r, y * r, r)) for x, y in ring
            )
        ndc, _ = project_points(leaf_vertices, config)
        x0, y0, x1, y1 = c["opening_ndc"]
        if not (ndc[:, 1].min() > y1 + 0.012 or ndc[:, 1].max() < y0 - 0.012):
            return
        faces = [(0, 1 + (i + 1) % count, 1 + i) for i in range(count)]
        for row in range(7):
            for i in range(count):
                a = 1 + row * count + i
                b = 1 + row * count + (i + 1) % count
                faces.append((a, b, b + count, a + count))
        mesh(name, leaf_vertices, faces, mat, 0.014)
        for tip in [
            (0, 0.94),
            (-0.37, 0.61),
            (0.37, 0.61),
            (-0.64, 0.30),
            (0.64, 0.30),
        ]:
            path = []
            for t in np.linspace(0, 0.91, 24):
                p = leaf_surface(t * tip[0], t * tip[1], t)
                p[2] += 0.015
                path.append(transform(p))
            verts, faces = tube(path, 0.012 * size)
            mesh(name + " · tapered vein", verts, faces, vein_mat)
        sculptures.append(
            {
                "name": name,
                "center_depth_m": z * relief_scale,
                "vertices": len(leaf_vertices),
            }
        )

    s = min(1.1, width / 8.4, height / 4.7)
    leaf_specs = [
        (-0.365, 0.5, 0.91, 1.4, 0.69, (0.2, -0.20, -0.40)),
        (-0.45, 0.5, 0.80, 0.42, 0.43, (-0.44, 0.28, 0.42)),
        (-0.25, 0.5, 1.10, -0.40, 0.39, (0.38, 0.41, -1.05)),
        (0.245, -0.5, -1.03, 0.96, 0.53, (0.37, -0.28, -0.87)),
        (0.364, -0.5, -1.03, 2.05, 0.84, (-0.38, 0.40, 0.74)),
        (0.451, -0.5, -1.36, 2.65, 0.42, (0.24, -0.48, -1.32)),
    ]
    for i, (x, y, offset, z, size, rotation) in enumerate(leaf_specs):
        leaf(
            f"Folded maple {i+1:02}",
            x * width,
            y * height + offset * s,
            z,
            size * s,
            rotation,
            warm if i % 3 != 1 else red,
        )

    def area(name, position, aim, power, size, color):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = power * lighting["intensity"]
        data.shape = "DISK"
        data.size = size * (0.4 + 0.75 * lighting["softness"])
        data.color = color
        ob = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(ob)
        ob.location = world(position)
        ob.rotation_euler = (
            (Vector(world(aim)) - ob.location).to_track_quat("-Z", "Y").to_euler()
        )
        return ob

    key = area(
        "Warm broad key",
        (-4.4, 4.8, 6.9),
        (-1.8, 2.7, -0.7),
        2200,
        4.2,
        (1, 0.74, 0.52),
    )
    area(
        "Lavender contour",
        (5.2, 2.0, 4.2),
        (3.8, 0.8, -1.8),
        1550,
        3.5,
        (0.56, 0.63, 1),
    )
    area(
        "Rose grazing light",
        (4.4, -4.5, 5.7),
        (2, -3.6, 1.1),
        680,
        3.7,
        (1, 0.67, 0.58),
    )
    area(
        "Warm reflected fill",
        (-4.5, -3.5, 4.4),
        (-0.8, -3.7, 1.2),
        490,
        4.6,
        (1, 0.86, 0.73),
    )
    scene = bpy.context.scene
    background = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    background.inputs["Color"].default_value = (0.22, 0.18, 0.30, 1)
    background.inputs["Strength"].default_value = lighting["ambient"] * 0.65
    scene.eevee.use_gtao = True
    scene.eevee.gtao_distance = 0.55
    scene.eevee.gtao_factor = 1.15

    return {
        "root": root,
        "objects": objects,
        "poster_object": poster_quad,
        "key_light": key,
        "report": {
            "template": TEMPLATE,
            "material": "satin_bronze_ceramic_mineral",
            "poster_original_pixels": list(image.size),
            "poster_display_metres": [iw, ih],
            "poster_aspect_preserved": c["layout"] != "fill",
            "source_aspect": image.size[0] / image.size[1],
            "display_aspect": iw / ih,
            "uv_crop": c["uv_crop"],
            "effective_frame_position": origin.tolist(),
            "composition": c,
            "continuous_ring_count": 0,
            "profile_stations": 0,
            "profile_faces": 0,
            "mesh_count": len(objects),
            "panel": {
                "thickness_m": thick,
                "full_rectangular_original": c["layout"] != "fill",
            },
            "backdrop": {"curved_mesh": True},
            "architectural_geometry": {
                "style": TEMPLATE,
                "sculpted_maple_count": len(sculptures),
                "leaves": sculptures,
                "ceiling_flutes": 17,
                "solid_lower_folds": 3,
            },
            "lighting": {
                "controls": lighting,
                "area_lights": 4,
                "key_energy_w": key.data.energy,
            },
        },
    }
