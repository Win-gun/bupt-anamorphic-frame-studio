"""Deterministic, Blender-independent Autumn Resonance motion and solid safety.

Frame i samples i/fps; 180 frames at 24 fps play for 7.5 seconds. The final
60 samples are identical. Safety covers the backing's 8 mm edge and 25 mm depth,
not only the visible image plane. Independent LED renders are separate checks.
"""
import math
import numpy as np
from studio.composition import project_points

DURATION = 7.5
FPS = 24
FRAME_COUNT = 180


def motion_state(time_s):
    t = max(0.0, min(DURATION, float(time_s)))
    light_phase = min(1.0, t / 1.5)
    smooth = lambda x: x * x * (3 - 2 * x)
    forward = 0.20 * smooth(max(0.0, min(1.0, (t - 1.5) / 2)))
    up = 0.05 * math.sin(math.pi * (t - 3.5) / 1.5) ** 2 if 3.5 < t < 5 else 0.0
    return dict(
        time_s=t,
        forward_m=forward,
        up_m=up,
        light_factor=0.55 + 0.45 * smooth(light_phase),
        stage=(
            "light_reveal"
            if t < 1.5
            else "forward"
            if t < 3.5
            else "breath"
            if t < 5
            else "stable_hold"
        ),
    )


def translation(state, composition):
    return (
        np.asarray(composition["normal"]) * state["forward_m"]
        + np.asarray(composition["up"]) * state["up_m"]
    )


def validate_geometry(config, composition, cavity, offset):
    """Conservative solid-envelope bounds in physical room and camera space."""
    right, up, normal = (
        np.asarray(composition[k], float) for k in ("right", "up", "normal")
    )
    center = np.asarray(composition["center"], float) + np.asarray(offset, float)
    width, height = (composition[k] for k in ("width", "height"))
    thickness = cavity.get("panel_total_envelope_m", 0.025)
    corners = np.array(
        [
            center + right * x + up * y + normal * z
            for x in (-width / 2 - 0.008, width / 2 + 0.008)
            for y in (-height / 2 - 0.008, height / 2 + 0.008)
            for z in (-thickness, 0)
        ]
    )
    ndc, depths = project_points(corners, config)
    opening = np.asarray(cavity["opening_ndc"], float)
    ndc_margin = float(min(np.min(ndc - opening[:2]), np.min(opening[2:] - ndc)))
    room = corners - np.asarray(cavity["front_plane_center"])
    inward = -(room @ normal)
    front = float(inward.min())
    rear = float(cavity["cavity_depth_m"] - inward.max())
    side_margin = float(
        min(
            cavity["opening_width_m"] / 2 - np.abs(room @ right).max(),
            cavity["opening_height_m"] / 2 - np.abs(room @ up).max(),
        )
    )
    passed = bool(
        np.isfinite(corners).all()
        and np.isfinite(ndc).all()
        and depths.min() > 0
        and ndc_margin >= 0
        and side_margin > 0
        and cavity["opening_safe"]
        and front > cavity["wall_thickness_m"] + 0.08
        and rear > 0
    )
    return dict(
        passed=passed,
        projected_corners_ndc=ndc.tolist(),
        camera_depth_min_m=float(depths.min()),
        opening_margin_ndc=ndc_margin,
        physical_side_clearance_m=side_margin,
        front_distance_m=front,
        front_safety_clearance_m=float(front - cavity["wall_thickness_m"] - 0.08),
        rear_clearance_m=rear,
        panel_envelope_m=thickness,
    )


def checkpoints(count=FRAME_COUNT):
    # Includes the peak of the temporary rise, start/finish of every stage and hold.
    return sorted(
        {
            0,
            *(
                min(count - 1, round(t / DURATION * count))
                for t in (1.5, 3.5, 4.25, 5, 6.25)
            ),
            count - 1,
        }
    )
