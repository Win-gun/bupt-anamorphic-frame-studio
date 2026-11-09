import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Upload,
  Play,
  Download,
  Box,
  ScanLine,
  Settings2,
  Image as ImageIcon,
} from "lucide-react";
import "./style.css";
type Config = {
  screen: {
    pixels: number[];
    height_px: number;
    pitch_mm: number;
    angle_deg: number;
    radius_m: number | null;
    calibrated: boolean;
  };
  camera: { position: number[]; target: number[]; fov_deg: number };
  frame: {
    template: string;
    width_m: number;
    height_m: number;
    depth_m: number;
    border_m: number;
    position: number[];
    color: string;
  };
  render: {
    scale: number;
    samples: number;
    video: boolean;
    duration: number;
    fps: number;
  };
};
type Job = {
  id: string;
  status: string;
  progress: number;
  error?: string;
  outputs?: Record<string, string>;
  metrics?: Record<string, unknown>;
};
function App() {
  const [c, setC] = useState<Config | null>(null),
    [file, setFile] = useState<File | null>(null),
    [job, setJob] = useState<Job | null>(null),
    [jobs, setJobs] = useState<Job[]>([]),
    [tab, setTab] = useState("simulation"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    fetch("/api/config")
      .then((r) => r.json())
      .then(setC)
      .catch(() => setError("无法连接本地服务，请检查后端是否运行。"));
    refresh();
  }, []);
  function refresh() {
    fetch("/api/jobs")
      .then((r) => r.json())
      .then((x) => setJobs(Array.isArray(x) ? x : x.jobs || []))
      .catch(() => {});
  }
  useEffect(() => {
    if (
      !job ||
      ["completed", "failed", "done", "error", "validation_failed"].includes(
        job.status,
      )
    )
      return;
    const t = setInterval(
      () =>
        fetch("/api/jobs/" + job.id)
          .then((r) => r.json())
          .then((j) => {
            setJob(j);
            if (
              [
                "completed",
                "failed",
                "done",
                "error",
                "validation_failed",
              ].includes(j.status)
            )
              refresh();
          })
          .catch(() => {}),
      1500,
    );
    return () => clearInterval(t);
  }, [job?.id, job?.status]);
  function set(section: keyof Config, key: string, value: unknown) {
    setC((old) =>
      old ? { ...old, [section]: { ...old[section], [key]: value } } : old,
    );
  }
  function vector(
    section: "screen" | "camera" | "frame",
    key: string,
    index: number,
    value: number,
  ) {
    if (!c) return;
    const a = [...(c[section] as unknown as Record<string, number[]>)[key]];
    a[index] = value;
    set(section, key, a);
  }
  async function submit() {
    if (!file || !c) return;
    setBusy(true);
    setError("");
    try {
      const data = new FormData();
      data.append("file", file);
      data.append("config", JSON.stringify(c));
      const r = await fetch("/api/jobs", { method: "POST", body: data });
      if (!r.ok) throw new Error(await r.text());
      const j = await r.json();
      setJob({ id: j.id, status: "queued", progress: 0 });
      refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  const n = (
    label: string,
    value: number,
    onChange: (n: number) => void,
    step = 0.1,
  ) => (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
  const vec = (
    title: string,
    section: "camera" | "frame",
    key: "position" | "target",
    v: number[],
  ) => (
    <div className="vector">
      <div className="sub">{title}</div>
      <div className="triple">
        {v.map((x, i) =>
          n(["X", "Y", "Z"][i], x, (z) => vector(section, key, i, z)),
        )}
      </div>
    </div>
  );
  const tabs = [
    ["original", "原始画作"],
    ["simulation", "观看模拟"],
    ["scene", "三维场景"],
    ["atlas", "屏幕展开"],
    ["difference", "差异图"],
  ];
  if (!c) return <div className="loading">{error || "正在连接工作室…"}</div>;
  return (
    <>
      <header>
        <div className="brand">
          <span className="brandmark">B</span>
          <div>
            <b>FRAME STUDIO</b>
            <small>BUPT · ANAMORPHIC LAB</small>
          </div>
        </div>
        <div className="headcenter">
          裸眼三维画框工作台 <span>/</span> 创作空间
        </div>
        <div className="headright">
          <span className="dot" /> 本地工作区{" "}
          <span className="version">V 1.0</span>
        </div>
      </header>
      <main>
        <aside className="left">
          <div className="paneltitle">
            <span>01 / 素材与模板</span>
            <ImageIcon size={16} />
          </div>
          <h2>从一张画开始</h2>
          <p className="muted">上传画作，选择空间画框的呈现方式。</p>
          <label className="upload">
            <Upload size={23} />
            <b>{file ? file.name : "选择一张图片"}</b>
            <span>点击上传 JPG、PNG 等图片</span>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </label>
          <div className="sectionlabel">
            <span>画框模板</span>
            <small>FRAME TYPE</small>
          </div>
          <div className="templates">
            {[
              ["deep", "深邃画框", "纵深空间感"],
              ["float", "悬浮画框", "轻盈悬浮感"],
              ["glass", "玻璃画框", "通透层次感"],
            ].map(([id, name, desc], i) => (
              <button
                key={id}
                className={
                  "template " + (c.frame.template === id ? "selected" : "")
                }
                onClick={() => set("frame", "template", id)}
              >
                <span className={"frameicon f" + i}>
                  <i />
                </span>
                <span>
                  <b>{name}</b>
                  <small>{desc}</small>
                </span>
                <span className="radio" />
              </button>
            ))}
          </div>
          <div className="paneltitle">
            <span>02 / 场景设置</span>
            <Settings2 size={16} />
          </div>
          <h2>调整参数</h2>
          <p className="muted">设定屏幕、机位与画框尺寸。</p>
          <div className="notice">
            <ScanLine size={17} />
            <div>
              <b>
                校准状态：{c.screen.calibrated ? "操作者声明已校准" : "未校准"}
              </b>
              <p>屏幕与机位参数需根据实际场地测量，当前结果仅供预览。</p>
            </div>
          </div>
          <details open>
            <summary>
              <span>屏幕参数</span>
              <small>SCREEN</small>
            </summary>
            <div className="triple">
              {c.screen.pixels.map((x, i) => (
                <label className="field" key={i}>
                  <span>{["左屏 px", "转角 px", "右屏 px"][i]}</span>
                  <input type="number" value={x} readOnly />
                </label>
              ))}
            </div>
            <div className="double">
              <label className="field">
                <span>高度 px</span>
                <input type="number" value={c.screen.height_px} readOnly />
              </label>
              {n("点间距 mm", c.screen.pitch_mm, (v) =>
                set("screen", "pitch_mm", v),
              )}
              {n(
                "夹角 °",
                c.screen.angle_deg,
                (v) => set("screen", "angle_deg", v),
                1,
              )}
              <label className="field">
                <span>弧半径 m（可选）</span>
                <input
                  type="number"
                  value={c.screen.radius_m ?? ""}
                  onChange={(e) =>
                    set(
                      "screen",
                      "radius_m",
                      e.target.value === "" ? null : Number(e.target.value),
                    )
                  }
                />
              </label>
            </div>
            <label className="check">
              <input
                type="checkbox"
                checked={c.screen.calibrated}
                onChange={(e) => set("screen", "calibrated", e.target.checked)}
              />{" "}
              已按实际场地校准
            </label>
          </details>
          <details open>
            <summary>
              <span>观看机位</span>
              <small>CAMERA</small>
            </summary>
            {vec("位置 / POSITION", "camera", "position", c.camera.position)}
            {vec("目标 / TARGET", "camera", "target", c.camera.target)}
            {n(
              "视场角 °",
              c.camera.fov_deg,
              (v) => set("camera", "fov_deg", v),
              1,
            )}
          </details>
          <details open>
            <summary>
              <span>画框尺寸</span>
              <small>FRAME</small>
            </summary>
            <div className="double">
              {n("宽度 m", c.frame.width_m, (v) => set("frame", "width_m", v))}
              {n("高度 m", c.frame.height_m, (v) =>
                set("frame", "height_m", v),
              )}
              {n(
                "深度 m",
                c.frame.depth_m,
                (v) => set("frame", "depth_m", v),
                0.01,
              )}
              {n(
                "边框 m",
                c.frame.border_m,
                (v) => set("frame", "border_m", v),
                0.01,
              )}
            </div>
            {vec("位置 / POSITION", "frame", "position", c.frame.position)}
            <label className="colorfield">
              画框颜色{" "}
              <input
                type="color"
                value={c.frame.color}
                onChange={(e) => set("frame", "color", e.target.value)}
              />
              <span>{c.frame.color}</span>
            </label>
          </details>
        </aside>
        <section className="center">
          <div className="workspacehead">
            <div>
              <div className="eyebrow">
                CREATIVE WORKSPACE <span> / 画面预览</span>
              </div>
              <h1>
                空间画框<span>工作台</span>
              </h1>
            </div>
            <div className="badge">
              <span className="amberdot" />{" "}
              {c.screen.calibrated ? "操作者声明已校准" : "屏幕未校准"}
            </div>
          </div>
          <div className="previewbar">
            <div className="tabs">
              {tabs.map(([id, name]) => (
                <button
                  key={id}
                  className={tab === id ? "active" : ""}
                  onClick={() => setTab(id)}
                >
                  {name}
                </button>
              ))}
            </div>
            <span className="previewhint">
              {job ? "任务 " + job.id.slice(0, 8) : "等待渲染"}
            </span>
          </div>
          <div className="viewport">
            {job?.outputs?.[tab] ? (
              <img
                src={job.outputs[tab]}
                alt={tabs.find((t) => t[0] === tab)?.[1]}
              />
            ) : (
              <div className="empty">
                <div className="emptygraphic">
                  <div className="cube">
                    <Box size={56} strokeWidth={0.8} />
                  </div>
                  <span className="axis a1" />
                  <span className="axis a2" />
                </div>
                <h3>
                  {job && ["queued", "running"].includes(job.status)
                    ? "正在生成画面"
                    : "画面将在这里呈现"}
                </h3>
                <p>
                  {job && ["queued", "running"].includes(job.status)
                    ? "渲染进行中，请稍候。"
                    : "上传图片并设置参数后，开始创建你的空间画框。"}
                </p>
              </div>
            )}
            <div className="viewportmeta">
              <span>PREVIEW / {tab.toUpperCase()}</span>
              <span>BUИT · FRAME LAB</span>
            </div>
          </div>
          <div className="statusline">
            <div>
              <span className="statusdot" />{" "}
              {job
                ? `${({ queued: "排队中", running: "渲染中", completed: "已完成", done: "已完成", failed: "失败", error: "错误", validation_failed: "验证未通过" } as Record<string, string>)[job.status] || job.status} · ${Math.round(job.progress <= 1 ? job.progress * 100 : job.progress)}%`
                : "准备就绪"}{" "}
              {job?.error && <span className="error"> · {job.error}</span>}
            </div>
            <span>
              预览比例 {c.render.scale} · 完整画布{" "}
              {c.screen.pixels.reduce((a, b) => a + b, 0)} ×{" "}
              {c.screen.height_px} px
            </span>
          </div>
          {error && <div className="error">{error}</div>}
          {job?.metrics && (
            <details className="metrics">
              <summary>验证指标 / METRICS</summary>
              <pre>{JSON.stringify(job.metrics, null, 2)}</pre>
            </details>
          )}
        </section>
        <aside className="right">
          <div className="paneltitle">
            <span>03 / 渲染与输出</span>
            <Settings2 size={16} />
          </div>
          <h2>生成画面</h2>
          <p className="muted">设置渲染质量并导出结果。</p>
          <details>
            <summary>
              <span>渲染设置</span>
              <small>RENDER</small>
            </summary>
            <div className="double">
              {n(
                "渲染比例",
                c.render.scale,
                (v) => set("render", "scale", v),
                0.05,
              )}
              {n(
                "采样数",
                c.render.samples,
                (v) => set("render", "samples", v),
                1,
              )}
              {n(
                "时长 s",
                c.render.duration,
                (v) => set("render", "duration", v),
                1,
              )}
              {n("帧率 fps", c.render.fps, (v) => set("render", "fps", v), 1)}
            </div>
            <label className="check">
              <input
                type="checkbox"
                checked={c.render.video}
                onChange={(e) => set("render", "video", e.target.checked)}
              />{" "}
              生成定格视频
            </label>
          </details>
          <button
            className="render"
            disabled={
              !file ||
              busy ||
              !!(job && ["queued", "running"].includes(job.status))
            }
            onClick={submit}
          >
            <Play size={15} fill="currentColor" /> 开始渲染 <span>↗</span>
          </button>
          <p className="rendernote">渲染将在本机执行</p>
          <div className="bottom">
            <div>
              <div className="eyebrow">OUTPUT / 输出文件</div>
              <h3>渲染结果</h3>
              <p className="muted">完成后可预览并下载生成的文件。</p>
            </div>
            <div className="downloads">
              {job?.outputs ? (
                Object.entries(job.outputs).map(([k, v]) => (
                  <a key={k} href={v} download>
                    <Download size={14} />
                    {(
                      {
                        original: "原图",
                        scene: "场景",
                        atlas: "展开图",
                        simulation: "模拟图",
                        difference: "差异图",
                        mask: "遮罩",
                        blend: "工程文件",
                        report: "报告",
                        video: "定格视频",
                      } as Record<string, string>
                    )[k] || k}
                  </a>
                ))
              ) : (
                <span>暂无输出文件</span>
              )}
            </div>
          </div>
          <div className="history">
            <div className="sectionlabel">
              <span>最近任务</span>
              <small>RECENT JOBS</small>
            </div>
            {jobs.length ? (
              jobs.slice(0, 5).map((j) => (
                <button
                  key={j.id}
                  onClick={() =>
                    fetch("/api/jobs/" + j.id)
                      .then((r) => r.json())
                      .then(setJob)
                  }
                >
                  <span>{j.id.slice(0, 12)}</span>
                  <span>
                    {(
                      {
                        queued: "排队中",
                        running: "渲染中",
                        completed: "已完成",
                        done: "已完成",
                        failed: "失败",
                        error: "错误",
                        validation_failed: "验证未通过",
                      } as Record<string, string>
                    )[j.status] || j.status}{" "}
                    ↗
                  </span>
                </button>
              ))
            ) : (
              <p className="muted">还没有渲染任务</p>
            )}
          </div>
        </aside>
      </main>
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
