# BUPT Anamorphic Frame Studio

为北京邮电大学三段式弧形转角 LED 大屏制作裸眼 3D 图片内容。上传一张海报，选择空间模板，工作室会在本机渲染三维场景，并生成 **4368 × 3120** 播放图和预设观看点的模拟图。默认按原图比例构图，标题、Logo 和其他内容随原图一起保留。

![计启秋韵 · 琥珀回廊的北邮转角屏模拟效果](examples/amber-gallery/preview.jpg)

[播放图示例](examples/amber-gallery/final/atlas.png) · [全尺寸回贴模拟](examples/amber-gallery/final/simulation.png) · [渲染与验证记录](examples/amber-gallery/README.md)

## 本地启动

准备 Python 3.9+、Node.js 20（20.19 起）或 22.12+、Blender 和 FFmpeg（含 `ffprobe`）。项目在 macOS Apple Silicon 上使用 **Blender 3.4.1** 的 Eevee 和 Cycles CPU 完成验证。较新的 Blender 版本尚未完成整套兼容验证。

```sh
git clone https://github.com/Win-gun/bupt-anamorphic-frame-studio.git
cd bupt-anamorphic-frame-studio
./scripts/setup.sh
./scripts/start.sh
```

打开 [本地工作室](http://127.0.0.1:8000/)，上传图片并选择空间样式。先用「快速预览」检查构图，再用「高质量预览」检查光影，最后点「正式导出」生成全尺寸画布。启动脚本仅监听本机，支持通过 `PORT` 更改端口。服务优先使用 `BLENDER_BIN` 指定的 Blender，其次查找命令行上的 `blender`，最后使用 macOS 的默认安装路径。

## LED 展开图如何生成

1. **建屏。** 按左平面 **2704 列**、中间圆弧 **416 列**、右平面 **1248 列**建立连续的三维屏幕，三段均高 **3120 行**。展开图的横坐标对应沿屏幕表面的累计距离。
2. **构图和渲染。** 根据预设观察点算出可见屏幕区域，在画面中按原图比例放置海报。Blender 从同一机位渲染海报、立体结构和照明，输出目标画面。
3. **逐像素反向取样。** 把播放画布的每个像素中心转换成屏幕上的三维点，再透视投影回目标画面，检查朝向、遮挡和图像边界后，用相邻四点取样得到 RGB。三段使用同一套计算。
4. **回贴验证。** 把播放图贴回三维屏幕，从原机位重新渲染，在有效屏幕区域内比较结果与目标画面。

| 输出文件 | 用途 |
| --- | --- |
| `atlas.png` | LED 播放画布。平铺查看时呈现为适配三段屏幕的预变形图像。 |
| `scene.png` | Blender 目标画面，用于检查构图和光影。 |
| `simulation.png` | 展开图贴回三段屏幕后，从预设机位看到的画面。 |
| `calibration.png`、`report.json` | 分段校准网格和回贴验证结果。 |

**屏幕像素规格已确定。** 外凸方向有现场照片支持，P3、90° 转角和观察点采用参考值，仍待现场实测校准。 [照片与模型核查](examples/screen-photo-fit/README.md) · [反向投影实现](studio/blender_render.py#L155)

## 场景示例

[Aurora Float · 极光悬浮](examples/v3/aurora-preview.png) · [三种配色](examples/v3/palette-contact-sheet.png) · [四种空间模板](examples/v3/architecture-contact-sheet.png) · [V2/V3 对比](examples/v3/v2-v3-comparison.png) · [验收报告](examples/v3/acceptance.md)

## 秋韵 · 琥珀回廊

为「计启秋韵」新增的独立样式，使用紫色陶釉曲面、缎面铜饰和带凸起叶脉的枫叶。海报约占照片参考机位下可见屏宽的 87%。界面可以分别选择琥珀回廊和枫光奏鸣。[正式渲染、工程和对比](examples/amber-gallery/README.md)

## 新增：Autumn Symphony · 秋韵枫光奏鸣

针对「计启秋韵」原图定制的独立三维样式 `autumn_symphony`：深紫弯折建筑翼面、宽幅悬浮曲面、铜色旋律曲带，以及九片带真实叶脉的曲面枫叶。海报在最佳观察点下放大，原始纹理、文字、Logo完整保留。

![灰舱与枫光奏鸣 · 同一观察点真实回贴对比](examples/autumn-symphony/before-after.png)

[完整场景](examples/autumn-symphony/final/scene.png) · [最佳点模拟](examples/autumn-symphony/final/simulation.png) · [4368×3120 LED画布](examples/autumn-symphony/final/atlas.png) · [可编辑Blender](examples/autumn-symphony/final/scene.blend) · [枫叶建模细节](examples/autumn-symphony/maple-detail.png) · [验收报告](examples/autumn-symphony/acceptance.md)

界面选择“秋韵 · 枫光奏鸣”，或导入 [`configs/autumn-symphony.json`](configs/autumn-symphony.json)。支持图片大小、光照强度、柔和度与环境光；高质量使用Cycles，快速构图使用Eevee。此前全部样式和Aurora默认保留。

## 新增：Autumn Resonance Cube · 秋韵光影舱

独立专属美术预设 `autumn_resonance_cube`，复用楼体开孔、五面实体内舱和北邮曲面映射。新增共享空间坐标下的矿物微水泥节点材质、宽柔渐变、六组真实 Area 灯及后壁软影；原图保持完整 UV 和色彩。Aurora 仍为启动默认，全部旧模板保留。

![三种秋韵建筑配色 · 真实 Cycles 渲染](examples/autumn-resonance/variants-comparison.png)

[最终完整场景](examples/autumn-resonance/final/scene.png) · [4368×3120 LED展开](examples/autumn-resonance/final/atlas.png) · [最佳点模拟](examples/autumn-resonance/final/simulation.png) · [可编辑 Blender](examples/autumn-resonance/final/scene.blend) · [优化前后对比](examples/autumn-resonance/before-after.png) · [验收报告](examples/autumn-resonance/acceptance.md)

界面选择“秋韵光影舱”，可调整 Balanced/Warm/Cool、纹理强度（mm）、光照/柔和度、舱内位置、阴影、环境及边缘高光。专业参数含渐变、真实倒角和引擎。`auto` 使用 Eevee 进行静态快速构图，使用 Cycles 进行高质量静态及秋韵动态；最终美术参考使用实际验证的 **Blender 3.4.1 Cycles CPU**。较新版本尚未完成整套兼容验收。

[7.5秒真实三维场景动画](examples/autumn-resonance/motion-preview/target.mp4) 与 [LED播放动画](examples/autumn-resonance/motion-preview/led.mp4) 均为546×390、24fps、180帧预览。每帧真实渲染/反投影/实体安全检查，7个检查点另做独立物理屏回贴；最后60帧位置与灯光固定。场景视图视频不冒充独立回贴模拟。

独立配置见 [`configs/autumn-resonance.json`](configs/autumn-resonance.json)。可通过界面“导入 JSON”加载，也可从仓库根目录运行：

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 \
  --python studio/blender_render.py -- \
  --config configs/autumn-resonance.json \
  --poster examples/v2/jiqi-qiuyun/original.png \
  --output outputs/autumn-local
```

此配置输出默认全尺寸静态；本轮128采样正式参考的完整参数另存于 `examples/autumn-resonance/final-config.json`。墙厚0.32m、舱深3m、海报开口后2.1m及P3/90°等均为未校准演示参数。材质、灯光与动画证据位于独立目录，旧版本验收未覆盖。

## 新增：Embedded Cube · 楼体内嵌立方体

保留全部已有样式，新增独立模板`embedded_cube_architecture`。连续建筑墙体中挖出真实展示舱，具有墙厚、顶/底/左右壁和后壁，无传统边框、玻璃盖或舞台底座。默认推荐B舱内悬浮，也可选择A后壁展示。

![后壁展示与舱内悬浮真实对比](examples/embedded-cube/layout-comparison.png)

[方案B全尺寸展开](examples/embedded-cube/floating-full/atlas.png) · [最佳点模拟](examples/embedded-cube/floating-full/simulation.png) · [可编辑Blender](examples/embedded-cube/floating-full/scene.blend) · [方案A输出](examples/embedded-cube/back-wall-full/) · [验收与五面可见性证据](examples/embedded-cube/acceptance.md)

界面提供空间深度、墙厚、海报占用和A/B布局；专业模式可调开口占用与舱内位置。建筑固定灰紫/雾蓝/暖灰材质，隐藏不适用的Aurora渐变控件。全局默认风格不变，旧轻型内嵌版本仍可选择。

## 新视觉系统

| 风格 | 实际空间结构 |
|---|---|
| **Aurora Float · 极光悬浮**（默认） | 无传统外框的薄面板，连续弧形渐变后景，宽软真实投影 |
| Soft Depth · 柔光纵深 | 单一连续曲面构成的浅凹空间，平滑侧面/上下转折 |
| Glass Layers · 轻透叠层 | 两片错位磨砂薄板位于海报后方，原海报不覆玻璃 |
| Embedded Cube V3 · 轻型内嵌（保留） | 原有轻型挖空结构，继续保留 |
| **Embedded Cube · 楼体内嵌立方体（新增）** | 连续建筑立面的厚墙切口与五面内舱，支持后壁展示/舱内悬浮 |

V2 的 Cinema、悬浮画框、玻璃展柜完整保留在 **Legacy** 中，原实现单独归档为 `studio/legacy_scene_design.py`，并有实际回归。V1/V2 样例仍在原 `examples/` 目录，V2 使用说明见 [历史说明](docs/v2-readme.md)。

三种默认低饱和配色：极光烟紫、灰蓝晨雾、暖粉薄雾。颜色只用于三维容器；不会降低用户图片本身的饱和度。

渐变由 Blender Shader Nodes 附着在真实曲面上计算，支持线性、径向、双光场、多色、方向、色标位置、亮度、饱和度和微量噪声。薄板厚度、倒角、悬浮间距和材质边缘反射可调。反射参数作用于薄板侧边，不给正文叠玻璃反光。

光照强度、柔和度、环境亮度、阴影柔和度均控制真实区域光及场景；背景辉光控制曲面低强度自发光，避免全局光晕覆盖原图。实际对照渲染证明所有参数有效，海报区域颜色保持不变，见 [控制检查](examples/v3/control-probe/report.json)。

## 创作与专业模式

创作模式默认呈现：上传、风格、渐变配色、悬浮深度、面板/光照、画面大小、预览及导出。普通用户无需输入三维坐标。

专业模式提供 LED 几何、凹凸方向、安装朝向、点间距、相机/FOV、UV 诊断、完整渐变色标、分辨率/视频编码和数值报告。Legacy 的传统画框尺寸与金属材质只在对应样式中出现。

Auto Fit 自动读取原始比例并在观察相机的实际可见屏幕轮廓中构图；Manual 完整 contain 放置，Fill 明确允许中心裁切。海报原始矩形四角完整保留，圆角仅用于微小外扩的薄背板。

支持保存/恢复配置、导入导出 JSON、重置北邮默认值。已保存的旧配置仍可恢复为其 Legacy 风格。结果使用任务提交时的配置快照。

## 预览与动画

- **完整三维场景**：展示虚拟空间的真实渲染。
- **最佳观看模拟**：把最终 LED 展开图重新贴回物理屏渲染；可选择屏外预览底色。
- **有效 LED 裁切**：实际屏幕遮罩的透明图，仅做包围盒裁切，绝不改变播放画布。
- **LED 展开**：实际三段连续 UV 画布。
- **交互 3D**：载入 Blender 导出的同源 GLB，默认正面三分之四视角，支持旋转、缩放和重置。程序化节点和完整灯光保存在 Blender；GLB 用于几何检查，其材质回退不等同于最终照明。
- **照片合成**：提供场地照片时，可手动调位置、大小和透明度；明确标注未现场校准。该功能的浏览器测试使用合成测试图。

快速预览使用 1/8 的线性分辨率，高质量预览使用 1/2，正式输出使用全尺寸。V3 动态缓慢向前、轻微悬浮后稳定停留，可选柔光移动；旧 Legacy 保持原有前进—停留—返回行为。每帧都是真实三维对象和灯光渲染后再执行曲面反投影，未使用二维缩放。

渲染界面显示实际阶段、分块/采样或已完成动画帧数与任务用时；百分比为阶段加权估算。全尺寸 Cycles CPU 可能需要数分钟，不能仅因数秒未更新采样就判断卡死。日常构图先用快速预览。

动态限6–360帧。已交付真实海报2秒/12fps低分辨率视频，以及端点/中间/结束的独立物理屏回贴检查。播放 PNG 按 sRGB 使用；MP4 采用 BT.709 矩阵、有限范围和显式 sRGB 传递标记，实际控制器仍需现场检查颜色响应。

## 北邮唯一默认预设

默认值继续由 [`configs/bupt-curved-led.json`](configs/bupt-curved-led.json) 管理，前端经 API 获取，示例配置是校验过的快照。

| 左平面 | 中间真实弧面 | 右平面 | 正式展开 |
|---:|---:|---:|---:|
| 2704×3120 | 416×3120 | 1248×3120 | **4368×3120** |

预览比例只改变渲染分辨率，不改变物理几何、UV、画布比例或像素次序。仍保留凹/凸、安装 yaw、自遮挡、表面弧长 UV 与独立数值验证。

**默认预设采用现场照片支持的外凸转角和低机位。** P3、90° 和机位用于照片参考，现场尺寸及最佳观看位置仍待实测。旧画布需要重新生成。[照片核查与回贴对比](examples/screen-photo-fit/README.md)

## 测试与渲染

```sh
.venv/bin/python -m pytest -q
RUN_BLENDER_TESTS=1 .venv/bin/python -m pytest -q
BASE_URL=http://127.0.0.1:8000 npm --prefix frontend run test:ui
.venv/bin/python scripts/v3_api_acceptance.py
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 --python scripts/v3_control_probe.py
```

独立正式输出：

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 \
  --python studio/blender_render.py -- \
  --config configs/bupt-demo.json --poster examples/v2/jiqi-qiuyun/original.png --output outputs/manual
```

真实素材为4535×2551「计启秋韵」原海报。另有浅色/深色、横版/竖版测试。数值一致性、结构检查、实际视觉复核分别记录；任何自动测试通过都不能代替用户审美确认。

## 交付入口

- [Aurora 正式输出](examples/v3/aurora-full/)：4368×3120展开、目标场景、最佳点模拟、有效区透明图、差异/遮罩、`.blend`、GLB与报告。
- [三种配色实测](examples/v3/palette-contact-sheet.png)：对应目录为 `aurora/`、`cool_mist/`、`warm_haze/`。
- [四种模板对比](examples/v3/architecture-contact-sheet.png)：`soft_depth/`、`glass_layers/`、`embedded_cube/` 含实际图片、配置与报告，可据配置重建可编辑场景。
- [动态预览](examples/v3/motion-api/led.mp4)与[逐帧联系图](examples/v3/motion-api/mapped-motion-frames.png)；与视频对应的可编辑动画工程为 `motion-api/scene.blend`；另有 `aurora-motion/` 独立关键帧落盘回归。
- [V2/V3 同海报对比](examples/v3/v2-v3-comparison.png)：使用相同屏外底色，避免黑色视场干扰评价。
- [验收报告](examples/v3/acceptance.md)、[独立视觉报告](examples/v3/visual-review.md)、[设计与已知边界](docs/v3-design-brief.md)。
