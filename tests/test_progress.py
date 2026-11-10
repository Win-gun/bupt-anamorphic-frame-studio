import json
from pathlib import Path
from studio.progress import render_progress
from studio.config import Config
from studio import server
from fastapi.testclient import TestClient


def setup(tmp_path):
    (tmp_path / "config.json").write_text(Config().model_dump_json())
    (tmp_path / "render.log").write_text("Rendered 2/6 Tiles, Sample 17/32\n")
    return {"id": "task", "status": "running", "progress": 10, "started_at": 100}


def test_live_tiles_and_elapsed_do_not_remain_at_ten(tmp_path):
    job = setup(tmp_path)
    result = render_progress(tmp_path, job, now=160)
    assert result["progress"] > 10
    assert result["elapsed_seconds"] == 60
    assert result["stage"] == "场景渲染" and "17/32" in result["detail"]
    assert job["progress"] == 10


def test_old_render_stats_not_reused_for_next_stage(tmp_path):
    job = setup(tmp_path)
    (tmp_path / "scene.png").touch()
    (tmp_path / "render.log").write_text(
        "Rendered 6/6 Tiles, Sample 32/32\nSaved: 'scene.png'\nUpdating scene\n"
    )
    result = render_progress(tmp_path, job, now=160)
    assert result["stage"] == "海报覆盖验证" and result["progress"] == 48


def test_animation_frames_are_real_file_counts(tmp_path):
    job = setup(tmp_path)
    c = Config()
    c.render.animation = True
    c.render.duration = 7.5
    c.render.fps = 24
    (tmp_path / "config.json").write_text(c.model_dump_json())
    (tmp_path / "frames").mkdir()
    for i in range(9):
        (tmp_path / "frames" / f"led_{i:04d}.png").touch()
    result = render_progress(tmp_path, job, now=160)
    assert result["stage"] == "三维动画与曲面映射" and result["detail"] == "已完成 9/180 帧"
    assert 30 < result["progress"] < 89


def test_encoding_terminal_and_missing_files(tmp_path):
    job = setup(tmp_path)
    job.update(progress=92, stage="视频编码")
    assert render_progress(tmp_path, job)["stage"] == "视频编码"
    job.update(status="completed", progress=100)
    assert render_progress(tmp_path, job) == job
    assert (
        render_progress(tmp_path / "absent", dict(status="running", progress=10))[
            "stage"
        ]
        == "启动 Blender"
    )


def test_api_polls_actual_log_without_holding_job_lock(tmp_path, monkeypatch):
    directory = tmp_path / "task"
    directory.mkdir()
    job = setup(directory)
    monkeypatch.setattr(server, "OUTPUTS", tmp_path)
    monkeypatch.setattr(server, "jobs", {"task": job})
    result = TestClient(server.app).get("/api/jobs/task").json()
    assert result["progress"] > 10 and result["stage"] == "场景渲染"


def test_cycles_untiled_preview_sample_format(tmp_path):
    job = setup(tmp_path)
    (tmp_path / "render.log").write_text("Scene, ViewLayer | Sample 17/64\n")
    result = render_progress(tmp_path, job, now=160)
    assert result["detail"] == "当前采样 17/64"
    assert 10 < result["progress"] < 48
