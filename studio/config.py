"""Validated parameters; the BUPT JSON preset is the single default source."""
import json
import math
from pathlib import Path
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator

PRESET = json.loads((Path(__file__).resolve().parents[1] / 'configs/bupt-curved-led.json').read_text())
S, C, F, R = (PRESET[k] for k in ('screen','camera','frame','render'))

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Screen(StrictModel):
    pixels: List[int] = Field(default_factory=lambda: list(S['pixels']), min_length=3, max_length=3)
    height_px: int = S['height_px']
    pitch_mm: float = Field(S['pitch_mm'], ge=0.1, le=20)
    angle_deg: float = Field(S['angle_deg'], ge=5, le=170)
    radius_m: Optional[float] = Field(None, gt=0, le=100)
    calibrated: bool = False
    curvature: Literal['concave','convex'] = S['curvature']
    yaw_deg: float = Field(S['yaw_deg'], ge=-180, le=180)

    @model_validator(mode='after')
    def check_geometry(self):
        if self.pixels != S['pixels'] or self.height_px != S['height_px']:
            raise ValueError('播放像素规格必须保持北邮默认预设，不能按海报比例拉伸')
        derived = self.pixels[1] * self.pitch_mm / 1000 / math.radians(self.angle_deg)
        if self.radius_m is not None and not math.isclose(derived, self.radius_m, rel_tol=1e-6):
            raise ValueError('半径、弧长（弧屏像素 × 像素间距）与角度不一致')
        return self

class Camera(StrictModel):
    position: List[float] = Field(default_factory=lambda: list(C['position']), min_length=3, max_length=3)
    target: List[float] = Field(default_factory=lambda: list(C['target']), min_length=3, max_length=3)
    fov_deg: float = Field(C['fov_deg'], ge=15, le=120)

    @model_validator(mode='after')
    def check_pose(self):
        delta = [a-b for a,b in zip(self.position,self.target)]
        if sum(v*v for v in delta) < 0.01:
            raise ValueError('相机与目标点必须分离')
        if delta[0]**2+delta[1]**2 < 1e-8:
            raise ValueError('机位不能与世界竖直方向重合，请调整 X/Y')
        if any(abs(v)>1000 for v in self.position+self.target):
            raise ValueError('坐标超出本地场景范围')
        return self

class Frame(StrictModel):
    template: Literal['cinema','deep','float','glass'] = F['template']
    layout: Literal['auto_fit','fill','manual'] = F['layout']
    material: Literal['gold','brushed_metal','black_titanium','lacquer','glass','emissive'] = F['material']
    scale: float = Field(F['scale'], ge=0.1, le=1)
    virtual_depth_m: float = Field(F['virtual_depth_m'], ge=-2, le=2)
    width_m: float = Field(F['width_m'], ge=0.1, le=20)
    height_m: float = Field(F['height_m'], ge=0.1, le=20)
    depth_m: float = Field(F['depth_m'], ge=0.02, le=5)
    border_m: float = Field(F['border_m'], ge=0.01, le=2)
    position: List[float] = Field(default_factory=lambda: list(F['position']), min_length=3, max_length=3)
    color: str = Field(F['color'], pattern=r'^#[0-9a-fA-F]{6}$')
    edge_light: bool = F['edge_light']
    portal_depth_m: float = Field(F['portal_depth_m'], ge=0.5, le=8)

    @model_validator(mode='after')
    def check_border(self):
        if self.border_m * 2.7 >= min(self.width_m,self.height_m):
            raise ValueError('边框宽度必须给海报保留有效开口')
        if any(abs(v)>100 for v in self.position):
            raise ValueError('画框坐标超出场景范围')
        return self

class Render(StrictModel):
    scale: float = Field(R['scale'], ge=0.0625, le=1)
    quality: Literal['quick','high'] = R['quality']
    samples: int = Field(R['samples'], ge=1, le=256)
    video: bool = False
    animation: bool = False
    light_sweep: bool = False
    duration: float = Field(R['duration'], ge=0.1, le=60)
    fps: int = Field(R['fps'], ge=1, le=60)

    @model_validator(mode='after')
    def check_animation(self):
        if self.light_sweep:
            self.animation = True
        if self.animation:
            self.video = True
        if self.animation and self.duration*self.fps<6:
            raise ValueError('三维动态至少需要6帧，请提高时长或帧率')
        if self.animation and self.duration*self.fps>360:
            raise ValueError('本地动态测试限360帧，请降低时长或帧率')
        return self

class Config(StrictModel):
    screen: Screen = Field(default_factory=Screen)
    camera: Camera = Field(default_factory=Camera)
    frame: Frame = Field(default_factory=Frame)
    render: Render = Field(default_factory=Render)

    @model_validator(mode='after')
    def check_spatial_limits(self):
        inward_offset = self.frame.position[2] if self.frame.layout != 'manual' else 0
        backing = max(self.frame.depth_m*.8,self.frame.border_m*.7,.36 if self.frame.template=='float' else 0)
        if self.frame.virtual_depth_m + inward_offset + backing >= self.frame.portal_depth_m-.1:
            raise ValueError('画框及背部结构进入后墙，请减少虚拟纵深/框体厚度或增大空间深度')
        return self
