'use client';

import React, { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useSimulationClock } from './SimulationContext';
import { getCoachTexture, getNoseTexture } from './trainTextures';

interface VandeBharatTrainModelProps {
  wheelRotation?: number;
  isSelected?: boolean;
  showTelemetry?: boolean;
  lighting?: 'dawn' | 'night' | 'overcast';
  trackZ?: number;
  onSelectTrain?: () => void;
}

/**
 * ---------------------------------------------------------------------------
 * UNIFIED MATHEMATICAL RAILWAY PROFILE
 * Evaluates the continuous, smooth cross-section shared identically by
 * both the coach body and the aerodynamic nose at the bulkhead transition.
 * ---------------------------------------------------------------------------
 */
function evalCrossSection(
  theta: number,
  w: number = 1.58,
  hTop: number = 1.35,
  hBot: number = 1.10,
  yMid: number = 1.10
): { z: number; y: number } {
  const cosT = Math.cos(theta);
  const sinT = Math.sin(theta);
  let z: number;
  let y: number;

  if (sinT >= 0) {
    // Upper body and smooth arched roof
    z = w * Math.sign(cosT) * Math.pow(Math.abs(cosT), 0.85);
    y = yMid + hTop * Math.pow(sinT, 1.3);
  } else {
    // Smooth aerodynamic lower skirt
    z = w * Math.sign(cosT) * Math.pow(Math.abs(cosT), 0.70);
    y = yMid + hBot * sinT;
  }
  return { z, y };
}

/**
 * ---------------------------------------------------------------------------
 * 1. SEAMLESS COACH BODYSHELL GEOMETRY
 * Extruded single-mesh continuous fuselage with smooth vertex normals.
 * ---------------------------------------------------------------------------
 */
function createCoachGeometry(
  length: number = 20.0,
  segsPerimeter: number = 48,
  segsX: number = 20
): THREE.BufferGeometry {
  const geom = new THREE.BufferGeometry();
  const vertices: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];

  for (let i = 0; i <= segsX; i++) {
    const u = i / segsX;
    const x = -length / 2 + u * length;

    for (let j = 0; j <= segsPerimeter; j++) {
      const v = j / segsPerimeter;
      const theta = -Math.PI / 2 + v * 2 * Math.PI;
      const pt = evalCrossSection(theta);

      vertices.push(x, pt.y, pt.z);
      uvs.push(u, v);
    }
  }

  for (let i = 0; i < segsX; i++) {
    for (let j = 0; j < segsPerimeter; j++) {
      const a = i * (segsPerimeter + 1) + j;
      const b = (i + 1) * (segsPerimeter + 1) + j;
      const c = (i + 1) * (segsPerimeter + 1) + (j + 1);
      const d = i * (segsPerimeter + 1) + (j + 1);

      // Outward-facing winding order (CCW)
      indices.push(a, b, c);
      indices.push(a, c, d);
    }
  }

  geom.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
  geom.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geom.setIndex(indices);
  geom.computeVertexNormals();
  return geom;
}

/**
 * ---------------------------------------------------------------------------
 * 2. SEAMLESS AERODYNAMIC NOSE LOFT GEOMETRY
 * Continuous loft from bulkhead (U=0, matching coach cross-section exactly)
 * to aerodynamic nose apex (U=1). Zero ridges, zero concentric steps.
 * ---------------------------------------------------------------------------
 */
function createAerodynamicNoseGeometry(
  length: number = 3.6,
  segsU: number = 36,
  segsPerimeter: number = 48
): THREE.BufferGeometry {
  const geom = new THREE.BufferGeometry();
  const vertices: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];

  for (let i = 0; i <= segsU; i++) {
    const u = i / segsU; // 0 at bulkhead, 1 at tip
    const x = u * length;

    // Smooth aerodynamic profile evolution along length
    const scaleW = Math.max(0.04, 1.0 - 0.96 * Math.pow(u, 1.6));
    const scaleTop = Math.max(0.04, 1.0 - 0.94 * Math.pow(u, 1.8));
    const scaleBot = Math.max(0.04, 1.0 - 0.92 * Math.pow(u, 1.5));
    const yShift = -0.30 * Math.pow(u, 1.4);

    for (let j = 0; j <= segsPerimeter; j++) {
      const v = j / segsPerimeter;
      const theta = -Math.PI / 2 + v * 2 * Math.PI;
      const base = evalCrossSection(theta);

      let y: number;
      if (base.y >= 1.10) {
        y = 1.10 + (base.y - 1.10) * scaleTop + yShift;
      } else {
        y = 1.10 + (base.y - 1.10) * scaleBot + yShift;
      }
      const z = base.z * scaleW;

      vertices.push(x, y, z);
      uvs.push(u, v);
    }
  }

  for (let i = 0; i < segsU; i++) {
    for (let j = 0; j < segsPerimeter; j++) {
      const a = i * (segsPerimeter + 1) + j;
      const b = (i + 1) * (segsPerimeter + 1) + j;
      const c = (i + 1) * (segsPerimeter + 1) + (j + 1);
      const d = i * (segsPerimeter + 1) + (j + 1);

      // Outward-facing winding order (CCW)
      indices.push(a, b, c);
      indices.push(a, c, d);
    }
  }

  geom.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
  geom.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geom.setIndex(indices);
  geom.computeVertexNormals();
  return geom;
}

/**
 * ---------------------------------------------------------------------------
 * AUTHENTIC STREAMLINED BROAD-GAUGE PASSENGER TRAINSET
 * (Vande Bharat Express — Orange & Platinum Silver Livery)
 * Smooth continuous painted panels with high-res textures, flush glazing,
 * seamless nose transition, and realistic 2-axle bogies.
 * ---------------------------------------------------------------------------
 */
export const VandeBharatTrainModel: React.FC<VandeBharatTrainModelProps> = ({
  wheelRotation = 0,
  lighting = 'dawn',
  trackZ = -2.0,
  onSelectTrain,
}) => {
  const clockRef = useSimulationClock();
  const rotatingWheelsRef = useRef<THREE.Group[]>([]);

  useFrame(() => {
    const clock = clockRef.current;
    const rot = clock ? clock.wheelRotation : wheelRotation;
    for (let i = 0; i < rotatingWheelsRef.current.length; i++) {
      const g = rotatingWheelsRef.current[i];
      if (g) g.rotation.z = rot;
    }
  });

  // Textures and geometries memoized
  const coachTexture = useMemo(() => getCoachTexture(), []);
  const noseTexture = useMemo(() => getNoseTexture(), []);

  const coachBodyGeom = useMemo(() => createCoachGeometry(20.0), []);
  const cabBodyGeom = useMemo(() => createCoachGeometry(17.5), []);
  const noseGeom = useMemo(() => createAerodynamicNoseGeometry(3.6), []);

  // Shared Physical Materials
  const materials = useMemo(() => {
    return {
      coachMaterial: new THREE.MeshStandardMaterial({
        map: coachTexture || undefined,
        color: coachTexture ? '#FFFFFF' : '#ECEFF1',
        roughness: 0.28,
        metalness: 0.35,
      }),
      noseMaterial: new THREE.MeshStandardMaterial({
        map: noseTexture || undefined,
        color: noseTexture ? '#FFFFFF' : '#ECEFF1',
        roughness: 0.25,
        metalness: 0.32,
      }),
      bogieDarkSteel: new THREE.MeshStandardMaterial({
        color: '#1E293B',
        roughness: 0.65,
        metalness: 0.75,
      }),
      wheelTreadSteel: new THREE.MeshStandardMaterial({
        color: '#CBD5E1',
        roughness: 0.15,
        metalness: 0.95,
      }),
      gangwayRubber: new THREE.MeshStandardMaterial({
        color: '#0B0F19',
        roughness: 0.90,
        metalness: 0.10,
      }),
      couplerKnuckle: new THREE.MeshStandardMaterial({
        color: '#334155',
        roughness: 0.45,
        metalness: 0.85,
      }),
      headlampLens: new THREE.MeshBasicMaterial({
        color: '#FFFFFF',
      }),
      pantographSteel: new THREE.MeshStandardMaterial({
        color: '#64748B',
        roughness: 0.35,
        metalness: 0.85,
      }),
      insulatorCeramic: new THREE.MeshStandardMaterial({
        color: '#7F1D1D',
        roughness: 0.35,
        metalness: 0.10,
      }),
      skirtDark: new THREE.MeshStandardMaterial({
        color: '#1E293B',
        roughness: 0.65,
        metalness: 0.40,
      }),
    };
  }, [coachTexture, noseTexture]);

  // Elevation setup: Rail running top is at Y = 0.28m
  // Wheel radius = 0.457m (914mm diameter), Axle center = 0.28 + 0.457 = 0.737m
  // Coach body base sits at Y = 0.65m
  const railTopY = 0.28;
  const wheelRadius = 0.457;
  const wheelAxleY = railTopY + wheelRadius;
  const bodyBaseY = 0.65;

  // ---------------------------------------------------------------------------
  // HELPER: 2-AXLE HIGH-SPEED EMU BOGIE
  // ---------------------------------------------------------------------------
  const renderBogie = (key: string, xPos: number) => {
    const axleSpacing = 2.4;
    const axleOffsets = [-axleSpacing / 2, axleSpacing / 2];
    const halfGauge = 1.676 / 2;

    return (
      <group key={key} position={[xPos, 0, 0]}>
        {/* Main Cast Steel Bogie Bolster Frame */}
        <mesh position={[0, wheelAxleY + 0.12, 0]} material={materials.bogieDarkSteel}>
          <boxGeometry args={[3.2, 0.22, 2.30]} />
        </mesh>
        {/* Secondary Air Springs */}
        <mesh position={[0, wheelAxleY + 0.26, -0.92]} material={materials.bogieDarkSteel}>
          <cylinderGeometry args={[0.22, 0.22, 0.20, 16]} />
        </mesh>
        <mesh position={[0, wheelAxleY + 0.26, 0.92]} material={materials.bogieDarkSteel}>
          <cylinderGeometry args={[0.22, 0.22, 0.20, 16]} />
        </mesh>

        {/* Dual Wheelsets seated tangent to rail head */}
        {axleOffsets.map((aOff, aIdx) => (
          <group key={`axle-${aIdx}`} position={[aOff, wheelAxleY, 0]}>
            {/* Solid Steel Axle */}
            <mesh rotation={[Math.PI / 2, 0, 0]} material={materials.bogieDarkSteel}>
              <cylinderGeometry args={[0.075, 0.075, 2.15, 16]} />
            </mesh>
            {/* Axle Box & Primary Spring Suspension */}
            <mesh position={[0, 0, -1.08]} material={materials.bogieDarkSteel}>
              <boxGeometry args={[0.32, 0.32, 0.18]} />
            </mesh>
            <mesh position={[0, 0, 1.08]} material={materials.bogieDarkSteel}>
              <boxGeometry args={[0.32, 0.32, 0.18]} />
            </mesh>

            {/* Rotating Steel Wheels */}
            <group
              ref={(el) => {
                if (el && !rotatingWheelsRef.current.includes(el)) {
                  rotatingWheelsRef.current.push(el);
                }
              }}
            >
              {/* Left Wheel (UP MAIN Left Rail) */}
              <group position={[0, 0, -halfGauge]}>
                <mesh rotation={[Math.PI / 2, 0, 0]} material={materials.wheelTreadSteel}>
                  <cylinderGeometry args={[wheelRadius, wheelRadius, 0.13, 24]} />
                </mesh>
                <mesh position={[0, 0, -0.05]} rotation={[Math.PI / 2, 0, 0]} material={materials.bogieDarkSteel}>
                  <cylinderGeometry args={[wheelRadius + 0.032, wheelRadius + 0.032, 0.025, 24]} />
                </mesh>
              </group>
              {/* Right Wheel (UP MAIN Right Rail) */}
              <group position={[0, 0, halfGauge]}>
                <mesh rotation={[Math.PI / 2, 0, 0]} material={materials.wheelTreadSteel}>
                  <cylinderGeometry args={[wheelRadius, wheelRadius, 0.13, 24]} />
                </mesh>
                <mesh position={[0, 0, 0.05]} rotation={[Math.PI / 2, 0, 0]} material={materials.bogieDarkSteel}>
                  <cylinderGeometry args={[wheelRadius + 0.032, wheelRadius + 0.032, 0.025, 24]} />
                </mesh>
              </group>
            </group>
          </group>
        ))}
      </group>
    );
  };

  // ---------------------------------------------------------------------------
  // HELPER: STREAMLINED PASSENGER COACH (SMOOTH PAINTED PANELS)
  // ---------------------------------------------------------------------------
  const renderCoach = (
    key: string,
    xPos: number,
    hasPantograph: boolean = false,
    isLastCar: boolean = false
  ) => {
    const coachLength = 20.0;

    return (
      <group key={key} position={[xPos, 0, 0]}>
        {/* Inter-Coach Articulated Rubber Gangway Bellows */}
        {!isLastCar && (
          <mesh position={[-coachLength / 2 - 0.45, bodyBaseY + 1.15, 0]} material={materials.gangwayRubber}>
            <boxGeometry args={[0.90, 2.30, 1.70]} />
          </mesh>
        )}

        {/* Seamless Extruded Bodyshell with Painted UV Livery (Zero Corrugation!) */}
        <group position={[0, bodyBaseY, 0]}>
          <mesh geometry={coachBodyGeom} material={materials.coachMaterial} castShadow />
        </group>

        {/* Lower Aerodynamic Underbody Skirting & Battery Enclosure */}
        <mesh position={[0, bodyBaseY - 0.12, 0]} material={materials.skirtDark}>
          <boxGeometry args={[coachLength - 0.8, 0.24, 2.85]} />
        </mesh>

        {/* Aerodynamic Roof HVAC Fairing Pods */}
        <group position={[-4.5, bodyBaseY + 2.45, 0]}>
          <mesh material={materials.coachMaterial} castShadow>
            <boxGeometry args={[3.2, 0.28, 1.8]} />
          </mesh>
        </group>
        <group position={[4.5, bodyBaseY + 2.45, 0]}>
          <mesh material={materials.coachMaterial} castShadow>
            <boxGeometry args={[3.2, 0.28, 1.8]} />
          </mesh>
        </group>

        {/* High-Speed Single-Arm Pantograph contacting OHE Contact Wire (Y = 5.35m) */}
        {hasPantograph && (
          <group position={[0, bodyBaseY + 2.45, 0]}>
            <mesh position={[-0.8, 0.08, -0.6]} material={materials.insulatorCeramic}>
              <cylinderGeometry args={[0.07, 0.07, 0.16, 8]} />
            </mesh>
            <mesh position={[-0.8, 0.08, 0.6]} material={materials.insulatorCeramic}>
              <cylinderGeometry args={[0.07, 0.07, 0.16, 8]} />
            </mesh>
            <mesh position={[0.8, 0.08, -0.6]} material={materials.insulatorCeramic}>
              <cylinderGeometry args={[0.07, 0.07, 0.16, 8]} />
            </mesh>
            <mesh position={[0.8, 0.08, 0.6]} material={materials.insulatorCeramic}>
              <cylinderGeometry args={[0.07, 0.07, 0.16, 8]} />
            </mesh>

            {/* Base Mounting Frame */}
            <mesh position={[0, 0.16, 0]} material={materials.pantographSteel}>
              <boxGeometry args={[2.0, 0.05, 1.4]} />
            </mesh>
            {/* Lower Articulated Arm */}
            <mesh position={[0.45, 0.72, 0]} rotation={[0, 0, -0.68]} material={materials.pantographSteel}>
              <cylinderGeometry args={[0.032, 0.032, 1.5, 8]} />
            </mesh>
            {/* Upper Articulated Arm reaching Y = 5.35m */}
            <mesh position={[-0.15, 1.42, 0]} rotation={[0, 0, 0.58]} material={materials.pantographSteel}>
              <cylinderGeometry args={[0.026, 0.026, 1.4, 8]} />
            </mesh>
            {/* Carbon Collector Strip */}
            <group position={[-0.55, 1.78, 0]}>
              <mesh material={materials.pantographSteel}>
                <boxGeometry args={[0.16, 0.035, 1.85]} />
              </mesh>
            </group>
          </group>
        )}

        {/* Two 2-Axle Bogies */}
        {renderBogie(`${key}-bogie-f`, coachLength / 2 - 3.4)}
        {renderBogie(`${key}-bogie-r`, -coachLength / 2 + 3.4)}
      </group>
    );
  };

  const cabBodyLength = 17.5;

  return (
    <group
      position={[0, 0, trackZ]}
      onClick={(e) => {
        if (onSelectTrain) {
          e.stopPropagation();
          onSelectTrain();
        }
      }}
    >
      {/* ==================================================================== */}
      {/* 1. LEAD CAB CAR (SEAMLESS BULLET NOSE + PANORAMIC WINDSHIELD)        */}
      {/* ==================================================================== */}
      <group position={[0, 0, 0]}>
        {/* Cab Car Cylindrical / Extruded Bodyshell */}
        <group position={[0, bodyBaseY, 0]}>
          <mesh geometry={cabBodyGeom} material={materials.coachMaterial} castShadow />
        </group>

        {/* Lower Aerodynamic Underbody Skirting */}
        <mesh position={[0, bodyBaseY - 0.12, 0]} material={materials.skirtDark}>
          <boxGeometry args={[cabBodyLength - 0.8, 0.24, 2.85]} />
        </mesh>

        {/* Rear Inter-Coach Gangway Bellows */}
        <mesh position={[-cabBodyLength / 2 - 0.45, bodyBaseY + 1.15, 0]} material={materials.gangwayRubber}>
          <boxGeometry args={[0.90, 2.30, 1.70]} />
        </mesh>

        {/* Two Bogies for Cab Car */}
        {renderBogie('cab-bogie-f', cabBodyLength / 2 - 3.8)}
        {renderBogie('cab-bogie-r', -cabBodyLength / 2 + 3.2)}

        {/* ------------------------------------------------------------------ */}
        {/* SEAMLESS CONTINUOUS AERODYNAMIC BULLET NOSE                        */}
        {/* 100% matched cross section at U=0, zero concentric ridges, smooth  */}
        {/* anti-aliased orange mask & raked panoramic cockpit visor           */}
        {/* ------------------------------------------------------------------ */}
        <group position={[cabBodyLength / 2, bodyBaseY, 0]}>
          <mesh geometry={noseGeom} material={materials.noseMaterial} castShadow />

          {/* Recessed Cast-Steel Scharfenberg Automatic Coupler in Chin Pocket */}
          <group position={[3.55, -0.20, 0]}>
            <mesh material={materials.couplerKnuckle}>
              <boxGeometry args={[0.20, 0.15, 0.25]} />
            </mesh>
            <mesh position={[0.10, 0, 0]} rotation={[0, 0, Math.PI / 2]} material={materials.couplerKnuckle}>
              <cylinderGeometry args={[0.055, 0.065, 0.14, 12]} />
            </mesh>
          </group>

          {/* Driver Windshield Wiper */}
          <group position={[1.40, 1.82, 0.08]} rotation={[0.34, -0.10, 0.38]}>
            <mesh material={materials.couplerKnuckle}>
              <boxGeometry args={[0.02, 0.75, 0.015]} />
            </mesh>
          </group>

          {/* Forward Track Illumination from Cheek Headlamp Clusters */}
          <pointLight
            color="#FFFBEB"
            intensity={lighting === 'night' ? 7.0 : 4.5}
            distance={24}
            position={[2.8, 0.65, 0.70]}
          />
          <pointLight
            color="#FFFBEB"
            intensity={lighting === 'night' ? 7.0 : 4.5}
            distance={24}
            position={[2.8, 0.65, -0.70]}
          />
        </group>
      </group>

      {/* ==================================================================== */}
      {/* 2. CONNECTED COACHES IN RAKE (16-Car EMU Formation)                 */}
      {/* ==================================================================== */}
      {renderCoach('coach-01', -19.2, true, false)}
      {renderCoach('coach-02', -39.6, false, false)}
      {renderCoach('coach-03', -60.0, false, false)}
      {renderCoach('coach-04', -80.4, true, false)}
      {renderCoach('coach-05', -100.8, false, true)}
    </group>
  );
};
