import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
export function Orbit({
  url,
  composition,
}: {
  url: string;
  composition?: {
    normal?: number[];
    right?: number[];
    up?: number[];
    center?: number[];
    width?: number;
    height?: number;
  };
}) {
  const reset = useRef<() => void>(() => {});
  const host = useRef<HTMLDivElement>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const el = host.current;
    if (!el) return;
    setError("");
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#17131c");
    const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 1000);
    camera.position.set(12, 8, 14);
    camera.up.set(0, 1, 0);
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true });
    } catch {
      setError("无法启动 3D 查看器，请检查浏览器 WebGL 支持。");
      return;
    }
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    el.appendChild(renderer.domElement);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x5a4b53, 2));
    const light = new THREE.DirectionalLight(0xffffff, 2);
    light.position.set(5, -8, 10);
    scene.add(light);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    let object: THREE.Object3D | undefined,
      disposed = false;
    new GLTFLoader().load(
      url,
      (g) => {
        if (disposed) return;
        object = g.scene;
        scene.add(object);
        const box = new THREE.Box3().setFromObject(object);
        const size = box.getSize(new THREE.Vector3());
        const basis = composition || g.scene.userData?.composition_basis || {};
        const cv = (v: number[] | undefined, fallback: THREE.Vector3) =>
          v?.length === 3 ? new THREE.Vector3(v[0], v[2], -v[1]) : fallback;
        const center = cv(basis.center, box.getCenter(new THREE.Vector3()));
        const normal = cv(basis.normal, new THREE.Vector3(0, 0, 1)).normalize();
        const right = cv(basis.right, new THREE.Vector3(1, 0, 0)).normalize();
        const up = cv(basis.up, new THREE.Vector3(0, 1, 0)).normalize();
        const direction = normal
          .clone()
          .addScaledVector(right, 0.2)
          .addScaledVector(up, 0.15)
          .normalize();
        const aspect = Math.max(
          el.clientWidth / Math.max(el.clientHeight, 1),
          0.2,
        );
        const posterSpan = Math.max(
          ((basis.width || 0) * 1.35) / aspect,
          (basis.height || 0) * 1.35,
        );
        const distance = posterSpan
          ? posterSpan /
            (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)))
          : Math.max(size.x, size.y, size.z) * 1.5;
        reset.current = () => {
          controls.enableDamping = false;
          controls.update();
          camera.up.copy(up);
          controls.target.copy(center);
          camera.position.copy(center).addScaledVector(direction, distance);
          controls.update();
          controls.enableDamping = true;
        };
        camera.near = Math.max(distance / 30, 0.02);
        camera.far = Math.max(distance * 10, size.length() * 3);
        camera.updateProjectionMatrix();
        reset.current();
      },
      undefined,
      () => setError("无法加载导出的 3D 模型"),
    );
    const resize = () => {
      const w = el.clientWidth,
        h = el.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();
    let frame = 0;
    const draw = () => {
      frame = requestAnimationFrame(draw);
      controls.update();
      renderer.render(scene, camera);
    };
    draw();
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      ro.disconnect();
      controls.dispose();
      renderer.dispose();
      renderer.domElement.remove();
      object?.traverse((o) => {
        if (o instanceof THREE.Mesh) {
          o.geometry.dispose();
          const m = Array.isArray(o.material) ? o.material : [o.material];
          m.forEach((x) => {
            Object.values(x).forEach((v) => {
              if (v instanceof THREE.Texture) v.dispose();
            });
            x.dispose();
          });
        }
      });
    };
  }, [url, composition]);
  return (
    <div className="orbit-wrap">
      <button className="orbit-reset" onClick={() => reset.current()}>
        重置视角
      </button>
      <div
        className="orbit"
        ref={host}
        aria-label="真实导出 3D 场景，拖动旋转，滚轮缩放"
      >
        {error && <p>{error}</p>}
      </div>
    </div>
  );
}
