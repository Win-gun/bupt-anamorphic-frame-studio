"""Autumn Resonance: art direction on the shared excavated-room geometry.

Pure plans also drive the Blender shader and lamp creation, so validation checks
actual emitter surfaces rather than unrelated bounding-box approximations.
"""
import copy
import math
import numpy as np
from studio.embedded_cube_scene import architecture_plan, build_exhibition as build_cube

# Blender has no Pydantic dependency; read the same canonical art defaults.
import json
from pathlib import Path

DEFAULTS = json.loads(
    (
        Path(__file__).resolve().parent.parent / "configs/bupt-curved-led.json"
    ).read_text()
)["autumn"]

BASE_COLORS = dict(
    facade="#858D9A",
    ceiling="#B8B5C0",
    left="#8F86A1",
    right="#8491A4",
    rear="#A79BAA",
    floor="#777C8D",
    cut="#B5A9B8",
)
VARIANTS = {
    "balanced": dict(tint="#B5A9B8", warm=1.0, cool=1.0, ceiling="#F1DED0"),
    "warm": dict(tint="#D8B7A7", warm=1.30, cool=0.72, ceiling="#F4DBBF"),
    "cool": dict(tint="#727B90", warm=0.65, cool=1.22, ceiling="#DCE3EE"),
}


def linear_color(value):
    rgb = [int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb
    )


def effective_config(config):
    result = copy.deepcopy(config)
    settings = dict(DEFAULTS, **result.get("autumn", {}))
    result["autumn"] = settings
    result["frame"]["template"] = "embedded_cube_architecture"
    result.setdefault("cube", {})["poster_depth_fraction"] = settings[
        "poster_depth_fraction"
    ]
    return result


def emitter_samples(position, target, diameter, count=64):
    """Sample the oriented emitter circumference in physical room coordinates."""
    position, target = np.array(position, float), np.array(target, float)
    normal = target - position
    normal /= np.linalg.norm(normal)
    helper = (
        np.array([0.0, 1.0, 0.0])
        if abs(normal[1]) < 0.95
        else np.array([1.0, 0.0, 0.0])
    )
    u = np.cross(normal, helper)
    u /= np.linalg.norm(u)
    v = np.cross(normal, u)
    angles = np.linspace(0, math.tau, count, endpoint=False)
    return position + diameter / 2 * (
        np.cos(angles)[:, None] * u + np.sin(angles)[:, None] * v
    )


def artistic_plan(config, geometry):
    a = dict(DEFAULTS, **config.get("autumn", {}))
    variant = VARIANTS[a["variant"]]
    w, h, d, t = (geometry[k] for k in ("width", "height", "depth", "wall_thickness"))
    # Colour positions artistically approximate the original poster's upper-left
    # autumn light, right stage light and lower pink stage wash; not photometry.
    specifications = [
        (
            "ceiling",
            (0, h * 0.18, -d * 0.38),
            (0, h * 0.18, -d),
            180,
            4.5,
            variant["ceiling"],
        ),
        (
            "autumn_left",
            (-w * 0.28, h * 0.20, -d * 0.29),
            (-w * 0.28, h * 0.10, -d),
            95 * variant["warm"],
            2.7,
            "#E9AC7F",
        ),
        (
            "smoky_right",
            (w * 0.28, h * 0.06, -d * 0.30),
            (w * 0.28, 0, -d),
            85 * variant["cool"],
            2.7,
            "#B5B6DA",
        ),
        (
            "stage_floor",
            (0, -h * 0.32, -d * 0.28),
            (0, -h * 0.25, -d),
            45 * variant["warm"],
            2.4,
            "#DAB8C9",
        ),
        ("rear_wash", (0, h * 0.12, -d * 0.40), (0, h * 0.12, -d), 55, 3.5, "#DDD0DC"),
        (
            "facade",
            (-w * 0.20, h * 0.30, 7),
            (-w * 0.20, h * 0.30, 0),
            850,
            max(w, h) * 1.65,
            "#E5E6ED",
        ),
    ]
    lamps = []
    lo = np.array([-w / 2 + 0.03, -h / 2 + 0.03, -d + 0.03])
    hi = np.array([w / 2 - 0.03, h / 2 - 0.03, -t - 0.03])
    for name, position, target, energy, size, color in specifications:
        if name != "facade":
            position = (*position[:2], max(-d + 0.15, min(-t - 0.10, position[2])))
        diameter = size * (0.55 + 0.5625 * a["softness"])
        if name != "facade":
            # Use analytic disc support in each axis: guarantees the complete
            # surface fits, even between circumference validation samples.
            normal = np.array(target) - position
            normal = normal / np.linalg.norm(normal)
            radial_extent = np.sqrt(np.maximum(0, 1 - normal * normal))
            clearance = np.minimum(np.array(position) - lo, hi - position)
            limits = [
                2 * clearance[i] / radial_extent[i]
                for i in range(3)
                if radial_extent[i] > 1e-8
            ]
            diameter = min(diameter, min(limits) * 0.98)
        samples = emitter_samples(position, target, diameter)
        safe = (
            bool(np.all(samples[:, 2] > 0.05))
            if name == "facade"
            else bool(np.all(samples > lo) and np.all(samples < hi))
        )
        if diameter <= 0 or not safe:
            raise ValueError("Autumn emitter intersects architectural solid: " + name)
        lamps.append(
            dict(
                name=name,
                position=list(position),
                target=list(target),
                energy_w=energy * a["light_intensity"],
                diameter_m=float(diameter),
                color_hex=color,
                entire_emitter_inside_free_space=safe,
            )
        )
    return dict(
        settings=a,
        palette=BASE_COLORS,
        variant=variant,
        lights=lamps,
        poster_light_link="artistic approximation of three source-poster light regions",
    )


def mineral_material(name, base_hex, finish, coordinates, geometry, art):
    import bpy

    a = art["settings"]
    mat = bpy.data.materials.new("Autumn mineral · " + name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Metallic"].default_value = 0
    shader.inputs["Roughness"].default_value = finish
    specular = shader.inputs.get("Specular IOR Level") or shader.inputs.get("Specular")
    specular.default_value = a["edge_highlight"]
    tex = nodes.new("ShaderNodeTexCoord")
    tex.object = coordinates
    tex.label = "Shared room coordinates in metres; no per-face Generated mapping"
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 185
    noise.inputs["Detail"].default_value = 2
    noise.inputs["Roughness"].default_value = 0.55
    links.new(tex.outputs["Object"], noise.inputs["Vector"])
    micro = nodes.new("ShaderNodeValToRGB")
    micro.label = "Restrained mineral grain"
    micro.color_ramp.elements[0].color = (0.44, 0.44, 0.44, 1)
    micro.color_ramp.elements[1].color = (0.56, 0.56, 0.56, 1)
    links.new(noise.outputs["Fac"], micro.inputs["Fac"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.30
    bump.inputs["Distance"].default_value = a["texture_strength_m"]
    links.new(micro.outputs["Color"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    normalize = nodes.new("ShaderNodeVectorMath")
    normalize.operation = "MULTIPLY"
    normalize.inputs[1].default_value = (
        1 / geometry["width"],
        1 / geometry["height"],
        1 / geometry["depth"],
    )
    links.new(tex.outputs["Object"], normalize.inputs[0])
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(normalize.outputs["Vector"], sep.inputs[0])
    gradient = nodes.new("ShaderNodeMath")
    gradient.operation = "MULTIPLY_ADD"
    gradient.inputs[1].default_value = 1 if name == "ceiling" else 0.8
    gradient.inputs[2].default_value = 1 if name == "ceiling" else 0.5
    links.new(sep.outputs["Z" if name == "ceiling" else "Y"], gradient.inputs[0])
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.label = "Broad low-saturation spatial mineral gradient"
    ramp.color_ramp.interpolation = "EASE"
    base = np.array(linear_color(base_hex))
    tint = np.array(linear_color(art["variant"]["tint"]))
    low = base * 0.83
    high = base * (1 - a["gradient_strength"]) + tint * a["gradient_strength"]
    if name == "ceiling":
        high = high * 1.12
    ramp.color_ramp.elements[0].color = (*low, 1)
    ramp.color_ramp.elements[1].color = (*high, 1)
    links.new(gradient.outputs[0], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    links.new(shader.outputs[0], output.inputs["Surface"])
    mat["micro_bump_distance_m"] = a["texture_strength_m"]
    mat["room_coordinates"] = coordinates.name
    return mat


def _apply(result, context, config):
    import bpy
    from mathutils import Matrix, Vector

    geometry, point = context["plan"], context["point"]
    art = artistic_plan(config, geometry)
    a = art["settings"]
    room = geometry["opening"]
    coordinates = bpy.data.objects.new("Autumn · shared mineral coordinates", None)
    bpy.context.collection.objects.link(coordinates)
    coordinates.matrix_world = Matrix(
        ((*room["right"], 0), (*room["up"], 0), (*room["normal"], 0), (0, 0, 0, 1))
    ).transposed()
    coordinates.location = Vector(room["center"])
    materials = {
        key: mineral_material(
            key,
            color,
            0.88
            if key == "rear"
            else 0.74
            if key == "floor"
            else 0.65
            if key == "cut"
            else 0.82,
            coordinates,
            geometry,
            art,
        )
        for key, color in BASE_COLORS.items()
    }
    for ob in result["objects"]:
        if ob.name.startswith("Building facade"):
            ob.data.materials[0] = materials["facade"]
            ob.data.materials[1] = materials["cut"]
            mod = next(m for m in ob.modifiers if m.type == "BEVEL")
            mod.width = min(a["opening_bevel_m"], geometry["wall_thickness"] * 0.24)
            mod.segments = 4
        elif ob.name.startswith("Excavated room"):
            key = next(
                k
                for k in ("left", "right", "ceiling", "floor", "rear")
                if k.upper() in ob.name
            )
            ob.data.materials[0] = materials[key]
        elif ob.name.startswith("Poster backing"):
            # Existing 24 mm slab leaves a 1 mm gap below the exact original UV plane.
            mod = next(m for m in ob.modifiers if m.type == "BEVEL")
            mod.width = min(a["panel_bevel_m"], 0.024 * 0.49)
            mod.segments = 4
            ob.data.materials[0] = materials["cut"]
    for lamp in context["lights"]:
        bpy.data.objects.remove(lamp, do_unlink=True)
    lamps = []
    for p in art["lights"]:
        data = bpy.data.lights.new("Autumn · " + p["name"], "AREA")
        ob = bpy.data.objects.new(data.name, data)
        bpy.context.collection.objects.link(ob)
        ob.location = point(p["position"])
        ob.rotation_euler = (
            (point(p["target"]) - ob.location).to_track_quat("-Z", "Y").to_euler()
        )
        data.energy, data.shape, data.size = p["energy_w"], "DISK", p["diameter_m"]
        data.color = linear_color(p["color_hex"])
        data.use_shadow = True
        if hasattr(data, "use_contact_shadow"):
            data.use_contact_shadow = True
        lamps.append(ob)
    world = next(
        n for n in bpy.context.scene.world.node_tree.nodes if n.type == "BACKGROUND"
    )
    world.inputs["Color"].default_value = (*linear_color("#B4B9C8"), 1)
    # Ambient provides real diffuse fill; shadow control changes fill/key balance.
    world.inputs["Strength"].default_value = a["ambient"] * (
        0.7 + 0.8 * (1 - a["shadow_strength"])
    )
    scene = bpy.context.scene
    if hasattr(scene, "eevee"):
        scene.eevee.gtao_factor = 0.65 + 0.6 * a["shadow_strength"]
        scene.eevee.gtao_distance = 0.5
    result["root"]["template"] = "autumn_resonance_cube"
    result["key_light"] = lamps[0]
    result["lights"] = lamps
    report = result["report"]
    report.update(
        template="autumn_resonance_cube",
        material="matte_mineral_microcement",
        autumn=art,
    )
    report["architectural_geometry"].update(
        opening_chamfer_m=min(a["opening_bevel_m"], geometry["wall_thickness"] * 0.24),
        panel_bevel_m=min(a["panel_bevel_m"], 0.024 * 0.49),
        panel_slab_thickness_m=0.024,
        panel_surface_gap_m=0.001,
        panel_total_envelope_m=0.025,
    )
    report["lighting"] = dict(
        lights=art["lights"],
        ambient_strength=world.inputs["Strength"].default_value,
        real_area_shadows=True,
    )
    report["material_nodes"] = dict(
        shared_coordinate_object=coordinates.name,
        noise_scale_per_m=185,
        noise_detail=2,
        bump_strength=0.30,
        bump_distance_m=a["texture_strength_m"],
        roughness=dict(walls=0.82, rear=0.88, floor=0.74, cut=0.65),
        metallic=0,
        specular=a["edge_highlight"],
        source_poster_shader="unchanged original full-UV emission",
    )


def build_exhibition(config, poster, composition, textured_material):
    effective = effective_config(config)
    return build_cube(
        effective,
        poster,
        composition,
        textured_material,
        postbuild=lambda result, context: _apply(result, context, effective),
    )
