"""Validated parameters; the BUPT JSON preset is the single default source."""
import json
import math
from pathlib import Path
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator

PRESET = json.loads(
    (Path(__file__).resolve().parents[1] / "configs/bupt-curved-led.json").read_text()
)
S, C, F, R = (PRESET[k] for k in ("screen", "camera", "frame", "render"))
A, L, P = (PRESET[k] for k in ("appearance", "lighting", "panel"))


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Screen(StrictModel):
    pixels: List[int] = Field(
        default_factory=lambda: list(S["pixels"]), min_length=3, max_length=3
    )
    height_px: int = S["height_px"]
    pitch_mm: float = Field(S["pitch_mm"], ge=0.1, le=20)
    angle_deg: float = Field(S["angle_deg"], ge=5, le=170)
    radius_m: Optional[float] = Field(None, gt=0, le=100)
    calibrated: bool = False
    curvature: Literal["concave", "convex"] = S["curvature"]
    yaw_deg: float = Field(S["yaw_deg"], ge=-180, le=180)

    @model_validator(mode="after")
    def check_geometry(self):
        if self.pixels != S["pixels"] or self.height_px != S["height_px"]:
            raise ValueError("播放像素规格必须保持北邮默认预设，不能按海报比例拉伸")
        derived = self.pixels[1] * self.pitch_mm / 1000 / math.radians(self.angle_deg)
        if self.radius_m is not None and not math.isclose(
            derived, self.radius_m, rel_tol=1e-6
        ):
            raise ValueError("半径、弧长（弧屏像素 × 像素间距）与角度不一致")
        return self


class Camera(StrictModel):
    position: List[float] = Field(
        default_factory=lambda: list(C["position"]), min_length=3, max_length=3
    )
    target: List[float] = Field(
        default_factory=lambda: list(C["target"]), min_length=3, max_length=3
    )
    fov_deg: float = Field(C["fov_deg"], ge=15, le=120)

    @model_validator(mode="after")
    def check_pose(self):
        delta = [a - b for a, b in zip(self.position, self.target)]
        if sum(v * v for v in delta) < 0.01:
            raise ValueError("相机与目标点必须分离")
        if delta[0] ** 2 + delta[1] ** 2 < 1e-8:
            raise ValueError("机位不能与世界竖直方向重合，请调整 X/Y")
        if any(abs(v) > 1000 for v in self.position + self.target):
            raise ValueError("坐标超出本地场景范围")
        return self


class Frame(StrictModel):
    template: Literal[
        "aurora_float",
        "soft_depth",
        "glass_layers",
        "embedded_cube",
        "embedded_cube_architecture",
        "autumn_resonance_cube",
        "cinema",
        "deep",
        "float",
        "glass",
    ] = F["template"]
    layout: Literal["auto_fit", "fill", "manual"] = F["layout"]
    material: Literal[
        "gold", "brushed_metal", "black_titanium", "lacquer", "glass", "emissive"
    ] = F["material"]
    scale: float = Field(F["scale"], ge=0.1, le=1)
    virtual_depth_m: float = Field(F["virtual_depth_m"], ge=-2, le=2)
    width_m: float = Field(F["width_m"], ge=0.1, le=20)
    height_m: float = Field(F["height_m"], ge=0.1, le=20)
    depth_m: float = Field(F["depth_m"], ge=0.02, le=5)
    border_m: float = Field(F["border_m"], ge=0.01, le=2)
    position: List[float] = Field(
        default_factory=lambda: list(F["position"]), min_length=3, max_length=3
    )
    color: str = Field(F["color"], pattern=r"^#[0-9a-fA-F]{6}$")
    edge_light: bool = F["edge_light"]
    portal_depth_m: float = Field(F["portal_depth_m"], ge=0.5, le=8)

    @model_validator(mode="after")
    def check_border(self):
        if self.border_m * 2.7 >= min(self.width_m, self.height_m):
            raise ValueError("边框宽度必须给海报保留有效开口")
        if any(abs(v) > 100 for v in self.position):
            raise ValueError("画框坐标超出场景范围")
        return self


class Render(StrictModel):
    scale: float = Field(R["scale"], ge=0.0625, le=1)
    quality: Literal["quick", "high"] = R["quality"]
    samples: int = Field(R["samples"], ge=1, le=256)
    video: bool = False
    animation: bool = False
    light_sweep: bool = False
    duration: float = Field(R["duration"], ge=0.1, le=60)
    fps: int = Field(R["fps"], ge=1, le=60)

    @model_validator(mode="after")
    def check_animation(self):
        if self.light_sweep:
            self.animation = True
        if self.animation:
            self.video = True
        if self.animation and self.duration * self.fps < 6:
            raise ValueError("三维动态至少需要6帧，请提高时长或帧率")
        if self.animation and self.duration * self.fps > 360:
            raise ValueError("本地动态测试限360帧，请降低时长或帧率")
        return self


class Appearance(StrictModel):
    palette: Literal["aurora", "cool_mist", "warm_haze", "custom"] = A["palette"]
    gradient_type: Literal["dual", "linear", "radial", "multi"] = A["gradient_type"]
    colors: List[str] = Field(
        default_factory=lambda: list(PRESET["appearance"]["colors"]),
        min_length=2,
        max_length=8,
    )
    stops: List[float] = Field(
        default_factory=lambda: list(PRESET["appearance"]["stops"]),
        min_length=2,
        max_length=8,
    )
    direction_deg: float = Field(A["direction_deg"], ge=-180, le=180)
    transition: float = Field(A["transition"], ge=0.05, le=0.95)
    brightness: float = Field(A["brightness"], ge=0.2, le=1.6)
    saturation: float = Field(A["saturation"], ge=0, le=1)
    noise_strength: float = Field(A["noise_strength"], ge=0, le=0.025)

    @model_validator(mode="after")
    def check_ramp(self):
        import re

        if self.palette != "custom":
            self.colors = list(PRESET["palettes"][self.palette]["colors"])
        if len(self.colors) != len(self.stops):
            raise ValueError("渐变颜色与位置数量必须一致")
        if any(
            re.fullmatch(r"#[0-9a-fA-F]{6}", color) is None for color in self.colors
        ):
            raise ValueError("渐变色必须为 #RRGGBB")
        if (
            self.stops[0] != 0
            or self.stops[-1] != 1
            or any(a >= b for a, b in zip(self.stops, self.stops[1:]))
        ):
            raise ValueError("渐变位置必须从0到1严格递增")
        return self


class Lighting(StrictModel):
    intensity: float = Field(L["intensity"], ge=0.1, le=3)
    softness: float = Field(L["softness"], ge=0.1, le=1)
    glow: float = Field(L["glow"], ge=0, le=0.2)
    ambient: float = Field(L["ambient"], ge=0.05, le=1.5)
    shadow_softness: float = Field(L["shadow_softness"], ge=0.1, le=1)


class Panel(StrictModel):
    thickness_m: float = Field(P["thickness_m"], ge=0.005, le=0.15)
    corner_radius_m: float = Field(P["corner_radius_m"], ge=0.001, le=0.15)
    float_distance_m: float = Field(P["float_distance_m"], ge=0.25, le=2)
    reflection: float = Field(P["reflection"], ge=0, le=0.15)


class Cube(StrictModel):
    layout: Literal["floating", "back_wall"] = PRESET["cube"]["layout"]
    depth_m: float = Field(PRESET["cube"]["depth_m"], ge=1, le=6)
    wall_thickness_m: float = Field(PRESET["cube"]["wall_thickness_m"], ge=0.12, le=0.8)
    opening_scale: float = Field(PRESET["cube"]["opening_scale"], ge=0.5, le=0.97)
    facade_margin_m: float = Field(PRESET["cube"]["facade_margin_m"], ge=0.5, le=4)
    poster_scale: float = Field(PRESET["cube"]["poster_scale"], ge=0.5, le=0.85)
    poster_depth_fraction: float = Field(
        PRESET["cube"]["poster_depth_fraction"], ge=0.35, le=0.8
    )

    @model_validator(mode="after")
    def check_cavity(self):
        if self.wall_thickness_m >= self.depth_m * 0.45:
            raise ValueError("墙体厚度必须小于空间深度的45%，保留真实舱内空间")
        if (
            self.layout == "floating"
            and self.depth_m * self.poster_depth_fraction
            <= self.wall_thickness_m + 0.08
        ):
            raise ValueError("悬浮海报需要位于墙体切口之后，请增加舱内位置比例或空间深度")
        return self


class Autumn(StrictModel):
    """Exclusive art controls; legacy presets never consume these values."""

    variant: Literal["balanced", "warm", "cool"] = PRESET["autumn"]["variant"]
    texture_strength_m: float = Field(
        PRESET["autumn"]["texture_strength_m"], ge=0, le=0.0004
    )
    gradient_strength: float = Field(
        PRESET["autumn"]["gradient_strength"], ge=0, le=0.6
    )
    light_intensity: float = Field(PRESET["autumn"]["light_intensity"], ge=0.1, le=3)
    softness: float = Field(PRESET["autumn"]["softness"], ge=0.1, le=1)
    shadow_strength: float = Field(PRESET["autumn"]["shadow_strength"], ge=0, le=1)
    ambient: float = Field(PRESET["autumn"]["ambient"], ge=0.05, le=1.5)
    edge_highlight: float = Field(PRESET["autumn"]["edge_highlight"], ge=0, le=1)
    poster_depth_fraction: float = Field(
        PRESET["autumn"]["poster_depth_fraction"], ge=0.35, le=0.8
    )
    opening_bevel_m: float = Field(
        PRESET["autumn"]["opening_bevel_m"], ge=0.005, le=0.05
    )
    panel_bevel_m: float = Field(PRESET["autumn"]["panel_bevel_m"], ge=0.001, le=0.006)
    engine: Literal["auto", "eevee", "cycles"] = PRESET["autumn"]["engine"]


class Config(StrictModel):
    screen: Screen = Field(default_factory=Screen)
    camera: Camera = Field(default_factory=Camera)
    frame: Frame = Field(default_factory=Frame)
    render: Render = Field(default_factory=Render)
    appearance: Appearance = Field(default_factory=Appearance)
    lighting: Lighting = Field(default_factory=Lighting)
    panel: Panel = Field(default_factory=Panel)
    cube: Cube = Field(default_factory=Cube)
    autumn: Autumn = Field(default_factory=Autumn)

    @model_validator(mode="after")
    def check_spatial_limits(self):
        if self.frame.template == "autumn_resonance_cube":
            distance = self.cube.depth_m * self.autumn.poster_depth_fraction
            if distance <= self.cube.wall_thickness_m + 0.08:
                raise ValueError("秋韵海报需位于墙体切口之后")
            if self.autumn.opening_bevel_m >= self.cube.wall_thickness_m / 2:
                raise ValueError("开口倒角须小于墙体厚度的一半")
        if self.frame.template in (
            "aurora_float",
            "soft_depth",
            "glass_layers",
            "embedded_cube",
            "embedded_cube_architecture",
            "autumn_resonance_cube",
        ):
            return self
        inward_offset = self.frame.position[2] if self.frame.layout != "manual" else 0
        backing = max(
            self.frame.depth_m * 0.8,
            self.frame.border_m * 0.7,
            0.36 if self.frame.template == "float" else 0,
        )
        if (
            self.frame.virtual_depth_m + inward_offset + backing
            >= self.frame.portal_depth_m - 0.1
        ):
            raise ValueError("画框及背部结构进入后墙，请减少虚拟纵深/框体厚度或增大空间深度")
        return self
