"""Read actual Blender logs/artifacts without blocking the API or inventing an ETA."""
import json
import re
import time
from pathlib import Path


def render_progress(directory, job, now=None):
    result = dict(job)
    if job["status"] != "running":
        return result
    directory = Path(directory)
    now = time.time() if now is None else now
    try:
        started = job.get("started_at", (directory / "config.json").stat().st_mtime)
        result["elapsed_seconds"] = max(0, round(now - started))
        config = json.loads((directory / "config.json").read_text())
        log = directory / "render.log"
        with log.open("rb") as stream:
            stream.seek(max(0, log.stat().st_size - 32768))
            tail = stream.read().decode("utf-8", errors="replace")
        result["last_activity_age_s"] = max(0, round(now - log.stat().st_mtime))
    except (OSError, ValueError):
        result.update(stage="启动 Blender", detail="正在准备场景")
        return result
    result["progress_kind"] = "stage_weighted"
    if job.get("progress", 0) >= 90:
        # The worker owns post-render/encoding stages; never regress to rendering.
        return result
    animation = config["render"].get("animation", False)
    done = len(list((directory / "frames").glob("led_*.png")))
    if animation and done:
        total = max(2, round(config["render"]["duration"] * config["render"]["fps"]))
        result.update(
            stage="三维动画与曲面映射",
            detail=f"已完成 {done}/{total} 帧",
            progress=min(89, 30 + 59 * done / total),
        )
        return result
    stages = [
        ("scene.png", "场景渲染", 10, 48),
        ("poster_mask.png", "海报覆盖验证", 48, 55),
        ("atlas.png", "三段曲面反向投影", 55, 63),
        ("simulation.png", "LED 回贴渲染", 63, 77),
        ("mask.png", "有效屏幕遮罩", 77, 85),
    ]
    missing = next((s for s in stages if not (directory / s[0]).exists()), None)
    if missing is None:
        result.update(stage="验证与工程保存", detail="计算误差并打包 Blender 工程", progress=89)
        return result
    filename, stage, start, end = missing
    # Ignore stats from the previous render when its image has already been saved.
    tail = re.split(r"(?:Saved:|已保存).*?\.png[^\n]*", tail)[-1]
    tiles = list(re.finditer(r"Rendered (\d+)/(\d+) Tiles, Sample (\d+)/(\d+)", tail))
    samples = list(re.finditer(r"Rendering\s+(\d+)\s*/\s*(\d+)\s+samples", tail))
    plain_samples = list(re.finditer(r"\bSample (\d+)/(\d+)", tail))
    fraction, detail = 0, "正在计算，请勿重复提交"
    if tiles:
        tile, total_tiles, sample, total_samples = map(int, tiles[-1].groups())
        fraction = min(1, tile / max(1, total_tiles))
        detail = f"分块 {tile}/{total_tiles} · 当前采样 {sample}/{total_samples}"
    elif samples or plain_samples:
        sample, total = map(int, (samples or plain_samples)[-1].groups())
        fraction = min(1, sample / max(1, total))
        detail = f"当前采样 {sample}/{total}"
    if animation:
        start, end = 10 + (start - 10) * 20 / 79, 10 + (end - 10) * 20 / 79
    result.update(
        stage=stage, detail=detail, progress=round(start + (end - start) * fraction, 1)
    )
    return result
