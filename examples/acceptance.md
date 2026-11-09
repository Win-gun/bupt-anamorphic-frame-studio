# 实际验收记录 · 2026-11-09

环境：Apple Silicon arm64 / macOS / Blender 3.4.1 EEVEE / Python 3.9.6 / Node 20.20.2 / FFmpeg 8.1.1。完整版本记录见 environment.json。

## 验收结果

- 实际 Blender 回归及 Python/API 测试：见 test-results.txt，覆盖三模板最小深度、海报横/竖/方比例、5°/170°角度、几何接缝位置与导数、UV 比例、前背面、参数异常、上传及队列失败恢复。
- 前端 TypeScript + Vite 8.3.6 构建通过，npm audit 0 vulnerabilities（见 npm-audit.json）。
- Playwright + 本机 Chrome 实际完成上传 → 提交 → Blender 队列 → 结果图片加载；无 pageerror，390 px 窄屏无文档横向溢出（ui-check.json）。最终三栏桌面与窄屏截图为 ui-desktop.png、ui-mobile.png。首次 CUA 连接两次超时，随后以 Playwright 验证成功。
- 独立数学/材质风险审阅发现的背板遮挡、玻璃折射设置、无效投影坐标问题均已修复并回归。

## 全尺寸输出

实际任务：586c60addf0f481fb045ef4726d437f4。

- full-resolution/atlas.png：4368 × 3120，真实三维曲面相机投影。
- full-resolution/simulation.png：将该 atlas 回贴物理屏后的 Blender 独立渲染。
- full-resolution/scene.png：目标虚拟场景。
- full-resolution/calibration.png：弧长网格及两个橙色屏幕分界线。
- full-resolution/difference.png、mask.png、report.json：有效区差异、遮罩和数值报告。
- full-resolution/scene.blend：内嵌原海报及生成贴图的三维工程。
- full-resolution/led.mp4：4368 × 3120 H.264 / yuv420p / 24fps / 3s 定格展开视频，ffprobe 原始检查结果为 video-probe.json。

全有效区 MAE 0.00115635，内区 MAE 0.00113548，前景 MAE 0.00535883，前景覆盖率 1.0，内区 PSNR 40.9394 dB。误差基于归一化 sRGB；不代表现场色差或光学测量。

## 三模板

546 × 390 实际渲染，各模板 simulation.png 和 report.json 存于 templates/：

| 模板 | 全有效区 MAE | 前景 MAE | 前景覆盖率 |
|---|---:|---:|---:|
| deep | 0.003350 | 0.014398 | 100% |
| float | 0.003677 | 0.015086 | 100% |
| glass | 0.002495 | 0.010451 | 100% |

## 现场限制

全部样例使用未校准 P3、90° 演示参数，不能声称现场播放已验收。进入现场前须测量屏幕参数、观察点和镜头/色彩响应，重新投影并检查控制器实际像素映射。视频为定格画布，无动画。只验证过 Blender 3.4.1，其他大版本需重新运行验收。
