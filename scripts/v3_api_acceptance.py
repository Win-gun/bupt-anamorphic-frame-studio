"""Actual V3 upload -> gentle 3D sequence -> mapped LED -> FFmpeg acceptance."""
import argparse, json, time, shutil
from pathlib import Path
import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--base-url", default="http://127.0.0.1:8000")
a = p.parse_args()
with httpx.Client(base_url=a.base_url, timeout=60) as client:
    config = client.get("/api/config").json()
    config["render"].update(
        scale=0.125, samples=8, duration=2, fps=12, animation=True, light_sweep=True
    )
    with (ROOT / "examples/v2/jiqi-qiuyun/original.png").open("rb") as source:
        response = client.post(
            "/api/jobs",
            data={"config": json.dumps(config)},
            files={"file": ("poster.png", source, "image/png")},
        )
    response.raise_for_status()
    identifier = response.json()["id"]
    print(identifier, flush=True)
    for _ in range(300):
        job = client.get("/api/jobs/" + identifier).json()
        if job["status"] not in ("queued", "running"):
            break
        time.sleep(2)
    target = ROOT / "examples/v3/motion-api"
    target.mkdir(exist_ok=True)
    (target / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2))
    assert job["status"] == "completed", job.get("error")
    source = ROOT / "outputs" / identifier
    for name in [
        "led.mp4",
        "video-probe.json",
        "report.json",
        "config.json",
        "animation.json",
        "preview.json",
    ]:
        shutil.copy2(source / name, target / name)
    dynamics = job["metrics"]["dynamics"]
    assert dynamics["passed"] and dynamics["timing"]["finish_hold"]
    positions = [frame["translation_m"] for frame in dynamics["frames"]]
    assert positions[-1] == positions[-2] and positions[-1] != positions[0]
    frames = sorted((source / "frames").glob("led_*.png"))
    assert len(frames) == 24
    sheet = Image.new("RGB", (546 * 3, 390 * 2))
    for slot, index in enumerate([0, 5, 10, 15, 20, 23]):
        sheet.paste(Image.open(frames[index]), ((slot % 3) * 546, (slot // 3) * 390))
    sheet.save(target / "mapped-motion-frames.png")
    print(
        json.dumps(
            {
                "job": identifier,
                "frames": len(frames),
                "finish_hold": True,
                "verification": dynamics["verification"],
            },
            indent=2,
        )
    )
