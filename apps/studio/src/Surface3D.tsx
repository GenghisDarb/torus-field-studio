import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { colorAsRgb, metricValue } from "./palette";
import type { FieldPoint, FieldTable, Metric } from "./types";

interface Props {
  table: FieldTable;
  metric: Metric;
  selected: FieldPoint | null;
  showRaw: boolean;
}

export function Surface3D({ table, metric, selected, showRaw }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [contextLost, setContextLost] = useState(false);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#081317");
    scene.fog = new THREE.Fog("#081317", 6.5, 13);
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 50);
    camera.position.set(5.6, 4.4, 6.6);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.appendChild(renderer.domElement);
    const handleContextLost = (event: Event) => {
      event.preventDefault();
      setContextLost(true);
    };
    const handleContextRestored = () => setContextLost(false);
    renderer.domElement.addEventListener("webglcontextlost", handleContextLost);
    renderer.domElement.addEventListener("webglcontextrestored", handleContextRestored);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.055;
    controls.minDistance = 4;
    controls.maxDistance = 13;
    controls.target.set(0, 0, 0.45);

    const positions: number[] = [];
    const colors: number[] = [];
    for (const point of table.points) {
      const x = (point.grid_x / Math.max(1, table.width - 1) - 0.5) * 7;
      const y = (0.5 - point.grid_y / Math.max(1, table.height - 1)) * 4.8;
      const z = metricValue(point, metric) * 2.3 - 0.8;
      positions.push(x, z, y);
      colors.push(...colorAsRgb(point, metric));
    }
    const indices: number[] = [];
    for (let y = 0; y < table.height - 1; y += 1) {
      for (let x = 0; x < table.width - 1; x += 1) {
        const a = y * table.width + x;
        const b = a + 1;
        const c = a + table.width;
        const d = c + 1;
        indices.push(a, c, b, b, c, d);
      }
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();
    const material = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.72,
      metalness: 0.08,
      side: THREE.DoubleSide,
      flatShading: false,
    });
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);
    if (showRaw) {
      const pointMaterial = new THREE.PointsMaterial({ size: 0.026, color: "#ecf4ee", transparent: true, opacity: 0.7 });
      scene.add(new THREE.Points(geometry, pointMaterial));
    }
    const grid = new THREE.GridHelper(7, 14, "#28545a", "#18363b");
    grid.position.y = -0.83;
    scene.add(grid);
    scene.add(new THREE.HemisphereLight("#dceceb", "#10292f", 2.2));
    const keyLight = new THREE.DirectionalLight("#f1c46e", 3.2);
    keyLight.position.set(3, 6, 4);
    scene.add(keyLight);

    let marker: THREE.Mesh | null = null;
    if (selected) {
      const pointPosition = positions.slice(selected.index * 3, selected.index * 3 + 3);
      marker = new THREE.Mesh(
        new THREE.SphereGeometry(0.105, 24, 16),
        new THREE.MeshBasicMaterial({ color: "#fff2cf" }),
      );
      marker.position.set(pointPosition[0], pointPosition[1], pointPosition[2]);
      scene.add(marker);
    }
    const resize = () => {
      const width = host.clientWidth;
      const height = host.clientHeight;
      renderer.setSize(width, height, false);
      camera.aspect = width / Math.max(1, height);
      camera.updateProjectionMatrix();
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    let frame = 0;
    const animate = () => {
      controls.update();
      renderer.render(scene, camera);
      frame = requestAnimationFrame(animate);
    };
    animate();
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      geometry.dispose();
      material.dispose();
      marker?.geometry.dispose();
      (marker?.material as THREE.Material | undefined)?.dispose();
      renderer.domElement.removeEventListener("webglcontextlost", handleContextLost);
      renderer.domElement.removeEventListener("webglcontextrestored", handleContextRestored);
      renderer.dispose();
      if (host.contains(renderer.domElement)) host.removeChild(renderer.domElement);
    };
  }, [metric, selected, showRaw, table]);

  return (
    <div className="surface-frame">
      <div className="surface-host" ref={hostRef} aria-label="Interactive three-dimensional metric surface" />
      {contextLost && <div className="surface-context-notice" role="status">WebGL context lost. Waiting for the browser to restore the surface.</div>}
    </div>
  );
}
