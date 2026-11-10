"""Real Blender renderer and camera-to-physical-LED inverse projection.
Run: Blender -b --python studio/blender_render.py -- --config C --poster P --output O
"""
import argparse
import json
import math
import shutil
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from geometry import dimensions, surface_grid, surface_point, visible_points


def material(name, color, emission=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    n = m.node_tree.nodes
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    shader = n.new("ShaderNodeEmission" if emission else "ShaderNodeBsdfPrincipled")
    shader.inputs["Color" if emission else "Base Color"].default_value = (*color, 1)
    if not emission:
        shader.inputs["Roughness"].default_value = 0.27
        shader.inputs["Metallic"].default_value = 0.35
    m.node_tree.links.new(shader.outputs[0], out.inputs["Surface"])
    return m


def cube(name, location, size, mat, bevel=0.04):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    ob = bpy.context.object
    ob.name = name
    ob.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(mat)
    if bevel:
        mod = ob.modifiers.new("Machined edges", "BEVEL")
        mod.width = min(bevel, min(size) / 4)
        mod.segments = 3
        ob.data.use_auto_smooth = True
        ob.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return ob


def save_pixels(path, pixels):
    """Arrays use bottom-left origin, matching Blender's image pixels and UVs."""
    h, w = pixels.shape[:2]
    rgba = np.ones((h, w, 4), np.float32)
    rgba[:, :, :3] = np.clip(pixels[:, :, :3], 0, 1)
    im = bpy.data.images.new(path.stem, width=w, height=h, alpha=False)
    im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = str(path)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)


def read_pixels(path):
    im = bpy.data.images.load(str(path), check_existing=False)
    im.colorspace_settings.name = "Non-Color"
    a = np.empty(im.size[0] * im.size[1] * 4, np.float32)
    im.pixels.foreach_get(a)
    a = a.reshape(im.size[1], im.size[0], 4)[:, :, :3].copy()
    bpy.data.images.remove(im)
    return a


def render(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_mask(scene, path):
    """Independent silhouette uses an actually black node world at every ambient value."""
    world = scene.world
    original = world.use_nodes
    world.use_nodes = True
    background = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    color = background.inputs["Color"].default_value[:]
    strength = background.inputs["Strength"].default_value
    try:
        background.inputs["Color"].default_value = (0, 0, 0, 1)
        background.inputs["Strength"].default_value = 0
        render(scene, path)
    finally:
        background.inputs["Color"].default_value = color
        background.inputs["Strength"].default_value = strength
        world.use_nodes = original


def textured_material(path, name):
    m = material(name, (1, 1, 1), True)
    tex = m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path), check_existing=False)
    tex.image.colorspace_settings.name = "sRGB"
    tex.interpolation = "Linear"
    tex.extension = "CLIP"
    shader = next(n for n in m.node_tree.nodes if n.type == "EMISSION")
    m.node_tree.links.new(tex.outputs["Color"], shader.inputs["Color"])
    return m


def build_target(config, poster):
    from composition import solve_composition
    from scene_design import build_exhibition

    image = bpy.data.images.load(str(poster), check_existing=True)
    return build_exhibition(
        config, poster, solve_composition(config, tuple(image.size)), textured_material
    )


def build_screen(config, atlas):
    s = config["screen"]
    d = dimensions(s)
    # Pixel boundaries at joints; 1 degree tessellation or finer on the arc.
    segments = max(96, math.ceil(s["pixels"][1] * config["render"]["scale"]))
    ss = (
        [0, d["left"]]
        + [d["left"] + d["arc"] * i / segments for i in range(1, segments + 1)]
        + [d["length"]]
    )
    verts = []
    for v in ss:
        verts.extend(
            [
                surface_point(v, -d["height"] / 2, s),
                surface_point(v, d["height"] / 2, s),
            ]
        )
    faces = [(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(len(ss) - 1)]
    mesh = bpy.data.meshes.new("Continuous LED geometry")
    mesh.from_pydata(verts, [], faces)
    mesh.uv_layers.new()
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            vi = mesh.loops[li].vertex_index
            mesh.uv_layers.active.data[li].uv = (ss[vi // 2] / d["length"], vi % 2)
    ob = bpy.data.objects.new("Physical LED · planar arc planar", mesh)
    bpy.context.collection.objects.link(ob)
    led_mat = textured_material(atlas, "LED emission atlas")
    led_mat.use_backface_culling = True
    mesh.materials.append(led_mat)
    return ob


def inverse_project(target, camera, config, aw, ah):
    s = config["screen"]
    d = dimensions(s)
    bpy.context.view_layer.update()
    matrix = np.asarray(camera.matrix_world.inverted(), dtype=float)
    atlas = np.zeros((ah, aw, 3), np.float32)
    valid_count = 0
    fx = 0.5 / math.tan(math.radians(config["camera"]["fov_deg"]) / 2)
    fy = fx * aw / ah
    for row in range(0, ah, 96):
        end = min(ah, row + 96)
        u = (np.arange(aw) + 0.5) / aw
        v = (np.arange(row, end) + 0.5) / ah
        points, normals = surface_grid(
            u[None, :] * d["length"], (v[:, None] - 0.5) * d["height"], s
        )
        local = points @ matrix[:3, :3].T + matrix[:3, 3]
        depth = -local[:, :, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            pu = 0.5 + fx * local[:, :, 0] / depth
            pv = 0.5 + fy * local[:, :, 1] / depth
        valid = (
            (depth > 0)
            & (pu >= 0)
            & (pu <= 1)
            & (pv >= 0)
            & (pv <= 1)
            & visible_points(points, normals, list(camera.location), s)
        )
        xx = np.nan_to_num(np.clip(pu * aw - 0.5, 0, aw - 1), nan=0)
        yy = np.nan_to_num(np.clip(pv * ah - 0.5, 0, ah - 1), nan=0)
        x0 = np.floor(xx).astype(int)
        y0 = np.floor(yy).astype(int)
        x1 = np.minimum(x0 + 1, aw - 1)
        y1 = np.minimum(y0 + 1, ah - 1)
        wx = (xx - x0)[..., None]
        wy = (yy - y0)[..., None]
        sample = (target[y0, x0] * (1 - wx) + target[y0, x1] * wx) * (1 - wy) + (
            target[y1, x0] * (1 - wx) + target[y1, x1] * wx
        ) * wy
        atlas[row:end] = np.where(valid[..., None], sample, 0)
        valid_count += int(valid.sum())
    return atlas, valid_count


def main():
    started = time.time()
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--poster", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    config = json.loads(Path(args.config).read_text())
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    poster = Path(args.poster).resolve()
    s = config["screen"]
    d = dimensions(s)
    r = config["render"]
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = r.get("samples", 16)
    autumn = config["frame"]["template"] == "autumn_resonance_cube"
    art_engine = config.get("autumn", {}).get("engine", "auto")
    use_cycles = r.get("engine") == "CYCLES" or (
        autumn
        and (
            art_engine == "cycles"
            or (
                art_engine == "auto"
                and (r.get("quality") == "high" or r.get("animation", False))
            )
        )
    )
    if config["frame"]["template"] == "autumn_symphony":
        use_cycles = r.get("quality") == "high" or r.get("animation", False)
    if use_cycles:
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = r.get("samples", 16)
        scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.world.use_nodes = True
    background = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    background.inputs["Color"].default_value = (0.004, 0.002, 0.008, 1)
    background.inputs["Strength"].default_value = 0.18
    scene.world.color = (0.004, 0.002, 0.008)
    aw = max(32, round(sum(s["pixels"]) * r["scale"]))
    ah = max(32, round(s["height_px"] * r["scale"]))
    scene.render.resolution_x = aw
    scene.render.resolution_y = ah
    scene.render.resolution_percentage = 100
    scene.render.dither_intensity = 0
    bpy.ops.object.camera_add(location=config["camera"]["position"])
    camera = bpy.context.object
    camera.rotation_euler = (
        (Vector(config["camera"]["target"]) - camera.location)
        .to_track_quat("-Z", "Y")
        .to_euler()
    )
    camera.data.type = "PERSP"
    camera.data.sensor_fit = "HORIZONTAL"
    camera.data.lens = 36 / (
        2 * math.tan(math.radians(config["camera"]["fov_deg"]) / 2)
    )
    scene.camera = camera
    exhibition = build_target(config, poster)
    artwork = exhibition["report"]
    target_objects = list(scene.objects)
    render(scene, out / "scene.png")
    target = read_pixels(out / "scene.png")
    # Independent artwork silhouette. Architecture may deliberately extend off LED.
    poster_ob = exhibition["poster_object"]
    original_poster_mat = poster_ob.data.materials[0]
    for ob in target_objects:
        if ob.type == "MESH" and ob != poster_ob:
            ob.hide_render = True
    poster_ob.data.materials[0] = material("Artwork coverage mask", (1, 1, 1), True)
    render_mask(scene, out / "poster_mask.png")
    poster_mask = read_pixels(out / "poster_mask.png").min(axis=2) > 0.98
    poster_ob.data.materials[0] = original_poster_mat
    for ob in target_objects:
        ob.hide_render = False
    # Project the complete 3D render onto physical LED texels.
    atlas, valid_count = inverse_project(target, camera, config, aw, ah)
    save_pixels(out / "atlas.png", atlas)
    for ob in target_objects:
        if ob.type != "CAMERA":
            ob.hide_render = True
    screen = build_screen(config, out / "atlas.png")
    render(scene, out / "simulation.png")
    simulated = read_pixels(out / "simulation.png")
    original_mat = screen.data.materials[0]
    screen.data.materials[0] = material("Visibility mask", (1, 1, 1), True)
    screen.data.materials[0].use_backface_culling = True
    world_color = scene.world.color[:]
    scene.world.color = (0, 0, 0)
    render_mask(scene, out / "mask.png")
    mask_rgb = read_pixels(out / "mask.png")
    mask = mask_rgb.min(axis=2) > 0.98
    # Conservative edge removal excludes raster anti-alias coverage, not content errors.
    inner = mask.copy()
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        inner &= np.roll(mask, (dy, dx), (0, 1))
    inner[[0, -1], :] = False
    inner[:, [0, -1]] = False
    err = np.abs(simulated - target)
    diff = np.where(mask[..., None], err, 0)
    save_pixels(out / "difference.png", diff)
    check = atlas.copy()
    yy, xx = np.indices((ah, aw))
    grid = (xx % (max(8, aw // 32)) < 1) | (yy % (max(8, ah // 24)) < 1)
    check[grid] = (0.2, 0.85, 1)
    for joint in np.cumsum(s["pixels"])[:-1]:
        col = round(joint / sum(s["pixels"]) * aw)
        check[:, max(0, col - 1) : col + 2] = (1, 0.25, 0.05)
    save_pixels(out / "calibration.png", check)
    screen.data.materials[0] = original_mat
    scene.world.color = world_color
    # Save the editable virtual exhibition; retain the physical LED hidden for inspection.
    screen.hide_render = True
    screen.hide_viewport = True
    for ob in target_objects:
        ob.hide_render = False
    root = exhibition["root"]
    normal = Vector(artwork["composition"]["normal"])
    is_aurora = artwork["template"] in (
        "aurora_float",
        "soft_depth",
        "glass_layers",
        "embedded_cube",
        "embedded_cube_architecture",
        "autumn_resonance_cube",
        "autumn_symphony",
    )
    dynamics = {
        "moving_objects": [
            ob.name for ob in exhibition["objects"] if ob.parent == root
        ],
        "static_architecture": True,
        "enabled": bool(r.get("animation", False)),
        "light_sweep": bool(r.get("light_sweep", False)),
        "frames": [],
    }
    if r.get("animation", False):
        count = max(2, round(r.get("duration", 3) * r.get("fps", 24)))
        scene.render.fps = r.get("fps", 24)
        scene.frame_start = 1
        scene.frame_end = count
        displacement = min(0.5, artwork["composition"]["depth"] * 0.055)
        if artwork["template"] in (
            "embedded_cube_architecture",
            "autumn_resonance_cube",
        ):
            cavity = artwork["architectural_geometry"]
            displacement = min(
                displacement,
                max(
                    0,
                    cavity["poster_distance_from_front_m"]
                    - cavity["wall_thickness_m"]
                    - 0.08,
                ),
            )
        poses = (
            (
                (1, 0),
                (max(2, round(1 + (count - 1) * 0.65)), displacement),
                (count, displacement),
            )
            if is_aurora
            else (
                (1, 0),
                (max(2, round(1 + (count - 1) * 0.35)), displacement),
                (min(count - 1, round(1 + (count - 1) * 0.65)), displacement),
                (count, 0),
            )
        )
        autumn_states, geometry_checks = [], []
        if autumn:
            from studio.autumn_motion import (
                motion_state,
                translation,
                validate_geometry,
                checkpoints,
            )

            # Preflight the complete solid assembly before spending time rendering.
            lights = exhibition.get("lights") or [
                ob for ob in target_objects if ob.type == "LIGHT"
            ]
            if len(lights) != 6:
                raise ValueError(
                    "Autumn motion requires exactly six actual exhibition lights"
                )
            base_energies = [ob.data.energy for ob in lights]
            for fi in range(count):
                state = motion_state(fi / count * 7.5)
                state["actual_time_s"] = fi / scene.render.fps
                offset = translation(state, artwork["composition"])
                geometry = validate_geometry(
                    config,
                    artwork["composition"],
                    artwork["architectural_geometry"],
                    offset,
                )
                if not geometry["passed"]:
                    raise ValueError(
                        "Unsafe Autumn solid motion at frame %d: %s" % (fi, geometry)
                    )
                autumn_states.append(state)
                geometry_checks.append(geometry)
                root.location = Vector(offset)
                root.keyframe_insert(data_path="location", frame=fi + 1)
                for light, base in zip(lights, base_energies):
                    light.data.energy = base * state["light_factor"]
                    light.data.keyframe_insert(data_path="energy", frame=fi + 1)
            # Every sampled pose is explicit; LINEAR avoids Bezier overshoot and
            # reproduces analytic safety exactly at all rendered frame times.
            for animated in [root, *(light.data for light in lights)]:
                for curve in animated.animation_data.action.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "LINEAR"
            check_frames = set(checkpoints(count))
        else:
            for frame, amount in poses:
                root.location = normal * amount
                if is_aurora:
                    root.location += (
                        Vector(artwork["composition"]["up"]) * amount * 0.08
                    )
                root.keyframe_insert(data_path="location", frame=frame)
            check_frames = {
                0,
                count // 2,
                count - 1,
                round((count - 1) * (0.65 if is_aurora else 0.35)),
            }
        # Blender's Bezier interpolation gives a smooth forward/back excursion.
        frames_dir = out / "frames"
        frames_dir.mkdir(exist_ok=True)
        sweep_origin = exhibition["key_light"].location.copy()
        dynamic_checks = []
        for fi in range(count):
            scene.frame_set(fi + 1)
            if autumn:
                expected_offset = translation(autumn_states[fi], artwork["composition"])
                if not np.allclose(
                    np.array(root.location), expected_offset, atol=1e-6, rtol=0
                ):
                    raise ValueError(
                        "Autumn evaluated root differs from preflight at frame %d" % fi
                    )
                geometry_checks[fi] = validate_geometry(
                    config,
                    artwork["composition"],
                    artwork["architectural_geometry"],
                    list(root.location),
                )
                expected_energies = (
                    np.array(base_energies) * autumn_states[fi]["light_factor"]
                )
                if not geometry_checks[fi]["passed"] or not np.allclose(
                    [light.data.energy for light in lights],
                    expected_energies,
                    atol=1e-4,
                    rtol=1e-6,
                ):
                    raise ValueError(
                        "Autumn evaluated geometry/light keyframes failed at frame %d"
                        % fi
                    )
            if r.get("light_sweep", False) and not autumn:
                phase = (
                    min(1.0, fi / max(1, count - 1) / 0.65)
                    if is_aurora
                    else fi / max(1, count - 1)
                )
                exhibition["key_light"].location = sweep_origin + Vector(
                    artwork["composition"]["right"]
                ) * (
                    math.sin(phase * (math.pi * 0.5 if is_aurora else 2 * math.pi))
                    * artwork["poster_display_metres"][0]
                    * (0.12 if is_aurora else 0.4)
                )
                if is_aurora:
                    exhibition["key_light"].keyframe_insert(
                        data_path="location", frame=fi + 1
                    )
            render(scene, out / "motion-source.png")
            if autumn:
                # Direct scene views are honest preview assets, distinct from
                # inverse-projected LED atlases and sampled LED re-renders.
                shutil.copyfile(
                    out / "motion-source.png", frames_dir / ("view_%04d.png" % fi)
                )
            motion = read_pixels(out / "motion-source.png")
            motion_atlas, _ = inverse_project(motion, camera, config, aw, ah)
            save_pixels(frames_dir / ("led_%04d.png" % fi), motion_atlas)
            dynamics["frames"].append(
                {
                    "index": fi,
                    "blender_frame": fi + 1,
                    "translation_m": list(root.location),
                    "path": "frames/led_%04d.png" % fi,
                    **(
                        {
                            "scene_view_path": "frames/view_%04d.png" % fi,
                            "motion": autumn_states[fi],
                            "geometry": geometry_checks[fi],
                            "light_energies_w": [
                                float(light.data.energy) for light in lights
                            ],
                        }
                        if autumn
                        else {}
                    ),
                }
            )
            if fi in check_frames:
                # Independently re-render the actual curved screen at endpoint and midpoint poses.
                for ob in target_objects:
                    if ob.type != "CAMERA":
                        ob.hide_render = True
                screen.hide_render = False
                screen.data.materials[0] = textured_material(
                    frames_dir / ("led_%04d.png" % fi), "Motion LED %d" % fi
                )
                render(scene, out / "motion-check.png")
                recovered = read_pixels(out / "motion-check.png")
                mean_error = float(np.abs(recovered - motion)[inner].mean())
                for ob in target_objects:
                    ob.hide_render = False
                screen.hide_render = True
                for ob in target_objects:
                    if ob.type == "MESH" and ob != poster_ob:
                        ob.hide_render = True
                poster_ob.data.materials[0] = material(
                    "Motion artwork white mask", (1, 1, 1), True
                )
                render_mask(scene, out / "motion-poster-mask.png")
                current_mask = (
                    read_pixels(out / "motion-poster-mask.png").min(axis=2) > 0.98
                )
                poster_ob.data.materials[0] = original_poster_mat
                for ob in target_objects:
                    ob.hide_render = False
                poster_coverage = float(
                    (current_mask & mask).sum() / max(1, current_mask.sum())
                )
                dynamic_checks.append(
                    {
                        "frame": fi,
                        "screen_mae_srgb": mean_error,
                        "poster_coverage": poster_coverage,
                        "passed": mean_error <= 0.04 and poster_coverage >= 0.98,
                    }
                )

        dynamics["timing"] = {
            "forward_end_fraction": 0.65 if is_aurora else 0.35,
            "hold_end_fraction": 1 if is_aurora else 0.65,
            "finish_hold": is_aurora,
            "interpolation": "BEZIER",
            "displacement_m": displacement,
        }
        dynamics["verification"] = dynamic_checks
        dynamics["passed"] = all(item["passed"] for item in dynamic_checks)
        if autumn:
            dynamics["timing"] = dict(
                nominal_timeline_s=7.5,
                actual_duration_s=count / scene.render.fps,
                fps=scene.render.fps,
                frame_count=count,
                sample_time="actual: index / fps; nominal reference: index / count * 7.5",
                interpolation="LINEAR sampled smoothstep/sine-squared",
                stages_s=[0, 1.5, 3.5, 5, 7.5],
                forward_displacement_m=0.20,
                temporary_up_peak_m=0.05,
                nominal_final_hold_seconds=2.5,
                finish_hold=True,
                actual_hold_frames=count - math.ceil(count * 5 / 7.5),
                light_reveal=True,
                light_energy_start_factor=0.55,
                light_energy_end_factor=1.0,
                moving_light_positions=False,
            )
            dynamics["verification_summary"] = dict(
                geometry_checks=len(geometry_checks),
                actual_source_renders=count,
                actual_inverse_projected_atlases=count,
                independent_led_rerenders=len(dynamic_checks),
                independent_poster_silhouettes=len(dynamic_checks),
                independent_check_frames=sorted(check_frames),
                note="All frames have solid-envelope geometry and actual 3D source renders; independent LED camera and coverage checks are sampled.",
            )
            dynamics["passed"] = bool(
                dynamics["passed"] and all(g["passed"] for g in geometry_checks)
            )
        scene.frame_set(1)
        exhibition["key_light"].location = sweep_origin
        screen.data.materials[0] = original_mat
        (out / "motion-check.png").unlink(missing_ok=True)
        (out / "motion-poster-mask.png").unlink(missing_ok=True)
        (out / "motion-source.png").unlink(missing_ok=True)
        (out / "animation.json").write_text(json.dumps(dynamics, indent=2))
    bpy.ops.object.select_all(action="DESELECT")
    for ob in exhibition["objects"]:
        ob.select_set(True)
    root.select_set(True)
    bpy.context.view_layer.objects.active = poster_ob
    try:
        bpy.ops.export_scene.gltf(
            filepath=str(out / "scene.glb"),
            export_format="GLB",
            use_selection=True,
            export_apply=True,
            export_extras=True,
        )
        model_status = "EXPORTED_VIRTUAL_EXHIBITION_MESHES"
    except Exception as exc:
        model_status = "EXPORT_FAILED: " + type(exc).__name__
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "scene.blend"))
    values = err[inner]
    mse = float(np.mean(values**2)) if values.size else None
    mae = float(np.mean(values)) if values.size else None
    full_mae = float(err[mask].mean()) if mask.any() else None
    foreground = poster_mask
    foreground_visible = foreground & inner
    foreground_mae = (
        float(err[foreground_visible].mean()) if foreground_visible.any() else None
    )
    coverage = float((foreground & mask).sum() / max(1, foreground.sum()))
    opening_safe = bool(
        artwork["composition"].get("metrics", {}).get("opening_safe", False)
    )
    passed = bool(
        opening_safe
        and mae is not None
        and mae <= 0.04
        and foreground_mae is not None
        and foreground_mae <= 0.04
        and coverage >= 0.98
        and inner.sum() > 100
    )
    if dynamics["enabled"]:
        passed = bool(passed and dynamics.get("passed", False))
    report = {
        "passed": passed,
        "engine": "Blender " + bpy.app.version_string + " " + scene.render.engine,
        "method": "3D physical continuous surface, perspective inverse projection, bilinear texture sampling, analytic front-face and self-occlusion tests, independent Blender camera re-render",
        "physical": d,
        "atlas_pixels": [aw, ah],
        "nominal_atlas_pixels": [sum(s["pixels"]), s["height_px"]],
        "scale": r["scale"],
        "calibration_status": "MEASURED_INPUT"
        if s.get("calibrated")
        else "NOMINAL_UNCALIBRATED",
        "metrics": {
            "mae_srgb": mae,
            "full_mask_mae_srgb": full_mae,
            "interior_mae_srgb": mae,
            "foreground_mae_srgb": foreground_mae,
            "foreground_coverage": coverage,
            "foreground_pixels": int(foreground_visible.sum()),
            "rmse_srgb": math.sqrt(mse) if mse is not None else None,
            "psnr_db": -10 * math.log10(max(mse, 1e-12)) if mse is not None else None,
            "p95_absolute_error": float(np.quantile(values, 0.95))
            if values.size
            else None,
            "mask_pixels": int(inner.sum()),
            "visible_screen_fraction": float(mask.mean()),
            "valid_atlas_fraction": valid_count / (aw * ah),
        },
        "verification": {
            "criterion": "composition opening must be within the visible screen; interior and artwork mean absolute sRGB error <= 0.04; >=98% independently rendered artwork silhouette covered by visible screen",
            "threshold_mae": 0.04,
            "opening_safe": opening_safe,
            "pass": passed,
        },
        "limitations": [
            "Nominal geometry is not field calibration; measured camera pose, lens distortion and LED transfer response are required on site.",
            "Pixels outside the camera frustum or occluded/back-facing physical surface are black.",
            "Comparison excludes a one-pixel raster boundary; texture resampling and finite curved mesh tessellation contribute remaining error.",
        ],
        "coordinate_system": {
            "units": "metres",
            "up": "Z",
            "curvature": s.get("curvature", "concave"),
            "yaw_deg": s.get("yaw_deg", 0),
            "physical_surface": "studio.geometry.surface_point; centered X bounds; yaw about Z",
            "virtual_frame_basis": artwork["composition"],
        },
        "artwork": artwork,
        "dynamics": dynamics,
        "model_export": model_status,
        "elapsed_seconds": time.time() - started,
        "config": config,
    }
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (out / "visual.json").write_text(
        json.dumps(
            {
                "structural_checks": {
                    "template": artwork["template"],
                    "continuous_miter_profile": None
                    if is_aurora
                    else artwork["profile_stations"] >= 10,
                    "minimal_architecture": is_aurora,
                    "procedural_curved_backdrop": bool(
                        artwork.get("backdrop", {}).get("curved_mesh")
                    ),
                    "layered_ring_count": artwork["continuous_ring_count"],
                    "artwork_coverage_pass": coverage >= 0.98,
                    "opening_safe": opening_safe,
                    "source_aspect": artwork["source_aspect"],
                    "display_aspect": artwork["display_aspect"],
                    "model_export": model_status,
                },
                "human_visual_judgment": "PENDING",
                "note": "Numerical projection agreement and scene structure do not establish visual quality.",
            },
            indent=2,
        )
    )
    print("RENDER_REPORT " + json.dumps(report["metrics"]))


if __name__ == "__main__":
    main()
