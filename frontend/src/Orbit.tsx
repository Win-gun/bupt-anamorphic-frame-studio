import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
export function Orbit({ url }: { url: string }) {
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
    const renderer = new THREE.WebGLRenderer({ antialias: true });
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
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3()).length();
        controls.target.copy(center);
        camera.position
          .copy(center)
          .add(new THREE.Vector3(size * 0.8, size * 0.6, size));
        camera.near = Math.max(size / 1000, 0.001);
        camera.far = size * 20;
        camera.updateProjectionMatrix();
        controls.update();
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
          m.forEach((x) => x.dispose());
        }
      });
    };
  }, [url]);
  return (
    <div
      className="orbit"
      ref={host}
      aria-label="真实导出 3D 场景，拖动旋转，滚轮缩放"
    >
      {error && <p>{error}</p>}
    </div>
  );
}
