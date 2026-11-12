"""Versioned scene dispatch. Legacy geometry stays isolated and unchanged."""
try:
    from .legacy_scene_design import FRAME_PROFILE, PRESETS, artwork_size, ring_mesh
except ImportError:
    from legacy_scene_design import FRAME_PROFILE, PRESETS, artwork_size, ring_mesh

LEGACY_TEMPLATES = frozenset(("cinema", "deep", "float", "glass"))
AURORA_TEMPLATES = frozenset(
    ("aurora_float", "soft_depth", "glass_layers", "embedded_cube")
)


def build_exhibition(config, poster, composition, textured_material):
    template = config["frame"].get("template", "aurora_float")
    if template in LEGACY_TEMPLATES:
        try:
            from .legacy_scene_design import build_exhibition as build
        except ImportError:
            from legacy_scene_design import build_exhibition as build
    elif template == "autumn_amber_gallery":
        from studio.amber_gallery import build_exhibition as build
    elif template == "autumn_symphony":
        try:
            from .symphony_scene import build_exhibition as build
        except ImportError:
            from symphony_scene import build_exhibition as build
    elif template == "autumn_resonance_cube":
        try:
            from .autumn_resonance import build_exhibition as build
        except ImportError:
            from autumn_resonance import build_exhibition as build
    elif template == "embedded_cube_architecture":
        try:
            from .embedded_cube_scene import build_exhibition as build
        except ImportError:
            from embedded_cube_scene import build_exhibition as build
    elif template in AURORA_TEMPLATES:
        try:
            from .aurora_scene import build_exhibition as build
        except ImportError:
            from aurora_scene import build_exhibition as build
    else:
        raise ValueError("Unknown scene template: " + template)
    return build(config, poster, composition, textured_material)
