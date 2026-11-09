# BUPT Anamorphic Frame Studio

本地海报 → Blender 厚度画框 → 连续平面/圆弧/平面投影 → LED 展开画布 → 观察点回贴验证。

**默认未校准。** 2704 + 416 + 1248 × 3120 是播放像素规格，不是米。P3、90° 是演示假设，不能作为现场交付依据。必须实测像素间距、转角/半径、观察点及屏幕朝向。

## 安装与启动（macOS Apple Silicon）

需要 Python 3.9+、Node.js 20.19+、Blender 3.4+、FFmpeg/ffprobe。已在本机 Blender 3.4.1、Python 3.9.6、Node 20.20.2 下实测；其他 Blender 主版本需重新运行验收。

```sh
git clone https://github.com/Win-gun/bupt-anamorphic-frame-studio.git
cd bupt-anamorphic-frame-studio
./scripts/setup.sh
./scripts/start.sh
```

打开 http://127.0.0.1:8000 。首次构建后，前后端由一个本地服务提供。开发前端可运行 `npm --prefix frontend run dev`，由 Vite 代理 API。只监听 loopback；不要直接暴露到公网。

Blender 默认路径 `/Applications/Blender.app/Contents/MacOS/Blender`，也支持 `BLENDER_BIN=/绝对路径/Blender ./scripts/start.sh`。Node 26 在此主机缺少动态库；安装脚本优先使用已安装的 `/opt/homebrew/opt/node@20/bin`，不修改系统链接。

## 使用

1. 上传 PNG/JPEG/WebP 海报，EXIF 朝向归一化、透明区域以白底合成；不使用生成式 AI，不裁剪、不拉伸海报。
2. 选择深邃画框、悬浮画框或玻璃展柜。设置画框外尺寸、边框、深度、位置、颜色。海报按原比例 contain 到内部开口。
3. 输入屏幕与相机参数。圆弧半径留空时按弧长和角度求解；指定半径时必须与像素间距/416 像素弧长一致（相对容差 0.0001%，几何使用弧长/角度的规范半径）。
4. 以低分辨率生成预览；检查原海报、目标 3D 场景、LED 展开、现场回贴四种视图及验证报告。
5. 将输出比例设为 1，导出 **4368 × 3120 PNG**。可选 MP4 是展开画布的定格视频，不包含角色或画框运动；FFmpeg 编码后以 ffprobe 检查。未校准标记留在界面和报告，避免污染播放素材。

更改观察相机后必须重新生成展开图。单一观察点的错觉不保证其他位置成立。参数在提交时快照保存为每个任务的 config.json。

## 数学与物理模型

单位为米，Z 向上。屏幕横向采用真实表面弧长 `s`，竖向采用 `z`。设左屏宽 `L=2704*p`、弧长 `A=416*p`、右屏宽 `B=1248*p`，`p=pitch_mm/1000`，`θ=angle_deg*π/180`，`R=A/θ`。

局部横截面：

- 左屏：`x=s-L, y=0`（`0≤s≤L`）。
- 圆弧：`t=(s-L)/R; x=R*sin(t), y=R*(cos(t)-1)`。
- 右屏：`q=s-L-A; x=R*sin(θ)+q*cos(θ), y=R*(cos(θ)-1)-q*sin(θ)`。

两处接缝位置与一阶切向连续。整体 X 居中。UV 为 `u=s/(L+A+B)`、`v=(z+H/2)/H`，其中 `H=3120*p`。几何使用细分圆柱曲面网格，像素采样使用解析表面而非把视频分三段裁切。世界坐标与网格细分规则以 `studio/geometry.py` 为准。

投影链路：Blender 渲染虚拟画框目标图 → 遍历展开画布像素中心，求真实三维表面点 → 投影到固定相机 → 双线性纹理采样 → 输出展开 → 将输出 PNG 作为发光纹理贴回真实 LED 网格，由 Blender 再渲染。背面与不可见表面不应作为可用显示区。

回贴验证使用独立的实际屏幕遮罩，只比较屏幕有效覆盖区域；同时输出边界与内区的误差、差异图及阈值结果。阈值和实际方法请查看每次任务的 report.json。有限纹理分辨率、网格近似、抗锯齿和掠射角会引入误差；这些指标验证数字投影链路，不能替代现场光学标定。

## 测试与证据

```sh
.venv/bin/python scripts/check_environment.py
.venv/bin/python -m pytest -q
RUN_BLENDER_TESTS=1 .venv/bin/python -m pytest -q
.venv/bin/python scripts/smoke.py --scale 0.125
.venv/bin/python scripts/smoke.py --scale 1 --video
```

后两条实际启动 Blender，不是 mock；任务 ID、渲染日志、所有图片、打包 .blend、验证报告均位于 `outputs/<任务ID>/`。全分辨率较慢，任务串行执行。服务重启后保留任务结果，中断任务标为失败，不自动重复执行。

独立运行 Blender：

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 \
  --python studio/blender_render.py -- \
  --config configs/bupt-demo.json --poster examples/poster.png --output outputs/manual
```

`examples/poster.png` 是通过 Pillow 排版的测试海报，文字和几何图形均为原始光栅素材。`examples/environment.json` 是实测环境记录。浏览器回归需本机 Chrome 与正在运行的服务，执行 `npm --prefix frontend run test:ui`。测试结果见 `examples/acceptance.md`。

## 目录

- `studio/`：验证模型、API、串行任务调度、Blender 几何/投影/回贴。
- `frontend/`：React + TypeScript 控制台。
- `configs/`：演示与快速测试 JSON。
- `scripts/`：安装、启动、环境检查、测试海报和端到端验收。
- `tests/`：参数、上传、几何与失败路径测试。
- `outputs/`：每个任务的输入快照、可播放素材、日志与验证证据。

## 第一阶段边界

提供三个基础材质模板、静态画框与可选定格视频。无 AI 抠图、生成式重绘、角色动画、自动测量或现场控制器推流。预览为提交后的准实时任务渲染。现场物理校准、LED 亮度/色彩/控制器映射仍需实测；`calibrated` 只记录操作者声明，不代表软件独立验证了现场。
