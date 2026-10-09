'use client';

import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface ProceduralTrainModelProps {
  speedKmh?: number;
  isPlaying?: boolean;
  onSelectTrain?: () => void;
  isSelected?: boolean;
  trackZ?: number; // Position on track (Z offset)
}

/**
 * High-Fidelity Procedural Model of a Modern High-Speed Passenger Train:
 * - Proportional 2-coach EMU rake with aerodynamic sloping bullet nose
 * - Flush-mounted driver cockpit windshield visor and integrated LED headlights
 * - Individual passenger windows with slim mullions, doors with grab handles
 * - Roof cantrail bevels, aerodynamic HVAC pods, and 25 kV AC single-arm pantograph
 * - Articulated corrugated rubber gangway between coaches
 * - Cast steel bogies with flanged wheels seated physically on rail heads
 * - Restrained, realistic livery: silver-white body, dark window band, TrackMeld blue cheatline
 */
export const ProceduralTrainModel: React.FC<ProceduralTrainModelProps> = ({
  speedKmh = 120,
  isPlaying = true,
  onSelectTrain,
  isSelected = false,
  trackZ = -2.0, // UP MAIN track
}) => {
  const trainGroupRef = useRef<THREE.Group>(null);
  const wheelsRef = useRef<THREE.Group[]>([]);

  // Physical railway PBR materials (realistic, restrained, non-glowing)
  const materials = useMemo(() => {
    return {
      bodyWhite: new THREE.MeshStandardMaterial({
        color: isSelected ? '#E0F2FE' : '#EAEEF4',
        metalness: 0.18,
        roughness: 0.32,
        envMapIntensity: 1.2,
      }),
      liveryBlue: new THREE.MeshStandardMaterial({
        color: '#0284C7',
        metalness: 0.35,
        roughness: 0.25,
      }),
      bodySkirt: new THREE.MeshStandardMaterial({
        color: '#0F172A',
        metalness: 0.60,
        roughness: 0.45,
      }),
      windowBand: new THREE.MeshStandardMaterial({
        color: '#0F172A',
        metalness: 0.85,
        roughness: 0.18,
      }),
      darkGlass: new THREE.MeshStandardMaterial({
        color: '#0A0F1D',
        metalness: 0.95,
        roughness: 0.05,
      }),
      interiorGlow: new THREE.MeshBasicMaterial({
        color: '#FEF3C7',
        transparent: true,
        opacity: 0.25,
      }),
      doorFrame: new THREE.MeshStandardMaterial({
        color: '#1E293B',
        metalness: 0.70,
        roughness: 0.35,
      }),
      chromeMetal: new THREE.MeshStandardMaterial({
        color: '#CBD5E1',
        metalness: 0.95,
        roughness: 0.15,
      }),
      steelWheels: new THREE.MeshStandardMaterial({
        color: '#CBD5E1',
        metalness: 0.96,
        roughness: 0.15,
      }),
      bogieSteel: new THREE.MeshStandardMaterial({
        color: '#1E293B',
        metalness: 0.75,
        roughness: 0.50,
      }),
      roofEquip: new THREE.MeshStandardMaterial({
        color: '#334155',
        metalness: 0.70,
        roughness: 0.35,
      }),
      pantographRed: new THREE.MeshStandardMaterial({
        color: '#DC2626',
        metalness: 0.70,
        roughness: 0.30,
      }),
      carbonStrip: new THREE.MeshStandardMaterial({
        color: '#0F172A',
        metalness: 0.90,
        roughness: 0.15,
      }),
      insulatorBrown: new THREE.MeshStandardMaterial({
        color: '#991B1B',
        roughness: 0.35,
      }),
      gangwayRubber: new THREE.MeshStandardMaterial({
        color: '#0A0E17',
        roughness: 0.95,
        metalness: 0.05,
      }),
      headlightGlow: new THREE.MeshBasicMaterial({
        color: '#FFFFFF',
      }),
      headlightHousing: new THREE.MeshStandardMaterial({
        color: '#1E293B',
        metalness: 0.80,
        roughness: 0.30,
      }),
    };
  }, [isSelected]);

  // Continuous aerodynamic bullet nose loft geometry with separated surface normals (no creases)
  const noseGeometries = useMemo(() => {
    // 6 cross-sectional stations defining the streamlined aerodynamic bullet nose
    // Station format: [x, yTop, yBottom, halfWidth]
    const stations = [
      [0.0, 3.82, 1.20, 1.55], // 0: Seamlessly flush with coach front face
      [1.2, 3.55, 1.20, 1.50], // 1: Cockpit roof transition
      [2.4, 3.05, 1.20, 1.38], // 2: Windshield brow / front cab slope
      [3.6, 2.35, 1.22, 1.12], // 3: Aerodynamic nose hood
      [4.5, 1.80, 1.25, 0.72], // 4: Front wedge collar
      [5.1, 1.52, 1.28, 0.40], // 5: Front nose cap base
    ];

    const vertices: number[] = [];
    const indices: number[] = [];

    // Helper to push a quad face with 2 triangles
    const addQuad = (v0: number[], v1: number[], v2: number[], v3: number[]) => {
      const baseIdx = vertices.length / 3;
      vertices.push(...v0, ...v1, ...v2, ...v3);
      indices.push(baseIdx, baseIdx + 1, baseIdx + 2);
      indices.push(baseIdx, baseIdx + 2, baseIdx + 3);
    };

    // Helper to push a triangle
    const addTri = (v0: number[], v1: number[], v2: number[]) => {
      const baseIdx = vertices.length / 3;
      vertices.push(...v0, ...v1, ...v2);
      indices.push(baseIdx, baseIdx + 1, baseIdx + 2);
    };

    for (let i = 0; i < stations.length - 1; i++) {
      const [x0, yt0, yb0, hw0] = stations[i];
      const [x1, yt1, yb1, hw1] = stations[i + 1];

      // Top Roof Face (pointing +Y)
      addQuad(
        [x0, yt0, hw0],
        [x1, yt1, hw1],
        [x1, yt1, -hw1],
        [x0, yt0, -hw0]
      );

      // Left Side Wall Face (+Z, pointing +Z)
      addQuad(
        [x0, yb0, hw0],
        [x1, yb1, hw1],
        [x1, yt1, hw1],
        [x0, yt0, hw0]
      );

      // Right Side Wall Face (-Z, pointing -Z)
      addQuad(
        [x0, yt0, -hw0],
        [x1, yt1, -hw1],
        [x1, yb1, -hw1],
        [x0, yb0, -hw0]
      );

      // Bottom Underside Face (pointing -Y)
      addQuad(
        [x0, yb0, -hw0],
        [x1, yb1, -hw1],
        [x1, yb1, hw1],
        [x0, yb0, hw0]
      );
    }

    // Front Nose Cap: Apex point at [5.45, 1.45, 0]
    const apex = [5.45, 1.45, 0];
    const [xLast, ytLast, ybLast, hwLast] = stations[stations.length - 1];

    // Top cap triangle
    addTri([xLast, ytLast, hwLast], apex, [xLast, ytLast, -hwLast]);
    // Left cap triangle
    addTri([xLast, ybLast, hwLast], apex, [xLast, ytLast, hwLast]);
    // Right cap triangle
    addTri([xLast, ytLast, -hwLast], apex, [xLast, ybLast, -hwLast]);
    // Bottom cap triangle
    addTri([xLast, ybLast, -hwLast], apex, [xLast, ybLast, hwLast]);

    const bodyGeom = new THREE.BufferGeometry();
    bodyGeom.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    bodyGeom.setIndex(indices);
    bodyGeom.computeVertexNormals();

    // Electric blue livery cheatline flowing into the nose
    const cheatlineVerts = [
      0.0, 1.62, 1.56,
      0.0, 1.46, 1.56,
      4.5, 1.46, 0.74,
      4.5, 1.62, 0.74,

      0.0, 1.62, -1.56,
      0.0, 1.46, -1.56,
      4.5, 1.46, -0.74,
      4.5, 1.62, -0.74,
    ];
    const cheatlineIndices = [
      0, 1, 2,
      0, 2, 3,
      4, 6, 5,
      4, 7, 6,
    ];
    const cheatlineGeom = new THREE.BufferGeometry();
    cheatlineGeom.setAttribute('position', new THREE.Float32BufferAttribute(cheatlineVerts, 3));
    cheatlineGeom.setIndex(cheatlineIndices);
    cheatlineGeom.computeVertexNormals();

    return { bodyGeom, cheatlineGeom };
  }, []);

  // Motion controller: gentle, cinematic forward cruise with wheel rotation
  useFrame((_, delta) => {
    if (!trainGroupRef.current) return;

    if (isPlaying) {
      const visualSpeed = Math.max((speedKmh / 3.6) * 0.12, 1.5);
      trainGroupRef.current.position.x += visualSpeed * delta;

      // Smooth loop: keep nose and lead coach permanently framed in the right-center 35-40%
      if (trainGroupRef.current.position.x > 5.0) {
        trainGroupRef.current.position.x = -3.0;
      }

      // Rotate wheelsets synchronously with linear distance traveled (wheel radius = 0.45m)
      const wheelAngularSpeed = (visualSpeed / 0.45) * delta;
      wheelsRef.current.forEach((wheelGroup) => {
        if (wheelGroup) {
          wheelGroup.rotation.z -= wheelAngularSpeed;
        }
      });
    }
  });

  // Track & wheel geometry constants
  const trackGauge = 1.676; // Broad gauge distance between rail centers
  const railTopY = 0.42;    // Rails sit from Y = 0.20 to Y = 0.42
  const wheelRadius = 0.45;
  const axleY = railTopY + wheelRadius; // Exactly 0.87m above ground
  const axleSpacing = 2.2;

  // Helper to build a 2-axle suspension Bogie (Truck) resting physically on rails
  const renderBogie = (key: string, xPos: number) => {
    return (
      <group key={key} position={[xPos, 0, 0]}>
        {/* Main Cast Steel H-Frame */}
        <mesh material={materials.bogieSteel} position={[0, axleY + 0.08, 0]}>
          <boxGeometry args={[3.0, 0.22, trackGauge + 0.40]} />
        </mesh>

        {/* Secondary Air Suspension Bellows */}
        <mesh material={materials.gangwayRubber} position={[0, axleY + 0.28, -(trackGauge / 2 + 0.16)]}>
          <cylinderGeometry args={[0.22, 0.24, 0.30, 16]} />
        </mesh>
        <mesh material={materials.gangwayRubber} position={[0, axleY + 0.28, trackGauge / 2 + 0.16]}>
          <cylinderGeometry args={[0.22, 0.24, 0.30, 16]} />
        </mesh>

        {/* Axle 1 (Front Axle) */}
        <group
          position={[axleSpacing / 2, axleY, 0]}
          ref={(el) => {
            if (el && !wheelsRef.current.includes(el)) wheelsRef.current.push(el);
          }}
        >
          {/* Steel Axle Shaft */}
          <mesh material={materials.steelWheels} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.075, 0.075, trackGauge, 16]} />
          </mesh>
          {/* Left Wheel */}
          <mesh material={materials.steelWheels} position={[0, 0, -trackGauge / 2]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[wheelRadius, wheelRadius, 0.14, 24]} />
          </mesh>
          {/* Right Wheel */}
          <mesh material={materials.steelWheels} position={[0, 0, trackGauge / 2]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[wheelRadius, wheelRadius, 0.14, 24]} />
          </mesh>
        </group>

        {/* Axle 2 (Rear Axle) */}
        <group
          position={[-axleSpacing / 2, axleY, 0]}
          ref={(el) => {
            if (el && !wheelsRef.current.includes(el)) wheelsRef.current.push(el);
          }}
        >
          {/* Steel Axle Shaft */}
          <mesh material={materials.steelWheels} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.075, 0.075, trackGauge, 16]} />
          </mesh>
          {/* Left Wheel */}
          <mesh material={materials.steelWheels} position={[0, 0, -trackGauge / 2]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[wheelRadius, wheelRadius, 0.14, 24]} />
          </mesh>
          {/* Right Wheel */}
          <mesh material={materials.steelWheels} position={[0, 0, trackGauge / 2]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[wheelRadius, wheelRadius, 0.14, 24]} />
          </mesh>
        </group>
      </group>
    );
  };

  // Helper to render individual passenger windows along a coach side
  const renderPassengerWindows = (windowXOffsets: number[]) => {
    return (
      <group>
        {/* Continuous Dark Window Band Recess */}
        <mesh material={materials.windowBand} position={[0, 2.65, 0]}>
          <boxGeometry args={[14.8, 0.78, 3.12]} />
        </mesh>

        {/* Individual Passenger Window Panes */}
        {windowXOffsets.map((wx, idx) => (
          <group key={idx} position={[wx, 2.65, 0]}>
            {/* Left side window */}
            <mesh material={materials.darkGlass} position={[0, 0, 1.565]}>
              <boxGeometry args={[1.20, 0.66, 0.03]} />
            </mesh>
            {/* Right side window */}
            <mesh material={materials.darkGlass} position={[0, 0, -1.565]}>
              <boxGeometry args={[1.20, 0.66, 0.03]} />
            </mesh>
          </group>
        ))}

        {/* Interior Cabin Diffuse Glow */}
        <mesh material={materials.interiorGlow} position={[0, 2.65, 0]}>
          <boxGeometry args={[14.4, 0.65, 2.9]} />
        </mesh>
      </group>
    );
  };

  // Helper to render passenger entry doors with windows and handles
  const renderDoors = (doorXOffsets: number[]) => {
    return (
      <group>
        {doorXOffsets.map((dx, idx) => (
          <group key={idx} position={[dx, 2.20, 0]}>
            {/* Left side door panel */}
            <mesh material={materials.bodyWhite} position={[0, 0, 1.555]}>
              <boxGeometry args={[0.92, 1.95, 0.02]} />
            </mesh>
            {/* Door perimeter seam */}
            <mesh material={materials.doorFrame} position={[0, 0, 1.553]}>
              <boxGeometry args={[0.96, 1.99, 0.01]} />
            </mesh>
            <mesh material={materials.darkGlass} position={[0, 0.35, 1.565]}>
              <boxGeometry args={[0.38, 0.78, 0.02]} />
            </mesh>
            {/* Chrome Handle Bar */}
            <mesh material={materials.chromeMetal} position={[0.32, 0, 1.575]}>
              <boxGeometry args={[0.03, 0.35, 0.02]} />
            </mesh>

            {/* Right side door panel */}
            <mesh material={materials.bodyWhite} position={[0, 0, -1.555]}>
              <boxGeometry args={[0.92, 1.95, 0.02]} />
            </mesh>
            {/* Door perimeter seam */}
            <mesh material={materials.doorFrame} position={[0, 0, -1.553]}>
              <boxGeometry args={[0.96, 1.99, 0.01]} />
            </mesh>
            <mesh material={materials.darkGlass} position={[0, 0.35, -1.565]}>
              <boxGeometry args={[0.38, 0.78, 0.02]} />
            </mesh>
            {/* Chrome Handle Bar */}
            <mesh material={materials.chromeMetal} position={[0.32, 0, -1.575]}>
              <boxGeometry args={[0.03, 0.35, 0.02]} />
            </mesh>
          </group>
        ))}
      </group>
    );
  };

  return (
    <group
      ref={trainGroupRef}
      position={[1.5, 0, trackZ]}
      onClick={(e) => {
        e.stopPropagation();
        onSelectTrain?.();
      }}
    >
      {/* ==================================================================== */}
      {/* 1. LEAD DRIVING CAR (AERODYNAMIC CAB COACH)                          */}
      {/* Length 15.0m, Nose at X = +4.5m, Rear at X = -10.5m                  */}
      {/* ==================================================================== */}
      <group position={[-3.0, 0, 0]}>
        {/* Main Passenger Body Structure */}
        <mesh material={materials.bodyWhite} position={[0, 2.51, 0]} castShadow receiveShadow>
          <boxGeometry args={[15.0, 2.62, 3.10]} />
        </mesh>

        {/* Roof Cantrail Bevels (Smooth curved transition from side to roof) */}
        <mesh material={materials.bodyWhite} position={[0, 3.80, 1.48]} rotation={[Math.PI / 4, 0, 0]}>
          <boxGeometry args={[15.0, 0.12, 0.12]} />
        </mesh>
        <mesh material={materials.bodyWhite} position={[0, 3.80, -1.48]} rotation={[Math.PI / 4, 0, 0]}>
          <boxGeometry args={[15.0, 0.12, 0.12]} />
        </mesh>

        {/* Lower Navy Blue Skirt Running Board */}
        <mesh material={materials.bodySkirt} position={[0, 1.25, 0]} castShadow>
          <boxGeometry args={[15.0, 0.42, 3.02]} />
        </mesh>

        {/* Electric Blue Dynamic Livery Stripe */}
        <mesh material={materials.liveryBlue} position={[0, 1.54, 0]}>
          <boxGeometry args={[15.02, 0.16, 3.12]} />
        </mesh>

        {/* Passenger Windows & Doors */}
        {renderPassengerWindows([-5.5, -3.8, -2.1, -0.4, 1.3, 3.0, 4.7])}
        {renderDoors([6.2, -6.6])}

        {/* Aerodynamic Roof Fairing & Dual HVAC Units */}
        <mesh material={materials.roofEquip} position={[0, 3.90, 0]} castShadow>
          <boxGeometry args={[14.2, 0.18, 2.4]} />
        </mesh>
        {[-3.5, 2.5].map((xOffset, idx) => (
          <mesh key={idx} material={materials.bogieSteel} position={[xOffset, 4.05, 0]}>
            <boxGeometry args={[2.4, 0.18, 1.6]} />
          </mesh>
        ))}

        {/* ------------------------------------------------------------------ */}
        {/* SLEEK CONTINUOUS AERODYNAMIC BULLET NOSE (From X = +7.5)           */}
        {/* ------------------------------------------------------------------ */}
        <group position={[7.5, 0, 0]}>
          {/* Main Aerodynamic Bullet Body Loft (Watertight, smoothly curved) */}
          <mesh
            geometry={noseGeometries.bodyGeom}
            material={materials.bodyWhite}
            castShadow
            receiveShadow
          />

          {/* Panoramic Curved Driver's Cockpit Windshield Visor */}
          <mesh
            material={materials.darkGlass}
            position={[1.8, 3.32, 0]}
            rotation={[0, 0, -0.38]}
            castShadow
          >
            <boxGeometry args={[1.65, 0.70, 2.45]} />
          </mesh>

          {/* Windshield Wiper Blade */}
          <mesh
            material={materials.chromeMetal}
            position={[2.2, 3.16, 0.25]}
            rotation={[0, 0, -0.38]}
          >
            <boxGeometry args={[0.04, 0.45, 0.02]} />
          </mesh>

          {/* Left Cockpit Side Window */}
          <mesh
            material={materials.darkGlass}
            position={[1.3, 3.32, 1.42]}
            rotation={[0, 0.12, -0.15]}
          >
            <boxGeometry args={[1.25, 0.58, 0.04]} />
          </mesh>

          {/* Right Cockpit Side Window */}
          <mesh
            material={materials.darkGlass}
            position={[1.3, 3.32, -1.42]}
            rotation={[0, -0.12, -0.15]}
          >
            <boxGeometry args={[1.25, 0.58, 0.04]} />
          </mesh>

          {/* Electric Blue Dynamic Livery Stripe */}
          <mesh
            geometry={noseGeometries.cheatlineGeom}
            material={materials.liveryBlue}
          />

          {/* Aerodynamic Lower Cowcatcher / Deflector Apron */}
          <mesh material={materials.bodySkirt} position={[2.5, 1.05, 0]} castShadow>
            <boxGeometry args={[4.8, 0.38, 2.8]} />
          </mesh>
          <mesh material={materials.liveryBlue} position={[4.4, 0.96, 0]} rotation={[0, 0, -0.10]}>
            <boxGeometry args={[1.4, 0.24, 1.8]} />
          </mesh>

          {/* ---------------------------------------------------------------- */}
          {/* HIGH-POWERED TRIPLE LED HEADLIGHT CLUSTER                        */}
          {/* ---------------------------------------------------------------- */}
          {/* Lower Left Headlight */}
          <group position={[4.7, 1.50, -0.60]}>
            <mesh material={materials.headlightHousing}>
              <cylinderGeometry args={[0.10, 0.12, 0.14, 16]} />
            </mesh>
            <mesh position={[0.07, 0, 0]} material={materials.headlightGlow} rotation={[0, Math.PI / 2, 0]}>
              <circleGeometry args={[0.09, 16]} />
            </mesh>
          </group>

          {/* Lower Right Headlight */}
          <group position={[4.7, 1.50, 0.60]}>
            <mesh material={materials.headlightHousing}>
              <cylinderGeometry args={[0.10, 0.12, 0.14, 16]} />
            </mesh>
            <mesh position={[0.07, 0, 0]} material={materials.headlightGlow} rotation={[0, Math.PI / 2, 0]}>
              <circleGeometry args={[0.09, 16]} />
            </mesh>
          </group>

          {/* Upper Cyclops High-Beam Headlight */}
          <group position={[2.7, 3.15, 0]}>
            <mesh material={materials.headlightHousing}>
              <cylinderGeometry args={[0.10, 0.12, 0.14, 16]} />
            </mesh>
            <mesh position={[0.07, 0, 0]} material={materials.headlightGlow} rotation={[0, Math.PI / 2, 0]}>
              <circleGeometry args={[0.09, 16]} />
            </mesh>
          </group>

          {/* Forward Track Illuminator Spotlight (Subtle beam along rails) */}
          <spotLight
            position={[4.8, 1.45, 0]}
            target-position={[35, 0.4, 0]}
            color="#F8FAFC"
            intensity={5.0}
            distance={45}
            angle={Math.PI / 7}
            penumbra={0.5}
            castShadow
          />
        </group>

        {/* Lead Car Bogies */}
        {renderBogie('lead-front-bogie', 4.5)}
        {renderBogie('lead-rear-bogie', -4.5)}
      </group>

      {/* ==================================================================== */}
      {/* 2. ARTICULATED INTER-CAR GANGWAY (RUBBER BELLOWS)                    */}
      {/* ==================================================================== */}
      <group position={[-11.15, 2.5, 0]}>
        <mesh material={materials.gangwayRubber}>
          <boxGeometry args={[1.3, 2.40, 2.70]} />
        </mesh>
        <mesh material={materials.bogieSteel} position={[0, -1.15, 0]}>
          <boxGeometry args={[1.35, 0.10, 2.75]} />
        </mesh>
      </group>

      {/* ==================================================================== */}
      {/* 3. TRAILER PASSENGER COACH (Second Coach with 25 kV AC Pantograph)   */}
      {/* Length 15.0m, Center at X = -19.3m                                   */}
      {/* ==================================================================== */}
      <group position={[-19.3, 0, 0]}>
        {/* Main Passenger Body Structure */}
        <mesh material={materials.bodyWhite} position={[0, 2.51, 0]} castShadow receiveShadow>
          <boxGeometry args={[15.0, 2.62, 3.10]} />
        </mesh>

        {/* Roof Cantrail Bevels */}
        <mesh material={materials.bodyWhite} position={[0, 3.80, 1.48]} rotation={[Math.PI / 4, 0, 0]}>
          <boxGeometry args={[15.0, 0.12, 0.12]} />
        </mesh>
        <mesh material={materials.bodyWhite} position={[0, 3.80, -1.48]} rotation={[Math.PI / 4, 0, 0]}>
          <boxGeometry args={[15.0, 0.12, 0.12]} />
        </mesh>

        {/* Skirt */}
        <mesh material={materials.bodySkirt} position={[0, 1.25, 0]} castShadow>
          <boxGeometry args={[15.0, 0.42, 3.02]} />
        </mesh>

        {/* Electric Blue Livery Stripe */}
        <mesh material={materials.liveryBlue} position={[0, 1.54, 0]}>
          <boxGeometry args={[15.02, 0.16, 3.12]} />
        </mesh>

        {/* Passenger Windows & Doors */}
        {renderPassengerWindows([-4.7, -3.0, -1.3, 0.4, 2.1, 3.8, 5.5])}
        {renderDoors([6.6, -6.2])}

        {/* Roof Equipment */}
        <mesh material={materials.roofEquip} position={[0, 3.90, 0]} castShadow>
          <boxGeometry args={[14.2, 0.18, 2.4]} />
        </mesh>
        {[-4.0, 4.0].map((xOffset, idx) => (
          <mesh key={idx} material={materials.bogieSteel} position={[xOffset, 4.05, 0]}>
            <boxGeometry args={[2.4, 0.18, 1.6]} />
          </mesh>
        ))}

        {/* ------------------------------------------------------------------ */}
        {/* 25 kV AC ARTICULATED HIGH-SPEED SINGLE-ARM PANTOGRAPH              */}
        {/* Mounts at X = 0, Collector touches contact wire at Y = 5.38m       */}
        {/* ------------------------------------------------------------------ */}
        <group position={[0, 3.95, 0]}>
          {/* Base Frame & High-Voltage Terracotta Insulators */}
          <mesh material={materials.bogieSteel} position={[0, 0.08, 0]}>
            <boxGeometry args={[2.0, 0.10, 1.5]} />
          </mesh>
          {[
            [-0.7, -0.55],
            [-0.7, 0.55],
            [0.7, -0.55],
            [0.7, 0.55],
          ].map(([ix, iz], idx) => (
            <mesh key={idx} material={materials.insulatorBrown} position={[ix, 0.22, iz]}>
              <cylinderGeometry args={[0.08, 0.09, 0.26, 12]} />
            </mesh>
          ))}

          {/* Lower Pantograph Arm (angled upward towards +X) */}
          <group position={[-0.5, 0.35, 0]} rotation={[0, 0, Math.PI / 4.2]}>
            <mesh material={materials.pantographRed} position={[0.75, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
              <cylinderGeometry args={[0.040, 0.040, 1.5, 8]} />
            </mesh>

            {/* Upper Articulated Arm (angles back upward to contact wire) */}
            <group position={[1.4, 0, 0]} rotation={[0, 0, -Math.PI / 2.5]}>
              <mesh material={materials.pantographRed} position={[0.80, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
                <cylinderGeometry args={[0.032, 0.032, 1.6, 8]} />
              </mesh>

              {/* Pantograph Head & Carbon Contact Strip (at Y ~ 5.38m) */}
              <group position={[1.65, 0, 0]} rotation={[0, 0, Math.PI / 5.2]}>
                <mesh material={materials.carbonStrip} position={[0, 0, 0]}>
                  <boxGeometry args={[0.24, 0.06, 1.95]} />
                </mesh>
                {/* Curved Horn Ends */}
                <mesh material={materials.pantographRed} position={[0, -0.05, -0.98]} rotation={[0, 0, -Math.PI / 6]}>
                  <cylinderGeometry args={[0.018, 0.018, 0.22, 8]} />
                </mesh>
                <mesh material={materials.pantographRed} position={[0, -0.05, 0.98]} rotation={[0, 0, Math.PI / 6]}>
                  <cylinderGeometry args={[0.018, 0.018, 0.22, 8]} />
                </mesh>
              </group>
            </group>
          </group>
        </group>

        {/* Coach Bogies */}
        {renderBogie('coach-front-bogie', 4.5)}
        {renderBogie('coach-rear-bogie', -4.5)}
      </group>
    </group>
  );
};
