import json
from pathlib import Path
import pytest
from PIL import Image
from pydantic import ValidationError
from studio.config import Config, PRESET
from studio.previews import make_previews


def test_v3_default_source_and_legacy_roundtrip():
    c = Config()
    assert c.frame.template == "aurora_float"
    for key in (
        "screen",
        "camera",
        "frame",
        "render",
        "appearance",
        "lighting",
        "panel",
    ):
        assert c.model_dump()[key] == PRESET[key]
    old = json.loads(
        (Path(__file__).parents[1] / "examples/v2/jiqi-qiuyun/config.json").read_text()
    )
    assert Config.model_validate(old).frame.template == "cinema"
    for template in ("cinema", "deep", "float", "glass"):
        data = c.model_dump()
        data["frame"]["template"] = template
        assert Config.model_validate(data).frame.template == template


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("appearance", "noise_strength", 0.2),
        ("appearance", "saturation", 2),
        ("lighting", "intensity", 0),
        ("lighting", "softness", 0),
        ("lighting", "glow", 1),
        ("panel", "thickness_m", 1),
        ("panel", "float_distance_m", 0),
        ("panel", "reflection", 1),
    ],
)
def test_v3_rejects_invalid_visual_parameters(section, key, value):
    data = Config().model_dump()
    data[section][key] = value
    with pytest.raises(ValidationError):
        Config.model_validate(data)


def test_gradient_custom_stops_and_palette_selection():
    data = Config().model_dump()
    data["appearance"]["palette"] = "cool_mist"
    assert (
        Config.model_validate(data).appearance.colors
        == PRESET["palettes"]["cool_mist"]["colors"]
    )
    data["appearance"].update(
        palette="custom", colors=["#223344", "#aabbcc"], stops=[0, 1]
    )
    assert Config.model_validate(data).appearance.colors == ["#223344", "#aabbcc"]
    data["appearance"]["stops"] = [1, 0]
    with pytest.raises(ValidationError):
        Config.model_validate(data)


def test_valid_led_crop_keeps_sampling_and_alpha(tmp_path):
    image = Image.new("RGB", (64, 48), "#9388a7")
    mask = Image.new("L", (64, 48), 0)
    from PIL import ImageDraw

    ImageDraw.Draw(mask).rectangle((8, 10, 49, 39), fill=255)
    image.save(tmp_path / "simulation.png")
    mask.save(tmp_path / "mask.png")
    image.save(tmp_path / "atlas.png")
    original = (tmp_path / "atlas.png").read_bytes()
    names = make_previews(tmp_path)
    assert Image.open(tmp_path / names["led_crop"]).size == (42, 30)
    rgba = Image.open(tmp_path / names["simulation_alpha"])
    assert rgba.getpixel((0, 0))[3] == 0 and rgba.getpixel((10, 12))[3] == 255
    assert (tmp_path / "atlas.png").read_bytes() == original
    assert json.loads((tmp_path / "preview.json").read_text())["crop_box"] == [
        8,
        10,
        50,
        40,
    ]


def test_embedded_cube_ignores_legacy_portal_depth():
    from studio.composition import solve_composition

    c = Config()
    c.frame.template = "embedded_cube"
    c.frame.portal_depth_m = 0.5
    data = Config.model_validate(c.model_dump())
    assert solve_composition(data, (1600, 900))["metrics"]["opening_safe"]
