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
const Orbit = React.lazy(() =>
  import("./Orbit").then((m) => ({ default: m.Orbit })),
);
type Config = {
  screen: {
    pixels: number[];
    height_px: number;
    pitch_mm: number;
    angle_deg: number;
    radius_m: number | null;
    calibrated: boolean;
    curvature: string;
    yaw_deg: number;
  };
  camera: { position: number[]; target: number[]; fov_deg: number };
  frame: {
    template: string;
    layout: string;
    material: string;
    scale: number;
    virtual_depth_m: number;
    edge_light: boolean;
    portal_depth_m: number;
    width_m: number;
    height_m: number;
    depth_m: number;
    border_m: number;
    position: number[];
    color: string;
  };
  appearance: {
    palette: string;
    colors: string[];
    gradient_type: string;
    stops: number[];
    direction_deg: number;
    transition: number;
    brightness: number;
    saturation: number;
    noise_strength: number;
  };
  lighting: {
    intensity: number;
    softness: number;
    glow: number;
    ambient: number;
    shadow_softness: number;
  };
  cube: {
    layout: string;
    depth_m: number;
    wall_thickness_m: number;
    opening_scale: number;
    facade_margin_m: number;
    poster_scale: number;
    poster_depth_fraction: number;
  };
  autumn: {
    variant: string;
    texture_strength_m: number;
    gradient_strength: number;
    light_intensity: number;
    softness: number;
    shadow_strength: number;
    ambient: number;
    edge_highlight: number;
    poster_depth_fraction: number;
    opening_bevel_m: number;
    panel_bevel_m: number;
    engine: string;
  };
  panel: {
    thickness_m: number;
    corner_radius_m: number;
    float_distance_m: number;
    reflection: number;
  };
  render: {
    scale: number;
    quality: string;
    animation: boolean;
    light_sweep: boolean;
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
  stage?: string;
  detail?: string;
  elapsed_seconds?: number;
  last_activity_age_s?: number;
  error?: string;
  outputs?: Record<string, string>;
  metrics?: Record<string, unknown>;
};
function App() {
  const [c, setC] = useState<Config | null>(null),
    [file, setFile] = useState<File | null>(null),
    [job, setJob] = useState<Job | null>(null),
    [jobs, setJobs] = useState<Job[]>([]),
    [tab, setTab] = useState("simulation_alpha"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [snapshot, setSnapshot] = useState<Config | null>(null),
    [localURL, setLocalURL] = useState(""),
    [preset, setPreset] = useState(""),
    [palettes, setPalettes] = useState<
      Record<string, { name: string; colors: string[] }>
    >({}),
    [professional, setProfessional] = useState(false),
    [background, setBackground] = useState("checker"),
    [photo, setPhoto] = useState(""),
    [placement, setPlacement] = useState({
      x: 50,
      y: 50,
      scale: 50,
      opacity: 80,
    });
  useEffect(() => {
    fetch("/api/settings")
      .then((r) => {
        if (!r.ok) throw new Error("保存的配置无效，请重置配置");
        return r.json();
      })
      .then(setC)
      .catch(() => setError("无法连接本地服务，请检查后端是否运行。"));
    fetch("/api/presets")
      .then((r) => r.json())
      .then((x) => {
        setPreset(x.name || "BUPT Curved LED");
        setPalettes(x.palettes || {});
      });
    refresh();
  }, []);
  useEffect(() => {
    if (!file) {
      setLocalURL("");
      return;
    }
    const u = URL.createObjectURL(file);
    setLocalURL(u);
    return () => URL.revokeObjectURL(u);
  }, [file]);
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
          .catch(() => setError("无法更新任务状态，请检查本地服务。")),
      1500,
    );
    return () => clearInterval(t);
  }, [job?.id, job?.status]);
  useEffect(() => {
    if (!job?.outputs?.config) return;
    let active = true;
    fetch(job.outputs.config)
      .then((r) => r.json())
      .then((config) => {
        if (active) setSnapshot(config);
      })
      .catch(() => setError("无法读取渲染配置快照"));
    return () => {
      active = false;
    };
  }, [job?.id, job?.outputs?.config]);
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
  async function submit(mode: "quick" | "high" | "formal" | "motion") {
    if (!file || !c) return;
    setBusy(true);
    setError("");
    try {
      const data = new FormData();
      data.append("file", file);
      const config = structuredClone(c);
      if (mode === "quick")
        Object.assign(config.render, {
          scale: 0.125,
          samples: 8,
          quality: "quick",
          video: false,
          animation: false,
          light_sweep: false,
        });
      if (mode === "high")
        Object.assign(config.render, {
          scale: 0.5,
          samples: 64,
          quality: "high",
          video: false,
          animation: false,
          light_sweep: false,
        });
      if (mode === "motion")
        Object.assign(config.render, {
          scale: 0.125,
          samples: 8,
          quality: "quick",
          animation: true,
          video: true,
          duration: config.frame.template === "autumn_resonance_cube" ? 7.5 : 2,
          fps: config.frame.template === "autumn_resonance_cube" ? 24 : 12,
        });
      if (mode === "formal") config.render.scale = 1;
      data.append("config", JSON.stringify(config));
      const r = await fetch("/api/jobs", { method: "POST", body: data });
      if (!r.ok) throw new Error(await r.text());
      const j = await r.json();
      setJob({ id: j.id, status: "queued", progress: 0 });
      setSnapshot(config);
      setTab("simulation_alpha");
      refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function configAction(path: string, method = "GET", body?: unknown) {
    try {
      const r = await fetch(path, {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      if (!r.ok) throw new Error(await r.text());
      const x = await r.json();
      setC(x);
      setError("");
    } catch (e) {
      setError(String(e));
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
    ["simulation_alpha", "最佳观看模拟"],
    ["led_crop", "LED 裁切预览"],
    ["scene", "三维场景"],
    ["atlas", "屏幕展开"],
    ["orbit", "交互 3D"],
    ["photo", "现场照片合成"],
  ];
  if (!c)
    return (
      <div className="loading">
        {error || "正在连接工作室…"}
        {error && (
          <button onClick={() => configAction("/api/settings/reset", "POST")}>
            重置配置
          </button>
        )}
      </div>
    );
  const isAutumn = c.frame.template === "autumn_resonance_cube";
  const isAmberGallery = c.frame.template === "autumn_amber_gallery";
  const isAutumnStage = isAmberGallery || c.frame.template === "autumn_symphony";
  const isArchitecture = c.frame.template === "embedded_cube_architecture";
  const isLegacy = ["cinema", "deep", "float", "glass"].includes(
    c.frame.template,
  );
  return (
    <>
      <header>
        <div className="brand">
          <span className="brandmark">B</span>
          <div>
            <b>ANAMORPHIC IMAGE DISPLAY STUDIO</b>
            <small>BUPT · ANAMORPHIC LAB</small>
          </div>
        </div>
        <div className="headcenter">
          图片空间展示 <span>/</span> 创作空间
        </div>
        <div className="headright">
          <button onClick={() => setProfessional(!professional)}>
            {professional ? "专业模式" : "创作模式"} · 切换
          </button>
          <span className="dot" /> 本地工作区{" "}
          <span className="version">V 3.0</span>
        </div>
      </header>
      <main>
        <aside className="left">
          <div className="paneltitle">
            <span>01 / 素材与模板</span>
            <ImageIcon size={16} />
          </div>
          <h2>从一张画开始</h2>
          <p className="muted">上传图片，选择柔和的空间展示方式。</p>
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
            <span>空间样式</span>
            <small>STYLE</small>
          </div>
          <div className="templates">
            {[
              ["autumn_amber_gallery", "秋韵 · 琥珀回廊", "铜饰曲面 · 陶釉枫叶"],
              ["autumn_symphony", "秋韵 · 枫光奏鸣", "枫叶雕塑 · 旋律曲面"],
              ["autumn_resonance_cube", "秋韵光影舱", "Autumn Resonance Cube"],
              ["aurora_float", "极光悬浮", "柔和空间"],
              ["soft_depth", "柔光纵深", "轻柔层次"],
              ["glass_layers", "玻璃叠层", "通透质感"],
              [
                "embedded_cube_architecture",
                "楼体内嵌立方体",
                "Embedded Cube · 建筑切口",
              ],
              ["embedded_cube", "嵌入立方（原版）", "保留 V3 轻型版本"],
            ].map(([id, name, desc]) => (
              <button
                key={id}
                className={
                  "template " + (c.frame.template === id ? "selected" : "")
                }
                onClick={() => {
                  if (id === "autumn_symphony" || id === "autumn_amber_gallery")
                    setC({
                      ...c,
                      frame: {
                        ...c.frame,
                        template: id,
                        layout: "auto_fit",
                        position: [0, 0, 0],
                        scale: id === "autumn_amber_gallery" ? 0.9 : 0.88,
                        virtual_depth_m: 0,
                      },
                      render: {
                        ...c.render,
                        animation: false,
                        video: false,
                        light_sweep: false,
                      },
                      lighting: {
                        ...c.lighting,
                        intensity: 1,
                        softness: 0.8,
                        ambient: 0.5,
                      },
                    });
                  else if (id === "autumn_resonance_cube")
                    setC({
                      ...c,
                      frame: {
                        ...c.frame,
                        template: id,
                        layout: "auto_fit",
                        position: [0, 0, 0],
                      },
                      cube: {
                        ...c.cube,
                        layout: "floating",
                        depth_m: 3,
                        wall_thickness_m: 0.32,
                        opening_scale: 0.94,
                        poster_scale: 0.82,
                      },
                      render: { ...c.render, light_sweep: false },
                    });
                  else if (id === "embedded_cube_architecture")
                    setC({
                      ...c,
                      frame: {
                        ...c.frame,
                        template: id,
                        layout: "auto_fit",
                        position: [0, 0, 0],
                      },
                    });
                  else set("frame", "template", id);
                }}
              >
                <span className={"frameicon f" + ({autumn_amber_gallery: 3, autumn_symphony: 2, autumn_resonance_cube: 3, aurora_float: 0, soft_depth: 1, glass_layers: 2, embedded_cube_architecture: 3, embedded_cube: 4} as Record<string, number>)[id]}>
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
          <details>
            <summary>Legacy / 经典样式</summary>
            <div className="templates">
              {[
                ["cinema", "影院画框"],
                ["float", "悬浮画框"],
                ["glass", "玻璃画框"],
              ].map(([id, name]) => (
                <button
                  key={id}
                  className={
                    "template " + (c.frame.template === id ? "selected" : "")
                  }
                  onClick={() => set("frame", "template", id)}
                >
                  {name}
                </button>
              ))}
            </div>
          </details>
          {isAutumnStage && (
            <p className="muted">
              {isAmberGallery
                ? "拉丝铜饰、紫色陶釉曲面与悬浮枫叶。高质量渲染呈现完整光影。"
                : "专为「计启秋韵」设计：立体枫叶、流动曲面与紫橙柔光延展原画意境。海报使用完整原始纹理。快速构图使用 Eevee，高质量输出使用 Cycles。"}
            </p>
          )}
          {c.frame.template === "embedded_cube_architecture" && (
            <details open>
              <summary>Embedded Cube · 建筑空间</summary>
              <label className="field">
                海报布局
                <select
                  value={c.cube.layout}
                  onChange={(e) => set("cube", "layout", e.target.value)}
                >
                  <option value="floating">方案 B · 舱内悬浮（推荐）</option>
                  <option value="back_wall">方案 A · 后壁展示</option>
                </select>
              </label>
              <p className="muted">
                整片建筑立面中的真实挖空空间，保留开口、墙厚及五个内部面。
              </p>
              <div className="double">
                {n("空间深度 m", c.cube.depth_m, (v) =>
                  set("cube", "depth_m", v),
                )}
                {n(
                  "墙体厚度 m",
                  c.cube.wall_thickness_m,
                  (v) => set("cube", "wall_thickness_m", v),
                  0.02,
                )}
                {n(
                  "海报占用",
                  c.cube.poster_scale,
                  (v) => set("cube", "poster_scale", v),
                  0.02,
                )}
              </div>
              {professional && (
                <div className="double">
                  {n(
                    "开口占用",
                    c.cube.opening_scale,
                    (v) => set("cube", "opening_scale", v),
                    0.01,
                  )}
                  {n("立面延伸 m", c.cube.facade_margin_m, (v) =>
                    set("cube", "facade_margin_m", v),
                  )}
                  {n(
                    "舱内位置比例",
                    c.cube.poster_depth_fraction,
                    (v) => set("cube", "poster_depth_fraction", v),
                    0.02,
                  )}
                </div>
              )}
            </details>
          )}
          {!isLegacy && !isArchitecture && !isAutumn && !isAutumnStage && (
            <>
              <div className="sectionlabel">
                <span>空间色彩</span>
                <small>PALETTE</small>
              </div>
              <div className="palette-list">
                {Object.entries(palettes).map(([id, p]) => (
                  <button
                    key={id}
                    className={c.appearance.palette === id ? "selected" : ""}
                    onClick={() =>
                      setC({
                        ...c,
                        appearance: {
                          ...c.appearance,
                          palette: id,
                          colors: p.colors,
                        },
                      })
                    }
                  >
                    <span>{p.name}</span>
                    <span className="swatches">
                      {p.colors.map((color, i) => (
                        <i key={i} style={{ background: color }} />
                      ))}
                    </span>
                  </button>
                ))}
              </div>
              {professional && (
                <div className="color-editor">
                  {c.appearance.colors.map((color, i) => (
                    <input
                      key={i}
                      aria-label={`颜色 ${i + 1}`}
                      type="color"
                      value={color}
                      onChange={(e) => {
                        const colors = [...c.appearance.colors];
                        colors[i] = e.target.value;
                        setC({
                          ...c,
                          appearance: {
                            ...c.appearance,
                            palette: "custom",
                            colors,
                          },
                        });
                      }}
                    />
                  ))}
                </div>
              )}
              {professional && (
                <details>
                  <summary>色彩细节 / APPEARANCE</summary>
                  <label className="field">
                    渐变类型
                    <select
                      value={c.appearance.gradient_type}
                      onChange={(e) =>
                        set("appearance", "gradient_type", e.target.value)
                      }
                    >
                      {[
                        ["dual", "双色"],
                        ["linear", "线性"],
                        ["radial", "径向"],
                        ["multi", "多色"],
                      ].map(([id, label]) => (
                        <option key={id} value={id}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="double">
                    {n(
                      "方向 °",
                      c.appearance.direction_deg,
                      (v) => set("appearance", "direction_deg", v),
                      1,
                    )}
                    {n(
                      "过渡",
                      c.appearance.transition,
                      (v) => set("appearance", "transition", v),
                      0.05,
                    )}
                    {n(
                      "亮度",
                      c.appearance.brightness,
                      (v) => set("appearance", "brightness", v),
                      0.05,
                    )}
                    {n(
                      "饱和度",
                      c.appearance.saturation,
                      (v) => set("appearance", "saturation", v),
                      0.05,
                    )}
                    {n(
                      "噪点",
                      c.appearance.noise_strength,
                      (v) => set("appearance", "noise_strength", v),
                      0.001,
                    )}
                    {n(
                      "圆角 m",
                      c.panel.corner_radius_m,
                      (v) => set("panel", "corner_radius_m", v),
                      0.005,
                    )}
                    {n(
                      "反射",
                      c.panel.reflection,
                      (v) => set("panel", "reflection", v),
                      0.005,
                    )}
                  </div>
                  <p className="muted">
                    色标需从 0 到 1 严格递增，与颜色数量一致。
                  </p>
                  <div className="double">
                    {c.appearance.stops.map((stop, i) =>
                      n(
                        `色标 ${i + 1}`,
                        stop,
                        (v) => {
                          const stops = [...c.appearance.stops];
                          stops[i] = v;
                          set("appearance", "stops", stops);
                        },
                        0.05,
                      ),
                    )}
                  </div>
                </details>
              )}
            </>
          )}
          {professional && !isLegacy && !isArchitecture && !isAutumn && !isAutumnStage && (
            <details>
              <summary>图片布局 / LAYOUT</summary>
              <label className="field">
                布局
                <select
                  value={c.frame.layout}
                  onChange={(e) => set("frame", "layout", e.target.value)}
                >
                  <option value="auto_fit">Auto Fit · 完整显示</option>
                  <option value="fill">Fill · 中心裁切</option>
                  <option value="manual">Manual · 人工尺寸</option>
                </select>
              </label>
              {c.frame.layout === "manual" && (
                <div className="double">
                  {n("面板宽度 m", c.frame.width_m, (v) =>
                    set("frame", "width_m", v),
                  )}
                  {n("面板高度 m", c.frame.height_m, (v) =>
                    set("frame", "height_m", v),
                  )}
                </div>
              )}
              {vec(
                c.frame.layout === "manual"
                  ? "面板世界位置"
                  : "相机空间偏移（右/上/向内）",
                "frame",
                "position",
                c.frame.position,
              )}
            </details>
          )}
          {isLegacy && !professional && (
            <p className="muted">
              经典样式保留原有材质与灯光。切换专业模式可调整画框参数。
            </p>
          )}
          {isAutumn && (
            <details open>
              <summary>秋韵光影 / AUTUMN</summary>
              <label className="field">
                色调
                <select
                  value={c.autumn.variant}
                  onChange={(e) => set("autumn", "variant", e.target.value)}
                >
                  <option value="balanced">平衡</option>
                  <option value="warm">暖调</option>
                  <option value="cool">冷调</option>
                </select>
              </label>
              <div className="double">
                {n(
                  "光照强度",
                  c.autumn.light_intensity,
                  (v) => set("autumn", "light_intensity", v),
                  0.05,
                )}
                {n(
                  "光线柔和度",
                  c.autumn.softness,
                  (v) => set("autumn", "softness", v),
                  0.05,
                )}
                {n(
                  "纹理强度 mm",
                  c.autumn.texture_strength_m * 1000,
                  (v) => set("autumn", "texture_strength_m", v / 1000),
                  0.05,
                )}
                {n(
                  "舱内位置比例",
                  c.autumn.poster_depth_fraction,
                  (v) => set("autumn", "poster_depth_fraction", v),
                  0.05,
                )}
                {n(
                  "阴影强度",
                  c.autumn.shadow_strength,
                  (v) => set("autumn", "shadow_strength", v),
                  0.05,
                )}
                {n(
                  "环境光",
                  c.autumn.ambient,
                  (v) => set("autumn", "ambient", v),
                  0.05,
                )}
                {n(
                  "边缘高光",
                  c.autumn.edge_highlight,
                  (v) => set("autumn", "edge_highlight", v),
                  0.05,
                )}
              </div>
              <details>
                <summary>高级参数</summary>
                <div className="double">
                  {n(
                    "渐变强度",
                    c.autumn.gradient_strength,
                    (v) => set("autumn", "gradient_strength", v),
                    0.05,
                  )}
                  {n(
                    "开口倒角 m",
                    c.autumn.opening_bevel_m,
                    (v) => set("autumn", "opening_bevel_m", v),
                    0.001,
                  )}
                  {n(
                    "面板倒角 m",
                    c.autumn.panel_bevel_m,
                    (v) => set("autumn", "panel_bevel_m", v),
                    0.001,
                  )}
                </div>
                <label className="field">
                  渲染引擎
                  <select
                    value={c.autumn.engine}
                    onChange={(e) => set("autumn", "engine", e.target.value)}
                  >
                    <option value="auto">自动（静态快览 Eevee）</option>
                    <option value="eevee">Eevee</option>
                    <option value="cycles">Cycles</option>
                  </select>
                </label>
                <p className="muted">自动模式下，高质量及秋韵动态使用 Cycles。</p>
              </details>
            </details>
          )}
          <details open>
            <summary>{isLegacy ? "作品大小" : "作品与光线"}</summary>
            <div className="double">
              {n(
                "图片大小",
                c.frame.scale,
                (v) => set("frame", "scale", v),
                0.05,
              )}
              {!isLegacy && !isAutumn && (
                <>
                  {!isArchitecture && !isAutumnStage && (
                    <>
                      {n(
                        "悬浮距离 m",
                        c.panel.float_distance_m,
                        (v) => set("panel", "float_distance_m", v),
                        0.05,
                      )}
                      {n(
                        "面板厚度 m",
                        c.panel.thickness_m,
                        (v) => set("panel", "thickness_m", v),
                        0.005,
                      )}
                    </>
                  )}
                  {(
                    [
                      ["intensity", "光照强度"],
                      ["softness", "光线柔和度"],
                      ["glow", "辉光"],
                      ["ambient", "环境光"],
                      ["shadow_softness", "阴影柔和度"],
                    ] as const
                  )
                    .filter(([k]) => (!isArchitecture || k !== "glow") && (!isAutumnStage || ["intensity", "softness", "ambient"].includes(k)))
                    .map(([k, label]) =>
                      n(
                        label,
                        c.lighting[k],
                        (v) => set("lighting", k, v),
                        0.05,
                      ),
                    )}
                </>
              )}
            </div>
          </details>
          <div className="paneltitle">
            <span>02 / 场景设置</span>
            <Settings2 size={16} />
          </div>
          <h2>调整参数</h2>
          <p className="muted">设定屏幕、机位与展示参数。</p>
          <div className="notice">
            <ScanLine size={17} />
            <div>
              <b>
                校准状态：{c.screen.calibrated ? "操作者声明已校准" : "未校准"}
              </b>
              <p>屏幕与机位参数需根据实际场地测量，当前结果仅供预览。</p>
            </div>
          </div>
          {professional && (
            <>
              <details open>
                <summary>
                  <span>屏幕参数</span>
                  <small>SCREEN</small>
                </summary>
                <p className="muted">{preset}</p>
                <label className="field">
                  弯曲方向
                  <select
                    value={c.screen.curvature}
                    onChange={(e) => set("screen", "curvature", e.target.value)}
                  >
                    <option value="convex">凸面</option>
                    <option value="concave">凹面</option>
                  </select>
                </label>
                <p className="muted">尚无现场照片佐证弯曲方向，请实地确认。</p>
                {n(
                  "旋转角 °",
                  c.screen.yaw_deg,
                  (v) => set("screen", "yaw_deg", v),
                  1,
                )}
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
                    onChange={(e) =>
                      set("screen", "calibrated", e.target.checked)
                    }
                  />{" "}
                  已按实际场地校准
                </label>
              </details>
              <details open>
                <summary>
                  <span>观看机位</span>
                  <small>CAMERA</small>
                </summary>
                <button
                  className="secondary"
                  onClick={() => {
                    setC((old) =>
                      old
                        ? {
                            ...old,
                            camera: {
                              ...old.camera,
                              position:
                                old.screen.curvature === "convex"
                                  ? [12, -14, 2]
                                  : [-2, -14, 2],
                              target: [0, 0, 0],
                            },
                          }
                        : old,
                    );
                  }}
                >
                  重置演示机位
                </button>
                <p className="muted">演示机位，不代表现场校准</p>
                {vec(
                  "位置 / POSITION",
                  "camera",
                  "position",
                  c.camera.position,
                )}
                {vec("目标 / TARGET", "camera", "target", c.camera.target)}
                {n(
                  "视场角 °",
                  c.camera.fov_deg,
                  (v) => set("camera", "fov_deg", v),
                  1,
                )}
              </details>
            </>
          )}
          {["cinema", "deep", "float", "glass"].includes(c.frame.template) && (
            <details open>
              <summary>
                <span>画框尺寸</span>
                <small>FRAME</small>
              </summary>
              <label className="field">
                布局
                <select
                  value={c.frame.layout}
                  onChange={(e) => set("frame", "layout", e.target.value)}
                >
                  <option value="auto_fit">自动适配</option>
                  <option value="fill">填充</option>
                  <option value="manual">手动</option>
                </select>
              </label>
              <label className="field">
                材质
                <select
                  value={c.frame.material}
                  onChange={(e) => set("frame", "material", e.target.value)}
                >
                  {[
                    ["gold", "金色"],
                    ["brushed_metal", "拉丝金属"],
                    ["black_titanium", "黑钛"],
                    ["lacquer", "漆面"],
                    ["glass", "玻璃"],
                    ["emissive", "发光"],
                  ].map(([v, t]) => (
                    <option key={v} value={v}>
                      {t}
                    </option>
                  ))}
                </select>
              </label>
              {n(
                "画框比例",
                c.frame.scale,
                (v) => set("frame", "scale", v),
                0.05,
              )}
              {n("虚拟纵深 m", c.frame.virtual_depth_m, (v) =>
                set("frame", "virtual_depth_m", v),
              )}
              {n("空间纵深 m", c.frame.portal_depth_m, (v) =>
                set("frame", "portal_depth_m", v),
              )}
              <label className="check">
                <input
                  type="checkbox"
                  checked={c.frame.edge_light}
                  onChange={(e) => set("frame", "edge_light", e.target.checked)}
                />{" "}
                边缘灯光
              </label>
              <div className="double">
                {n("宽度 m", c.frame.width_m, (v) =>
                  set("frame", "width_m", v),
                )}
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
          )}
        </aside>
        <section className="center">
          <div className="workspacehead">
            <div>
              <div className="eyebrow">
                CREATIVE WORKSPACE <span> / 画面预览</span>
              </div>
              <h1>
                图片空间<span>展示</span>
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
          {["simulation_alpha", "led_crop"].includes(tab) && (
            <div className="preview-options">
              背景：
              {[
                ["light", "浅色"],
                ["dark", "深色"],
                ["checker", "透明棋盘"],
              ].map(([id, label]) => (
                <button
                  key={id}
                  onClick={() => setBackground(id)}
                  aria-pressed={background === id}
                >
                  {label}
                </button>
              ))}{" "}
              {tab === "led_crop" && <span>裁切预览，并非实际播放尺寸</span>}
            </div>
          )}
          <div
            className={
              "viewport " +
              (["simulation_alpha", "led_crop"].includes(tab)
                ? "alpha-" + background
                : "")
            }
          >
            {tab === "photo" ? (
              <div className="photo-tools">
                <p>手动配准预览 · 未现场校准</p>
                <label>
                  选择现场照片{" "}
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => {
                      if (photo) URL.revokeObjectURL(photo);
                      const f = e.target.files?.[0];
                      setPhoto(f ? URL.createObjectURL(f) : "");
                    }}
                  />
                </label>
                {photo && (
                  <div className="photo-stage">
                    <img src={photo} alt="用户选择的照片" />
                    {job?.outputs?.simulation_alpha && (
                      <img
                        className="photo-overlay"
                        src={job.outputs.simulation_alpha}
                        alt="手动配准的模拟画面"
                        style={{
                          left: placement.x + "%",
                          top: placement.y + "%",
                          width: placement.scale + "%",
                          opacity: placement.opacity / 100,
                        }}
                      />
                    )}
                  </div>
                )}
                {photo &&
                  (
                    [
                      ["x", "水平位置"],
                      ["y", "垂直位置"],
                      ["scale", "大小"],
                      ["opacity", "透明度"],
                    ] as const
                  ).map(([k, label]) => (
                    <label key={k}>
                      {label}
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={placement[k]}
                        onChange={(e) =>
                          setPlacement({ ...placement, [k]: +e.target.value })
                        }
                      />
                      {professional && (
                        <input
                          type="number"
                          value={placement[k]}
                          onChange={(e) =>
                            setPlacement({ ...placement, [k]: +e.target.value })
                          }
                        />
                      )}
                    </label>
                  ))}
              </div>
            ) : tab === "orbit" ? (
              job?.outputs?.model ? (
                <React.Suspense
                  fallback={<div className="empty">正在加载 3D 查看器…</div>}
                >
                  <Orbit
                    url={job.outputs.model}
                    composition={(job.metrics as any)?.artwork?.composition}
                  />
                </React.Suspense>
              ) : (
                <div className="empty">完成渲染后可查看真实导出的 3D 场景</div>
              )
            ) : tab === "original" && localURL && !job?.outputs?.original ? (
              <img src={localURL} alt="本地原始画作" />
            ) : job?.outputs?.[tab] ? (
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
                    : "上传图片并选择风格后，开始创建图片空间。"}
                </p>
              </div>
            )}
            {tab === "orbit" && (
              <div className="orbit-caption">
                几何检查 · 最终光照以 Blender 为准
              </div>
            )}
            <div className="viewportmeta">
              <span>PREVIEW / {tab.toUpperCase()}</span>
              <span>BUPT · IMAGE SPACE</span>
            </div>
          </div>
          {job?.outputs?.original && job?.outputs?.simulation && (
            <details className="compare">
              <summary>原画 / 模拟效果对照</summary>
              <div>
                <figure>
                  <img src={job.outputs.original} alt="原画" />
                  <figcaption>原画</figcaption>
                </figure>
                <figure>
                  <img src={job.outputs.simulation} alt="模拟效果" />
                  <figcaption>模拟效果</figcaption>
                </figure>
              </div>
            </details>
          )}
          <div className="statusline">
            <div>
              <span className="statusdot" />{" "}
              {job
                ? `${({ queued: "排队中", running: "渲染中", completed: "已完成", done: "已完成", failed: "失败", error: "错误", validation_failed: "验证未通过" } as Record<string, string>)[job.status] || job.status} · ${Math.round(job.progress <= 1 ? job.progress * 100 : job.progress)}%`
                : "准备就绪"}{" "}
              {job?.status === "running" && (
                <span aria-live="polite">
                  {" · "}{job.stage}{" · "}{job.detail}
                  {job.elapsed_seconds !== undefined && ` · 已用时 ${Math.floor(job.elapsed_seconds / 60)}分${job.elapsed_seconds % 60}秒`}
                  {" · 阶段估算"}
                </span>
              )}
              {job?.error && <span className="error"> · {job.error}</span>}
            </div>
            <span>
              结果比例 {snapshot?.render.scale ?? "—"} · 完整画布{" "}
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
          {professional && (
            <>
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
                  {n(
                    "帧率 fps",
                    c.render.fps,
                    (v) => set("render", "fps", v),
                    1,
                  )}
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
              <label className="check">
                <input
                  type="checkbox"
                  checked={c.render.animation}
                  onChange={(e) =>
                    setC((old) =>
                      old
                        ? {
                            ...old,
                            render: {
                              ...old.render,
                              animation: e.target.checked,
                              light_sweep: e.target.checked
                                ? old.render.light_sweep
                                : false,
                            },
                          }
                        : old,
                    )
                  }
                />{" "}
                动画
              </label>
              {!isAutumn && (
              <label className="check">
                <input
                  type="checkbox"
                  checked={c.render.light_sweep}
                  onChange={(e) =>
                    setC((old) =>
                      old
                        ? {
                            ...old,
                            render: {
                              ...old.render,
                              light_sweep: e.target.checked,
                              animation:
                                e.target.checked || old.render.animation,
                            },
                          }
                        : old,
                    )
                  }
                />{" "}
                边缘扫光（启用三维序列）
              </label>
              )}
            </>
          )}
          <button
            className="secondary"
            disabled={
              !file ||
              busy ||
              !!(job && ["queued", "running"].includes(job.status))
            }
            onClick={() => submit("quick")}
          >
            快速预览
          </button>
          <button
            className="secondary"
            disabled={
              !file ||
              busy ||
              !!(job && ["queued", "running"].includes(job.status))
            }
            onClick={() => submit("high")}
          >
            高质量预览
          </button>
          <button
            className="secondary"
            disabled={
              !file ||
              busy ||
              !!(job && ["queued", "running"].includes(job.status))
            }
            onClick={() => submit("motion")}
          >
            {isAutumn ? "动态测试 · 低清7.5秒" : "动态测试 · 低清2秒"}
          </button>
          <button
            className="render"
            disabled={
              !file ||
              busy ||
              !!(job && ["queued", "running"].includes(job.status))
            }
            onClick={() => submit("formal")}
          >
            <Play size={15} fill="currentColor" /> 正式导出 <span>↗</span>
          </button>
          <p className="rendernote">渲染将在本机执行</p>
          <div className="config-actions">
            <button onClick={() => configAction("/api/settings", "PUT", c)}>
              保存配置
            </button>
            <button onClick={() => configAction("/api/settings")}>
              恢复已保存
            </button>
            <button onClick={() => configAction("/api/settings/reset", "POST")}>
              重置默认
            </button>
            <button
              onClick={() => {
                const a = document.createElement("a");
                a.href = URL.createObjectURL(
                  new Blob([JSON.stringify(c, null, 2)], {
                    type: "application/json",
                  }),
                );
                a.download = "frame-config.json";
                a.click();
                URL.revokeObjectURL(a.href);
              }}
            >
              下载 JSON
            </button>
            <label>
              导入 JSON
              <input
                type="file"
                accept="application/json,.json"
                onChange={async (e) => {
                  try {
                    const f = e.target.files?.[0];
                    if (f)
                      await configAction(
                        "/api/config/validate",
                        "POST",
                        JSON.parse(await f.text()),
                      );
                  } catch (err) {
                    setError(String(err));
                  }
                  e.target.value = "";
                }}
              />
            </label>
          </div>
          <div className="bottom">
            <div>
              <div className="eyebrow">OUTPUT / 输出文件</div>
              <h3>渲染结果</h3>
              <p className="muted">完成后可预览并下载生成的文件。</p>
            </div>
            <div className="downloads">
              {job?.outputs ? (
                Object.entries(job.outputs)
                  .filter(
                    ([k]) =>
                      professional ||
                      [
                        "original",
                        "scene",
                        "simulation_alpha",
                        "led_crop",
                        "atlas",
                        "blend",
                        "video",
                      ].includes(k),
                  )
                  .map(([k, v]) => (
                    <a key={k} href={v} download>
                      <Download size={14} />
                      {(
                        {
                          original: "原图",
                          scene: "场景",
                          atlas: "展开图",
                          simulation: "模拟图",
                          simulation_alpha: "透明模拟图",
                          led_crop: "LED 裁切预览",
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
                      .then((j) => {
                        setJob(j);
                        setSnapshot(null);
                        if (j.outputs?.config)
                          fetch(j.outputs.config)
                            .then((r) => r.json())
                            .then(setSnapshot)
                            .catch(() => {});
                      })
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
