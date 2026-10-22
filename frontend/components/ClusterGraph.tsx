"use client";
import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

function Nodes({ n = 48 }: { n?: number }) {
  const group = useRef<THREE.Group>(null);
  const pts = useMemo(() => Array.from({ length: n }, (_, i) => {
    const phi = Math.acos(1 - 2 * (i + 0.5) / n), th = Math.PI * (1 + Math.sqrt(5)) * i;
    return new THREE.Vector3(Math.cos(th) * Math.sin(phi), Math.sin(th) * Math.sin(phi), Math.cos(phi)).multiplyScalar(2.2);
  }), [n]);
  const lines = useMemo(() => {
    const g = new THREE.BufferGeometry(); const v: number[] = [];
    pts.forEach((a, i) => pts.forEach((b, j) => { if (j > i && a.distanceTo(b) < 1.1) v.push(a.x, a.y, a.z, b.x, b.y, b.z); }));
    g.setAttribute("position", new THREE.Float32BufferAttribute(v, 3)); return g;
  }, [pts]);
  useFrame((_, dt) => { if (group.current) group.current.rotation.y += dt * 0.15; });
  return (
    <group ref={group}>
      {pts.map((p, i) => (
        <mesh key={i} position={p}><sphereGeometry args={[0.05, 12, 12]} />
          <meshBasicMaterial color={i % 11 === 0 ? "#f26b1d" : "#e8e8e8"} /></mesh>))}
      <lineSegments geometry={lines}><lineBasicMaterial color="#ffffff" transparent opacity={0.18} /></lineSegments>
    </group>);
}

export default function ClusterGraph() {
  return <div className="h-72 w-full"><Canvas camera={{ position: [0, 0, 6], fov: 50 }}><Nodes /></Canvas></div>;
}
