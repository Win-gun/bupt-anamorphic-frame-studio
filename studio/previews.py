"""Preview-only alpha/crop derivatives; playback atlas is never resized here."""
import json
from pathlib import Path
from PIL import Image


def make_previews(directory):
    directory = Path(directory)
    with Image.open(directory / "simulation.png") as source, Image.open(
        directory / "mask.png"
    ) as mask:
        if source.size != mask.size:
            raise ValueError("模拟图与独立LED遮罩尺寸不一致")
        alpha = mask.convert("L")
        image = source.convert("RGBA")
        image.putalpha(alpha)
        image.save(directory / "simulation_rgba.png")
        bbox = alpha.point(lambda x: 255 if x > 3 else 0).getbbox()
        if bbox is None:
            raise ValueError("观察点下没有有效LED区域")
        image.crop(bbox).save(directory / "led_crop.png")
        metadata = {
            "source_size": list(source.size),
            "crop_box": list(bbox),
            "cropped_size": [bbox[2] - bbox[0], bbox[3] - bbox[1]],
            "playback_canvas_changed": False,
            "method": "Actual Blender simulated LED render with independently rendered physical-screen coverage alpha; bounding-box crop only.",
        }
    (directory / "preview.json").write_text(json.dumps(metadata, indent=2))
    return {
        "simulation_alpha": "simulation_rgba.png",
        "led_crop": "led_crop.png",
        "preview_report": "preview.json",
    }
