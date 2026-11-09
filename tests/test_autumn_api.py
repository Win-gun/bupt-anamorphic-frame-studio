"""Declared art controls survive strict validation and local save/reload."""
import json
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from studio.config import Config, PRESET
from studio import server


def test_autumn_preserves_default_and_old_snapshots():
    c = Config()
    assert c.frame.template == "aurora_float"
    assert c.cube.poster_depth_fraction == 0.62
    assert c.autumn.model_dump() == PRESET["autumn"]
    for name in ("bupt-demo.json", "quick-test.json"):
        old = json.loads((server.ROOT / "configs" / name).read_text())
        old.pop("autumn", None)
        assert Config.model_validate(old).autumn == c.autumn
    preset = Config.model_validate_json(
        (server.ROOT / "configs/autumn-resonance.json").read_text()
    )
    assert preset.frame.template == "autumn_resonance_cube"
    assert preset.screen == c.screen and preset.camera == c.camera
    assert preset.autumn.poster_depth_fraction == 0.70


@pytest.mark.parametrize(
    "key,value",
    [
        ("variant", "neon"),
        ("engine", "UNKNOWN"),
        ("texture_strength_m", 0.001),
        ("softness", 0),
        ("shadow_strength", 1.1),
        ("edge_highlight", float("nan")),
        ("poster_depth_fraction", 0.95),
        ("opening_bevel_m", 0.2),
        ("undeclared_parameter", 1),
    ],
)
def test_autumn_strict_rejects_invalid_values(key, value):
    data = Config().model_dump()
    data["autumn"][key] = value
    with pytest.raises(ValidationError):
        Config.model_validate(data)


def test_autumn_api_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "SETTINGS_PATH", tmp_path / "settings.json")
    client = TestClient(server.app)
    data = Config().model_dump()
    data["frame"]["template"] = "autumn_resonance_cube"
    data["autumn"].update(
        variant="warm", texture_strength_m=0.00015, shadow_strength=0.5
    )
    assert client.post("/api/config/validate", json=data).json() == data
    assert client.put("/api/settings", json=data).json() == data
    assert client.get("/api/settings").json() == data
    assert (
        client.post("/api/settings/reset").json()["frame"]["template"] == "aurora_float"
    )
