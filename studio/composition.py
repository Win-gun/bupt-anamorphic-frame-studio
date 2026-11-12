"""Camera-space composition against the actual visible LED silhouette.

All math is NumPy-only, shared by offline tests and Blender. NDC uses horizontal
camera FOV and output aspect sum(screen.pixels)/screen.height_px. A binary ray
mask finds an inscribed opening; no world-space centering assumptions are used.
"""
import math
import numpy as np
from studio.geometry import dimensions, surface_grid, visible_points, ray_surface_hit


def camera_basis(config):
    config = config.model_dump() if hasattr(config, "model_dump") else config
    camera = config["camera"]
    position = np.asarray(camera["position"], dtype=float)
    forward = np.asarray(camera["target"], dtype=float) - position
    forward /= np.linalg.norm(forward)
    reference = np.array([0.0, 0.0, 1.0])
    if abs(forward @ reference) > 0.999:
        reference = np.array([0.0, 1.0, 0.0])
    right = np.cross(forward, reference)
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    aspect = sum(config["screen"]["pixels"]) / config["screen"]["height_px"]
    tx = math.tan(math.radians(camera["fov_deg"]) / 2)
    return position, forward, right, up, tx, tx / aspect


def project_points(points, config):
    position, forward, right, up, tx, ty = camera_basis(config)
    rel = np.asarray(points) - position
    depth = rel @ forward
    return (
        np.stack([(rel @ right) / (depth * tx), (rel @ up) / (depth * ty)], axis=-1),
        depth,
    )


def visible_screen_mask(config, resolution=256):
    """Pixel-center NDC mask obtained by analytic rays, including occlusion."""
    position, forward, right, up, tx, ty = camera_basis(config)
    axis = (np.arange(resolution) + 0.5) * 2 / resolution - 1
    x, y = np.meshgrid(axis, axis)
    rays = forward + x[..., None] * tx * right + y[..., None] * ty * up
    distance, front = ray_surface_hit(position, rays, config["screen"])
    return np.isfinite(distance) & front


def _rectangle(mask, ratio):
    """Largest all-true axis-aligned rectangle with specified NDC aspect."""
    n = len(mask)
    # Erode one pixel on every side. This also avoids sampled silhouette edges.
    safe = mask.copy()
    safe[0] = safe[-1] = False
    safe[:, 0] = safe[:, -1] = False
    safe[1:] &= mask[:-1]
    safe[:-1] &= mask[1:]
    safe[:, 1:] &= mask[:, :-1]
    safe[:, :-1] &= mask[:, 1:]
    integral = np.pad((~safe).astype(int), ((1, 0), (1, 0))).cumsum(0).cumsum(1)

    def candidates(h):
        w = max(1, int(math.ceil(h * ratio)))
        if w > n or h > n:
            return None
        counts = (
            integral[h:, w:]
            - integral[:-h, w:]
            - integral[h:, :-w]
            + integral[:-h, :-w]
        )
        ys, xs = np.where(counts == 0)
        if not len(xs):
            return None
        # Stable center preference among equally sized placements.
        i = np.argmin((xs + w / 2 - n / 2) ** 2 + (ys + h / 2 - n / 2) ** 2)
        return xs[i], ys[i], w, h

    lo, hi, best = 1, n, None
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = candidates(mid)
        if candidate is None:
            hi = mid - 1
        else:
            best = candidate
            lo = mid + 1
    if best is None:
        raise ValueError("No usable front-visible screen area for this camera")
    x, y, w, h = best
    # Continuous exact ratio inside the raster-safe rectangle.
    width, height = min(w, h * ratio), min(h, w / ratio)
    cx, cy = x + w / 2, y + h / 2
    return (
        np.array([cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2])
        * 2
        / n
        - 1
    )


def solve_composition(config, poster_size, resolution=256):
    """Return camera-aligned inner opening and outer portal dimensions in metres.

    auto_fit preserves poster aspect, fill uses explicit frame aspect with a
    centered UV crop, manual honors absolute position/size. Auto position values
    are local right/up/forward offsets; nonzero offsets can leave the silhouette
    and are reported by opening_safe. virtual_depth_m moves the shared plane.
    """
    config = config.model_dump() if hasattr(config, "model_dump") else config
    frame, screen = config["frame"], config["screen"]
    layout = frame.get("layout", "auto_fit")
    if layout not in ("auto_fit", "fill", "manual"):
        raise ValueError("Unknown layout")
    pw, ph = poster_size
    if pw <= 0 or ph <= 0:
        raise ValueError("Poster dimensions must be positive")
    position, forward, right, up, tx, ty = camera_basis(config)
    mask = visible_screen_mask(config, resolution)
    yy, xx = np.where(mask)
    if not len(xx):
        raise ValueError("Screen has no front-visible pixels")
    bbox = (
        np.array([xx.min(), yy.min(), xx.max() + 1, yy.max() + 1]) * 2 / resolution - 1
    )
    d = dimensions(screen)
    points, normals = surface_grid(np.linspace(0, d["length"], 1025), 0, screen)
    valid = visible_points(points, normals, position, screen)
    depths = (points - position) @ forward
    valid &= depths > 0.01
    if not valid.any():
        raise ValueError("Screen lies behind camera")
    static_depth = float(np.median(depths[valid]))
    depth = static_depth + frame.get("virtual_depth_m", 0)
    if depth <= 0.01:
        raise ValueError("Composition plane lies behind camera")
    image_ratio = pw / ph
    ratio = (
        image_ratio if layout == "auto_fit" else frame["width_m"] / frame["height_m"]
    )
    opening = _rectangle(mask, ratio * ty / tx)
    scale = frame.get("scale", 0.9)
    if not 0 < scale <= 1:
        raise ValueError("Composition scale must be in (0,1]")
    mid = (opening[:2] + opening[2:]) / 2
    half = (opening[2:] - opening[:2]) * scale / 2
    opening = np.r_[mid - half, mid + half]
    stage_mid = mid.copy()
    stage_center = (
        position
        + forward * static_depth
        + right * mid[0] * static_depth * tx
        + up * mid[1] * static_depth * ty
    )
    stage_width, stage_height = (
        (opening[2:] - opening[:2]) * static_depth * np.array([tx, ty])
    )
    center = (
        position
        + forward * depth
        + right * mid[0] * depth * tx
        + up * mid[1] * depth * ty
    )
    width, height = (opening[2:] - opening[:2]) * depth * np.array([tx, ty])
    offsets = np.asarray(frame.get("position", [0, 0, 0]), dtype=float)
    if layout == "manual":
        center = offsets
        width, height = frame["width_m"], frame["height_m"]
        depth = float((center - position) @ forward)
        if depth <= 0.01:
            raise ValueError("Manual frame lies behind camera")
    else:
        center = center + right * offsets[0] + up * offsets[1] + forward * offsets[2]
        depth = float((center - position) @ forward)
        if depth <= 0.01:
            raise ValueError("Offset frame lies behind camera")
    mid, _ = project_points(center, config)
    half = np.array([width / (depth * tx), height / (depth * ty)]) / 2
    opening = np.r_[mid - half, mid + half]
    uv = [0.0, 0.0, 1.0, 1.0]
    if layout == "fill":
        if image_ratio > ratio:
            span = ratio / image_ratio
            uv = [(1 - span) / 2, 0.0, (1 + span) / 2, 1.0]
        else:
            span = image_ratio / ratio
            uv = [0.0, (1 - span) / 2, 1.0, (1 + span) / 2]
    border = frame.get("border_m", 0.18)
    stage_outer_width = max(
        stage_width + 2 * border,
        2 * max(abs(bbox[[0, 2]] - stage_mid[0])) * static_depth * tx,
    )
    stage_outer_height = max(
        stage_height + 2 * border,
        2 * max(abs(bbox[[1, 3]] - stage_mid[1])) * static_depth * ty,
    )
    delta = center - stage_center
    main_frame_offset = [
        float(delta @ right),
        float(delta @ up),
        float(delta @ (-forward)),
    ]
    # The architecture stays on stage_center. Account for manual world poses and
    # auto forward offsets as well as virtual depth before building Blender meshes.
    effective_border = min(border, min(width, height) * 0.12)
    rear_extent = max(
        frame.get("depth_m", 0.65) * 0.8,
        effective_border * 0.7,
        0.36 if frame.get("template") == "float" else 0.0,
    )
    inward_extent = -main_frame_offset[2] + rear_extent
    if (
        frame.get("template", "cinema")
        not in (
            "aurora_float",
            "soft_depth",
            "glass_layers",
            "embedded_cube",
            "embedded_cube_architecture",
            "autumn_resonance_cube",
            "autumn_symphony",
            "autumn_amber_gallery",
        )
        and inward_extent >= frame.get("portal_depth_m", 3) - 0.1
    ):
        raise ValueError("画框或背部结构进入空间后墙；请减少纵深/向内偏移，或增大空间深度")
    # Portal surround extends to visible-screen bounds in this same plane.
    outer_width = max(
        width + 2 * border, 2 * max(abs(bbox[[0, 2]] - mid[0])) * depth * tx
    )
    outer_height = max(
        height + 2 * border, 2 * max(abs(bbox[[1, 3]] - mid[1])) * depth * ty
    )
    x0, y0, x1, y1 = opening
    ix0, iy0 = np.floor((opening[:2] + 1) * resolution / 2).astype(int)
    ix1, iy1 = np.ceil((opening[2:] + 1) * resolution / 2).astype(int)
    safe = ix0 >= 0 and iy0 >= 0 and ix1 <= resolution and iy1 <= resolution
    safe = bool(safe and mask[iy0:iy1, ix0:ix1].all())
    return dict(
        layout=layout,
        center=center.tolist(),
        right=right.tolist(),
        up=up.tolist(),
        normal=(-forward).tolist(),
        stage_center=stage_center.tolist(),
        static_depth=static_depth,
        main_frame_offset=main_frame_offset,
        stage_width=float(stage_width),
        stage_height=float(stage_height),
        stage_outer_width=float(stage_outer_width),
        stage_outer_height=float(stage_outer_height),
        width=float(width),
        height=float(height),
        width_m=float(width),
        height_m=float(height),
        depth=depth,
        outer_width=float(outer_width),
        outer_height=float(outer_height),
        opening_ndc=opening.tolist(),
        screen_bbox_ndc=bbox.tolist(),
        uv_crop=uv,
        metrics=dict(
            opening_safe=safe,
            projected_width_fraction=float((x1 - x0) / (bbox[2] - bbox[0])),
            visible_mask_pixels=int(mask.sum()),
            mask_resolution=resolution,
        ),
    )
