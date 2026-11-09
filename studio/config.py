"""Validated physical parameters. Pixel counts are never physical lengths."""
import math
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Screen(StrictModel):
    pixels: List[int] = Field(default_factory=lambda: [2704, 416, 1248], min_length=3, max_length=3)
    height_px: int = 3120
    pitch_mm: float = Field(3, ge=0.1, le=20)
    angle_deg: float = Field(90, ge=5, le=170)
    radius_m: Optional[float] = Field(None, gt=0, le=100)
    calibrated: bool = False

    @model_validator(mode='after')
    def check_geometry(self):
        if self.pixels != [2704, 416, 1248] or self.height_px != 3120:
            raise ValueError('本项目播放规格固定为 2704 + 416 + 1248 × 3120')
        derived = self.pixels[1] * self.pitch_mm / 1000 / math.radians(self.angle_deg)
        if self.radius_m is not None and not math.isclose(derived, self.radius_m, rel_tol=1e-6):
            raise ValueError('半径、弧长（416 × 像素间距）与角度不一致；请统一测量参数')
        return self

class Camera(StrictModel):
    position: List[float] = Field(default_factory=lambda: [-2, -10, 1], min_length=3, max_length=3)
    target: List[float] = Field(default_factory=lambda: [1.5, -0.5, 0], min_length=3, max_length=3)
    fov_deg: float = Field(65, ge=15, le=120)

    @model_validator(mode='after')
    def check_pose(self):
        if sum((a-b)**2 for a,b in zip(self.position,self.target)) < 0.01:
            raise ValueError('相机与目标点必须分离')
        if any(abs(v)>1000 for v in self.position+self.target):
            raise ValueError('坐标超出本地场景范围')
        return self

class Frame(StrictModel):
    template: Literal['deep', 'float', 'glass'] = 'deep'
    width_m: float = Field(5, ge=0.1, le=20)
    height_m: float = Field(6, ge=0.1, le=20)
    depth_m: float = Field(0.65, ge=0.02, le=5)
    border_m: float = Field(0.18, ge=0.01, le=2)
    position: List[float] = Field(default_factory=lambda: [2.5,0.7,0], min_length=3, max_length=3)
    color: str = Field('#234863', pattern=r'^#[0-9a-fA-F]{6}$')

    @model_validator(mode='after')
    def check_border(self):
        if self.border_m * 2.7 >= min(self.width_m, self.height_m):
            raise ValueError('边框厚度必须小于画框短边的一半')
        if any(abs(v)>100 for v in self.position):
            raise ValueError('画框坐标超出场景范围')
        return self

class Render(StrictModel):
    scale: float = Field(0.25, ge=0.0625, le=1)
    samples: int = Field(16, ge=1, le=256)
    video: bool = False
    duration: float = Field(3, ge=0.1, le=60)
    fps: int = Field(24, ge=1, le=60)

class Config(StrictModel):
    screen: Screen = Field(default_factory=Screen)
    camera: Camera = Field(default_factory=Camera)
    frame: Frame = Field(default_factory=Frame)
    render: Render = Field(default_factory=Render)
