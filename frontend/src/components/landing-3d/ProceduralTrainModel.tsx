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
  showTelemetry?: boolean;
}

/**
 * High-Speed Modern Passenger Streamliner (Physical PBR + Restrained Digital-Twin Overlay)
 * Strictly matches reference screenshot:
 * - Solid, aerodynamic European high-speed electric streamliner (Siemens Velaro / AGV aerodynamic profile)
 * - Deep metallic midnight-blue/graphite livery with high specular gloss
 * - TrackMeld electric cobalt blue waistline speed stripe and obsidian window band
 * - Restrained, surgical cyan (#00F0FF) digital-twin CAD wireframe overlay (toggled via showTelemetry)
 * - Luminous telemetry vertex nodes highlighting sensor radar/lidar positions on the prow
 * - Recessed automatic Scharfenberg coupler pocket in lower nose
 * - Piercing dual-projector LED headlights with cyan halo bezels and forward spotlights
 * - Raked panoramic cockpit windscreen and flush tinted passenger windows
 * - Recessed passenger entrance doors with door seals and illuminated indicators
 * - 25 kV AC roof pantograph contacting overhead catenary wire
 * - High-detail 2-axle cast steel bogies with brake discs and flanged wheels seated tangent to rail heads
 */
export const ProceduralTrainModel: React.FC<ProceduralTrainModelProps> = ({
  speedKmh = 120,
  isPlaying = true,
  onSelectTrain,
  isSelected = false,
  trackZ = -2.0, // UP MAIN track center
  showTelemetry = true,
}) => {
  const trainGroupRef = useRef<THREE.Group>(null);
  const wheelsRef = useRef<THREE.Group[]>([]);
  const wireframeMaterialRef = useRef<THREE.LineBasicMaterial>(null);
  const accentWireMaterialRef = useRef<THREE.LineBasicMaterial>(null);
  const pointsMaterialRef = useRef<THREE.PointsMaterial>(null);

  // ---------------------------------------------------------------------------
  // 1. PBR MATERIALS & RESTRAINED DIGITAL-TWIN CYAN ACCENTS
  // ---------------------------------------------------------------------------
  const materials = useMemo(() => {
    // Aerodynamic Streamliner Prow & Fuselage: Sleek metallic silver/platinum finish matching reference photo
    const hullSilver = new THREE.MeshStandardMaterial({
      color: '#CBD5E1', // Aerodynamic platinum silver streamliner livery
      metalness: 0.45,
      roughness: 0.22,
      side: THREE.DoubleSide,
    });

    // Primary Aerodynamic Streamliner Fuselage: Rich metallic midnight-blue/slate finish
    const hullBase = new THREE.MeshStandardMaterial({
      color: '#162C48', // Authentic high-speed electric streamliner metallic livery
      metalness: 0.35,
      roughness: 0.26,
      side: THREE.DoubleSide,
    });

    // Aerodynamic TrackMeld Cobalt Blue Speed Stripe along waistline
    const speedStripe = new THREE.MeshStandardMaterial({
      color: '#2563EB',
      metalness: 0.55,
      roughness: 0.22,
      side: THREE.DoubleSide,
    });

    // Dark Obsidian Gloss Window Band along cabin sides
    const windowBand = new THREE.MeshStandardMaterial({
      color: '#070C15',
      metalness: 0.85,
      roughness: 0.10,
      side: THREE.DoubleSide,
    });

    // Lower aerodynamic skirts and dark structural components
    const hullDarkAccent = new THREE.MeshStandardMaterial({
      color: '#0B1524',
      metalness: 0.65,
      roughness: 0.35,
      side: THREE.DoubleSide,
    });

    // Roof equipment fairings and HVAC housings
    const roofFairing = new THREE.MeshStandardMaterial({
      color: '#2A3F5E',
      metalness: 0.50,
      roughness: 0.24,
      side: THREE.DoubleSide,
    });

    // Restrained, surgical cyan digital-twin schematic lines (subtle, non-obtrusive technical accent)
    const lineCyan = new THREE.LineBasicMaterial({
      color: isSelected ? '#38BDF8' : '#00F0FF',
      transparent: true,
      opacity: showTelemetry ? 0.10 : 0.0,
      depthTest: true,
    });

    const lineAccent = new THREE.LineBasicMaterial({
      color: '#7DD3FC',
      transparent: true,
      opacity: showTelemetry ? 0.14 : 0.0,
      depthTest: true,
    });

    // Fine radar/telemetry vertex nodes on the nose prow (subtle precision dots)
    const pointsCyan = new THREE.PointsMaterial({
      color: '#00F0FF',
      size: 0.018,
      transparent: true,
      opacity: showTelemetry ? 0.35 : 0.0,
      sizeAttenuation: true,
    });

    // Dark tinted panoramic laminated glass with high specular reflectivity
    const darkGlass = new THREE.MeshStandardMaterial({
      color: '#040A16',
      metalness: 0.98,
      roughness: 0.04,
      transparent: true,
      opacity: 0.94,
    });

    // Soft passenger cabin interior illumination (warm ambient glow matching reference)
    const interiorGlow = new THREE.MeshBasicMaterial({
      color: '#FEF3C7',
      transparent: true,
      opacity: 0.22,
    });

    // Illuminated Passenger Destination Matrix Display (Amber LED)
    const destMatrix = new THREE.MeshBasicMaterial({
      color: '#F59E0B',
    });

    // Cast steel bogies and mechanical undercarriage
    const bogieSteel = new THREE.MeshStandardMaterial({
      color: '#0B1120',
      metalness: 0.85,
      roughness: 0.40,
    });

    // Machined steel wheels with high specular gleam
    const steelWheels = new THREE.MeshStandardMaterial({
      color: '#E2E8F0',
      metalness: 0.98,
      roughness: 0.10,
    });

    // Ventilated steel brake discs
    const brakeDiscSteel = new THREE.MeshStandardMaterial({
      color: '#94A3B8',
      metalness: 0.92,
      roughness: 0.25,
    });

    // Front high-power LED headlight projector lenses (pure brilliant white)
    const headlightCore = new THREE.MeshBasicMaterial({
      color: '#FFFFFF',
    });

    const headlightHalo = new THREE.MeshBasicMaterial({
      color: '#00F0FF',
      transparent: true,
      opacity: 0.85,
    });

    // Catenary pantograph red/steel arm
    const pantographRed = new THREE.MeshStandardMaterial({
      color: '#DC2626',
      metalness: 0.65,
      roughness: 0.35,
    });

    const carbonStrip = new THREE.MeshStandardMaterial({
      color: '#0F172A',
      metalness: 0.90,
      roughness: 0.20,
    });

    const gangwayRubber = new THREE.MeshStandardMaterial({
      color: '#060A12',
      roughness: 0.90,
      metalness: 0.10,
    });

    return {
      hullSilver,
      hullBase,
      speedStripe,
      windowBand,
      hullDarkAccent,
      roofFairing,
      lineCyan,
      lineAccent,
      pointsCyan,
      darkGlass,
      interiorGlow,
      bogieSteel,
      steelWheels,
      brakeDiscSteel,
      headlightCore,
      headlightHalo,
      pantographRed,
      carbonStrip,
      gangwayRubber,
      destMatrix,
    };
  }, [isSelected, showTelemetry]);

  // ---------------------------------------------------------------------------
  // 2. PARAMETRIC STREAMLINER PROFILE & RESTRAINED WIREFRAME GENERATOR
  // Builds both the smooth solid hull BufferGeometry and selective CAD LineSegments
  // ---------------------------------------------------------------------------
  const {
    leadHullGeom,
    leadWireGeom,
    leadPointsGeom,
    coachHullGeom,
    coachWireGeom,
    windshieldGeom,
    windshieldWireGeom,
  } = useMemo(() => {
    // 24 normalized points defining the authentic aerodynamic cross-section:
    // Tumblehome lower skirt, vertical window band, arched cantrail, curved roof crown
    const basePerimeter = [
      // Bottom center to right skirt
      { y: 0.72, z: 0.00 }, // 0: Bottom center
      { y: 0.74, z: 0.65 }, // 1
      { y: 0.80, z: 1.30 }, // 2: Skirt bottom corner
      { y: 1.12, z: 1.48 }, // 3: Skirt crease
      { y: 1.55, z: 1.55 }, // 4: Lower sill
      { y: 2.10, z: 1.55 }, // 5: Window sill / waistline
      { y: 2.55, z: 1.55 }, // 6: Window mid
      { y: 3.00, z: 1.55 }, // 7: Window header
      { y: 3.32, z: 1.52 }, // 8: Cantrail start
      { y: 3.58, z: 1.38 }, // 9: Roof shoulder curve 1
      { y: 3.76, z: 1.08 }, // 10: Roof shoulder curve 2
      { y: 3.88, z: 0.58 }, // 11: Roof crown flank
      { y: 3.92, z: 0.00 }, // 12: Roof crown apex
      // Left side (symmetric)
      { y: 3.88, z: -0.58 }, // 13
      { y: 3.76, z: -1.08 }, // 14: Roof shoulder curve 2
      { y: 3.58, z: -1.38 }, // 15
      { y: 3.32, z: -1.52 }, // 16: Cantrail start
      { y: 3.00, z: -1.55 }, // 17: Window header
      { y: 2.55, z: -1.55 }, // 18
      { y: 2.10, z: -1.55 }, // 19: Window sill / waistline
      { y: 1.55, z: -1.55 }, // 20
      { y: 1.12, z: -1.48 }, // 21: Skirt crease
      { y: 0.80, z: -1.30 }, // 22: Skirt bottom corner
      { y: 0.74, z: -0.65 }, // 23
    ];
    const nPts = basePerimeter.length;

    // Key aerodynamic longitudinal character lines to highlight in wireframe
    const characterLineIndices = new Set([0, 2, 3, 5, 7, 8, 10, 12, 14, 16, 17, 19, 21, 22]);

    // Helper to generate solid hull and selective quad wireframe from station rings
    const buildLoft = (
      stations: Array<{
        x: number;
        wScale: number;
        yOffset: number;
        yScale: number;
        skirtUp?: number;
      }>,
      isLeadNose: boolean = false
    ) => {
      const vertices: number[] = [];
      const indices: number[] = [];
      const uvs: number[] = [];
      const linePositions: number[] = [];
      const nosePointVertices: number[] = [];

      const nStations = stations.length;

      // 1. Generate vertices for all station rings
      for (let i = 0; i < nStations; i++) {
        const st = stations[i];
        const u = i / (nStations - 1);

        for (let j = 0; j < nPts; j++) {
          const pt = basePerimeter[j];
          const vx = st.x;
          let vy = st.yOffset + pt.y * st.yScale;
          if (st.skirtUp && pt.y < 1.0) {
            vy += st.skirtUp * (1.0 - pt.y);
          }
          const vz = pt.z * st.wScale;

          vertices.push(vx, vy, vz);
          uvs.push(u, j / nPts);

          // Collect front nose prow vertices for luminous telemetry nodes
          if (isLeadNose && i <= 8) {
            nosePointVertices.push(vx, vy, vz);
          }
        }
      }

      // 2. Generate solid hull triangles and selective CAD character wireframe
      for (let i = 0; i < nStations - 1; i++) {
        const ring1 = i * nPts;
        const ring2 = (i + 1) * nPts;

        // On nose prow (i <= 8), draw every ring for aerodynamic contour; on body, draw frame ribs
        const isFrameRing = isLeadNose ? (i <= 8 || i % 2 === 0) : (i % 2 === 0);

        for (let j = 0; j < nPts; j++) {
          const jNext = (j + 1) % nPts;

          const p1 = ring1 + j;
          const p2 = ring2 + j;
          const p3 = ring2 + jNext;
          const p4 = ring1 + jNext;

          // Solid mesh triangles (outward facing normals)
          indices.push(p1, p4, p2);
          indices.push(p2, p4, p3);

          // Transverse frame hoop segment
          if (isFrameRing) {
            linePositions.push(
              vertices[p1 * 3], vertices[p1 * 3 + 1], vertices[p1 * 3 + 2],
              vertices[p4 * 3], vertices[p4 * 3 + 1], vertices[p4 * 3 + 2]
            );
          }

          // Longitudinal streamline segment: All points on nose prow; key character lines on body
          const isLongitudinal = isLeadNose && i <= 8 ? true : characterLineIndices.has(j);
          if (isLongitudinal) {
            linePositions.push(
              vertices[p1 * 3], vertices[p1 * 3 + 1], vertices[p1 * 3 + 2],
              vertices[p2 * 3], vertices[p2 * 3 + 1], vertices[p2 * 3 + 2]
            );
          }
        }
      }

      // Add closing hoop for final station
      const lastRing = (nStations - 1) * nPts;
      for (let j = 0; j < nPts; j++) {
        const jNext = (j + 1) % nPts;
        const p1 = lastRing + j;
        const p2 = lastRing + jNext;
        linePositions.push(
          vertices[p1 * 3], vertices[p1 * 3 + 1], vertices[p1 * 3 + 2],
          vertices[p2 * 3], vertices[p2 * 3 + 1], vertices[p2 * 3 + 2]
        );
      }

      // Smooth nose cone apex closure
      if (isLeadNose) {
        const apexIdx = vertices.length / 3;
        const apexX = stations[0].x + 0.12;
        const apexY = stations[0].yOffset + 2.0 * stations[0].yScale;
        const apexZ = 0.0;
        vertices.push(apexX, apexY, apexZ);
        uvs.push(0, 0.5);
        nosePointVertices.push(apexX, apexY, apexZ);

        for (let j = 0; j < nPts; j++) {
          const jNext = (j + 1) % nPts;
          indices.push(apexIdx, jNext, j);

          // Full radial streamline convergence at prow apex
          linePositions.push(
            apexX, apexY, apexZ,
            vertices[j * 3], vertices[j * 3 + 1], vertices[j * 3 + 2]
          );
        }
      }

      const hullGeom = new THREE.BufferGeometry();
      hullGeom.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
      hullGeom.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
      hullGeom.setIndex(indices);
      hullGeom.computeVertexNormals();

      const wireGeom = new THREE.BufferGeometry();
      wireGeom.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));

      const pointsGeom = new THREE.BufferGeometry();
      if (nosePointVertices.length > 0) {
        pointsGeom.setAttribute('position', new THREE.Float32BufferAttribute(nosePointVertices, 3));
      }

      return { hullGeom, wireGeom, pointsGeom };
    };

    // A. Lead Driving Car: European Streamliner Aerodynamic Bullet Nose
    const leadStations = [
      // Rounded aerodynamic bullet prow apex & lower pilot
      { x: 5.60, wScale: 0.10, yOffset: 0.55, yScale: 0.22, skirtUp: 0.28 },
      { x: 5.40, wScale: 0.22, yOffset: 0.44, yScale: 0.35, skirtUp: 0.22 },
      { x: 5.15, wScale: 0.38, yOffset: 0.32, yScale: 0.48, skirtUp: 0.16 },
      { x: 4.80, wScale: 0.54, yOffset: 0.20, yScale: 0.60, skirtUp: 0.10 },
      // Coupler zone & headlight cluster mounting shoulders
      { x: 4.40, wScale: 0.70, yOffset: 0.12, yScale: 0.72, skirtUp: 0.04 },
      { x: 3.90, wScale: 0.82, yOffset: 0.06, yScale: 0.82 },
      // Raked Aerodynamic Cockpit Windshield Slope
      { x: 3.30, wScale: 0.90, yOffset: 0.02, yScale: 0.90 },
      { x: 2.60, wScale: 0.95, yOffset: 0.01, yScale: 0.95 },
      { x: 1.80, wScale: 0.98, yOffset: 0.00, yScale: 0.98 },
      { x: 0.90, wScale: 1.00, yOffset: 0.00, yScale: 1.00 },
      { x: 0.00, wScale: 1.00, yOffset: 0.00, yScale: 1.00 },
      // Cabin Body Stations
      { x: -1.60, wScale: 1.00, yOffset: 0.00, yScale: 1.00 },
      { x: -3.20, wScale: 1.00, yOffset: 0.00, yScale: 1.00 },
      { x: -4.80, wScale: 1.00, yOffset: 0.00, yScale: 1.00 },
      { x: -6.40, wScale: 1.00, yOffset: 0.00, yScale: 1.00 },
      { x: -8.00, wScale: 1.00, yOffset: 0.00, yScale: 1.00 },
      { x: -9.60, wScale: 1.00, yOffset: 0.00, yScale: 1.00 },
      { x: -11.20, wScale: 1.00, yOffset: 0.00, yScale: 1.00 },
      { x: -12.80, wScale: 1.00, yOffset: 0.00, yScale: 1.00 },
      { x: -14.20, wScale: 1.00, yOffset: 0.00, yScale: 1.00 },
    ];
    const {
      hullGeom: leadHullGeom,
      wireGeom: leadWireGeom,
      pointsGeom: leadPointsGeom,
    } = buildLoft(leadStations, true);

    // B. Intermediate & Trailing Passenger Coaches (16.5m length each)
    const coachStations: Array<{ x: number; wScale: number; yOffset: number; yScale: number }> = [];
    const nCoachRings = 14;
    const coachLen = 16.5;
    for (let i = 0; i <= nCoachRings; i++) {
      const x = (coachLen / 2) - (i / nCoachRings) * coachLen;
      coachStations.push({ x, wScale: 1.0, yOffset: 0.0, yScale: 1.0 });
    }
    const { hullGeom: coachHullGeom, wireGeom: coachWireGeom } = buildLoft(coachStations, false);

    // C. Aerodynamic Driver's Panoramic Cockpit Windshield (Raked glass shell)
    const wsVertices = [
      // Top cantrail brow
      1.75, 3.68, 1.25,
      1.75, 3.68, -1.25,
      // Mid windshield rake
      2.85, 3.12, -1.20,
      2.85, 3.12, 1.20,
      // Lower cowl base
      3.85, 2.30, 1.00,
      3.85, 2.30, -1.00,
    ];
    const wsIndices = [
      0, 3, 2,  0, 2, 1,
      3, 4, 5,  3, 5, 2,
    ];
    const wsLines = [
      // Outer border outline
      1.75, 3.68, 1.25,  1.75, 3.68, -1.25,
      1.75, 3.68, -1.25, 2.85, 3.12, -1.20,
      2.85, 3.12, -1.20, 3.85, 2.30, -1.00,
      3.85, 2.30, -1.00, 3.85, 2.30, 1.00,
      3.85, 2.30, 1.00,  2.85, 3.12, 1.20,
      2.85, 3.12, 1.20,  1.75, 3.68, 1.25,
      // Center dividing mullion / structural pillar
      1.75, 3.68, 0.00,  3.85, 2.30, 0.00,
    ];

    const windshieldGeom = new THREE.BufferGeometry();
    windshieldGeom.setAttribute('position', new THREE.Float32BufferAttribute(wsVertices, 3));
    windshieldGeom.setIndex(wsIndices);
    windshieldGeom.computeVertexNormals();

    const windshieldWireGeom = new THREE.BufferGeometry();
    windshieldWireGeom.setAttribute('position', new THREE.Float32BufferAttribute(wsLines, 3));

    return {
      leadHullGeom,
      leadWireGeom,
      leadPointsGeom,
      coachHullGeom,
      coachWireGeom,
      windshieldGeom,
      windshieldWireGeom,
    };
  }, []);

  // ---------------------------------------------------------------------------
  // 3. ANIMATION & TELEMETRY CONTROLLER
  // Forward cruising motion, rotating wheels, and restrained telemetry pulse
  // ---------------------------------------------------------------------------
  useFrame((state, delta) => {
    if (!trainGroupRef.current) return;

    if (isPlaying) {
      // Scaled cruising speed for realistic railway visual cadence
      const visualSpeed = Math.max((speedKmh / 3.6) * 0.12, 1.8);
      trainGroupRef.current.position.x += visualSpeed * delta;

      // Smooth continuous loop keeping the lead car nose framed in center-right
      if (trainGroupRef.current.position.x > 6.2) {
        trainGroupRef.current.position.x = 0.8;
      }

      // Rotate wheelsets synchronously with linear motion (wheel radius = 0.45m)
      const wheelAngularSpeed = (visualSpeed / 0.45) * delta;
      wheelsRef.current.forEach((wheelGroup) => {
        if (wheelGroup) {
          wheelGroup.rotation.z -= wheelAngularSpeed;
        }
      });
    }

    // Dynamic subtle telemetry pulse when enabled (subtle architectural schematic accent)
    if (wireframeMaterialRef.current) {
      if (showTelemetry) {
        const pulseT = (state.clock.elapsedTime * 2.0) % 1.0;
        const pulseBrightness = 0.09 + Math.sin(pulseT * Math.PI) * 0.04; // Delicate 0.09 to 0.13 opacity
        wireframeMaterialRef.current.opacity = pulseBrightness;
        wireframeMaterialRef.current.visible = true;
      } else {
        wireframeMaterialRef.current.opacity = 0.0;
        wireframeMaterialRef.current.visible = false;
      }
    }

    if (accentWireMaterialRef.current) {
      accentWireMaterialRef.current.visible = showTelemetry;
      accentWireMaterialRef.current.opacity = showTelemetry ? 0.14 : 0.0;
    }

    if (pointsMaterialRef.current) {
      if (showTelemetry) {
        const pulseT = (state.clock.elapsedTime * 2.5) % 1.0;
        pointsMaterialRef.current.size = 0.018 + Math.sin(pulseT * Math.PI) * 0.004;
        pointsMaterialRef.current.opacity = 0.35;
        pointsMaterialRef.current.visible = true;
      } else {
        pointsMaterialRef.current.opacity = 0.0;
        pointsMaterialRef.current.visible = false;
      }
    }
  });

  // Track & wheel dimension standards
  const trackGauge = 1.676; // Broad gauge distance between rail centers
  const railTopY = 0.44;    // Rail head elevation
  const wheelRadius = 0.45;
  const axleY = railTopY + wheelRadius; // Exactly 0.89m above ground
  const axleSpacing = 2.4;

  // ---------------------------------------------------------------------------
  // 4. HELPER: 2-AXLE HIGH-SPEED BOGIE (TRUCK) SEATED DIRECTLY ON RAILS
  // ---------------------------------------------------------------------------
  const renderBogie = (key: string, xPos: number) => {
    return (
      <group key={key} position={[xPos, 0, 0]}>
        {/* Main Cast Steel H-Frame */}
        <mesh material={materials.bogieSteel} position={[0, axleY + 0.10, 0]} castShadow>
          <boxGeometry args={[3.2, 0.22, trackGauge + 0.40]} />
        </mesh>

        {/* Secondary Air Suspension Bellows */}
        <mesh material={materials.gangwayRubber} position={[0, axleY + 0.30, -(trackGauge / 2 + 0.16)]}>
          <cylinderGeometry args={[0.22, 0.24, 0.28, 16]} />
        </mesh>
        <mesh material={materials.gangwayRubber} position={[0, axleY + 0.30, trackGauge / 2 + 0.16]}>
          <cylinderGeometry args={[0.22, 0.24, 0.28, 16]} />
        </mesh>

        {/* Axle 1 (Front Wheelset) */}
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
          {/* Ventilated Brake Discs mounted on Axle */}
          <mesh material={materials.brakeDiscSteel} position={[0, 0, -0.35]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.26, 0.26, 0.04, 20]} />
          </mesh>
          <mesh material={materials.brakeDiscSteel} position={[0, 0, 0.35]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.26, 0.26, 0.04, 20]} />
          </mesh>

          {/* Left Flanged Wheel (Resting tangent to Rail Top Y = 0.44) */}
          <mesh material={materials.steelWheels} position={[0, 0, -trackGauge / 2]} rotation={[Math.PI / 2, 0, 0]} castShadow>
            <cylinderGeometry args={[wheelRadius, wheelRadius, 0.14, 24]} />
          </mesh>
          <mesh material={materials.steelWheels} position={[0, 0, -trackGauge / 2 - 0.06]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[wheelRadius + 0.035, wheelRadius + 0.035, 0.03, 24]} />
          </mesh>

          {/* Right Flanged Wheel */}
          <mesh material={materials.steelWheels} position={[0, 0, trackGauge / 2]} rotation={[Math.PI / 2, 0, 0]} castShadow>
            <cylinderGeometry args={[wheelRadius, wheelRadius, 0.14, 24]} />
          </mesh>
          <mesh material={materials.steelWheels} position={[0, 0, trackGauge / 2 + 0.06]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[wheelRadius + 0.035, wheelRadius + 0.035, 0.03, 24]} />
          </mesh>
        </group>

        {/* Axle 2 (Rear Wheelset) */}
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
          {/* Ventilated Brake Discs */}
          <mesh material={materials.brakeDiscSteel} position={[0, 0, -0.35]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.26, 0.26, 0.04, 20]} />
          </mesh>
          <mesh material={materials.brakeDiscSteel} position={[0, 0, 0.35]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.26, 0.26, 0.04, 20]} />
          </mesh>

          {/* Left Flanged Wheel */}
          <mesh material={materials.steelWheels} position={[0, 0, -trackGauge / 2]} rotation={[Math.PI / 2, 0, 0]} castShadow>
            <cylinderGeometry args={[wheelRadius, wheelRadius, 0.14, 24]} />
          </mesh>
          <mesh material={materials.steelWheels} position={[0, 0, -trackGauge / 2 - 0.06]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[wheelRadius + 0.035, wheelRadius + 0.035, 0.03, 24]} />
          </mesh>

          {/* Right Flanged Wheel */}
          <mesh material={materials.steelWheels} position={[0, 0, trackGauge / 2]} rotation={[Math.PI / 2, 0, 0]} castShadow>
            <cylinderGeometry args={[wheelRadius, wheelRadius, 0.14, 24]} />
          </mesh>
          <mesh material={materials.steelWheels} position={[0, 0, trackGauge / 2 + 0.06]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[wheelRadius + 0.035, wheelRadius + 0.035, 0.03, 24]} />
          </mesh>
        </group>
      </group>
    );
  };

  // ---------------------------------------------------------------------------
  // 5. HELPER: WINDOW BANDS & ENTRANCE DOORS WITH RESTYLED LIVERY
  // ---------------------------------------------------------------------------
  const renderWindowsAndDoors = (windowOffsets: number[], doorOffsets: number[] = [-6.8, 6.8]) => {
    return (
      <>
        {/* Continuous Dark Obsidian Window Band along cabin sides */}
        <mesh material={materials.windowBand} position={[0, 2.55, 1.554]}>
          <boxGeometry args={[14.8, 0.88, 0.015]} />
        </mesh>
        <mesh material={materials.windowBand} position={[0, 2.55, -1.554]}>
          <boxGeometry args={[14.8, 0.88, 0.015]} />
        </mesh>

        {/* Aerodynamic Cobalt Blue Speed Stripe along waistline below window band */}
        <mesh material={materials.speedStripe} position={[0, 1.95, 1.556]}>
          <boxGeometry args={[14.8, 0.18, 0.012]} />
        </mesh>
        <mesh material={materials.speedStripe} position={[0, 1.95, -1.556]}>
          <boxGeometry args={[14.8, 0.18, 0.012]} />
        </mesh>

        {/* Flush Panoramic Tinted Glass Strip along both sides */}
        <mesh material={materials.darkGlass} position={[0, 2.55, 1.560]}>
          <boxGeometry args={[14.7, 0.76, 0.015]} />
        </mesh>
        <mesh material={materials.darkGlass} position={[0, 2.55, -1.560]}>
          <boxGeometry args={[14.7, 0.76, 0.015]} />
        </mesh>

        {/* Side Destination LED Matrix Display */}
        <mesh material={materials.destMatrix} position={[0, 3.08, 1.558]}>
          <boxGeometry args={[2.2, 0.14, 0.015]} />
        </mesh>
        <mesh material={materials.destMatrix} position={[0, 3.08, -1.558]}>
          <boxGeometry args={[2.2, 0.14, 0.015]} />
        </mesh>

        {/* Individual Window Bays with subtle CAD Frame Accents */}
        {showTelemetry &&
          windowOffsets.map((wx, idx) => (
            <group key={`win-${idx}`} position={[wx, 2.55, 0]}>
              <lineSegments position={[0, 0, 1.564]}>
                <edgesGeometry args={[new THREE.BoxGeometry(1.42, 0.72, 0.01)]} />
                <lineBasicMaterial color="#38BDF8" transparent opacity={0.16} />
              </lineSegments>
              <lineSegments position={[0, 0, -1.564]}>
                <edgesGeometry args={[new THREE.BoxGeometry(1.42, 0.72, 0.01)]} />
                <lineBasicMaterial color="#38BDF8" transparent opacity={0.16} />
              </lineSegments>
            </group>
          ))}

        {/* Recessed Passenger Entrance Doors */}
        {doorOffsets.map((dx, idx) => (
          <group key={`door-${idx}`} position={[dx, 2.30, 0]}>
            {/* Right Side Door */}
            <mesh position={[0, 0, 1.554]} material={materials.hullDarkAccent}>
              <boxGeometry args={[1.20, 2.20, 0.02]} />
            </mesh>
            {showTelemetry && (
              <lineSegments position={[0, 0, 1.558]}>
                <edgesGeometry args={[new THREE.BoxGeometry(1.20, 2.20, 0.01)]} />
                <lineBasicMaterial color="#38BDF8" transparent opacity={0.40} />
              </lineSegments>
            )}
            {/* Illuminated Door Push Button Indicator */}
            <mesh position={[0.50, -0.20, 1.562]} material={materials.headlightHalo}>
              <circleGeometry args={[0.04, 12]} />
            </mesh>

            {/* Left Side Door */}
            <mesh position={[0, 0, -1.554]} material={materials.hullDarkAccent}>
              <boxGeometry args={[1.20, 2.20, 0.02]} />
            </mesh>
            {showTelemetry && (
              <lineSegments position={[0, 0, -1.558]}>
                <edgesGeometry args={[new THREE.BoxGeometry(1.20, 2.20, 0.01)]} />
                <lineBasicMaterial color="#38BDF8" transparent opacity={0.40} />
              </lineSegments>
            )}
            <mesh position={[0.50, -0.20, -1.562]} material={materials.headlightHalo} rotation={[0, Math.PI, 0]}>
              <circleGeometry args={[0.04, 12]} />
            </mesh>
          </group>
        ))}

        {/* Soft Interior Cabin Ambient Illumination */}
        <mesh material={materials.interiorGlow} position={[0, 2.55, 0]}>
          <boxGeometry args={[14.0, 0.68, 2.8]} />
        </mesh>
      </>
    );
  };

  // ---------------------------------------------------------------------------
  // 6. HELPER: PASSENGER COACH WITH AERODYNAMIC ROOF & BOGIES
  // ---------------------------------------------------------------------------
  const renderCoach = (
    coachId: string,
    xCenter: number,
    windowOffsets: number[],
    hasPantograph: boolean = false
  ) => {
    return (
      <group key={coachId} position={[xCenter, 0, 0]}>
        {/* Streamlined Solid Metallic Fuselage Hull */}
        <mesh
          geometry={coachHullGeom}
          material={materials.hullBase}
          castShadow
          receiveShadow
        />

        {/* Restrained CAD Wireframe Mesh */}
        {showTelemetry && (
          <lineSegments
            geometry={coachWireGeom}
            material={materials.lineCyan}
          />
        )}

        {/* Panoramic Side Windows & Entrance Doors */}
        {renderWindowsAndDoors(windowOffsets, [-6.8, 6.8])}

        {/* Aerodynamic Roof HVAC Equipment Fairing */}
        <mesh material={materials.roofFairing} position={[0, 3.96, 0]} castShadow>
          <boxGeometry args={[11.5, 0.16, 2.2]} />
        </mesh>
        {showTelemetry && (
          <lineSegments position={[0, 3.96, 0]}>
            <edgesGeometry args={[new THREE.BoxGeometry(11.5, 0.16, 2.2)]} />
            <lineBasicMaterial color="#38BDF8" transparent opacity={0.35} />
          </lineSegments>
        )}

        {/* 25 kV AC Articulated Single-Arm Pantograph */}
        {hasPantograph && (
          <group position={[0, 4.04, 0]}>
            <mesh material={materials.bogieSteel} position={[0, 0.06, 0]}>
              <boxGeometry args={[1.8, 0.08, 1.4]} />
            </mesh>
            {/* Lower Pantograph Arm (angled towards +X) */}
            <group position={[-0.45, 0.28, 0]} rotation={[0, 0, Math.PI / 4.4]}>
              <mesh material={materials.pantographRed} position={[0.70, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
                <cylinderGeometry args={[0.038, 0.038, 1.45, 8]} />
              </mesh>
              {/* Upper Articulated Arm */}
              <group position={[1.35, 0, 0]} rotation={[0, 0, -Math.PI / 2.6]}>
                <mesh material={materials.pantographRed} position={[0.75, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
                  <cylinderGeometry args={[0.032, 0.032, 1.55, 8]} />
                </mesh>
                {/* Carbon Contact Collector Head contacting contact wire at Y = 5.38m */}
                <group position={[1.55, 0, 0]} rotation={[0, 0, Math.PI / 5.5]}>
                  <mesh material={materials.carbonStrip}>
                    <boxGeometry args={[0.22, 0.05, 1.95]} />
                  </mesh>
                  {/* Cyan Contact Arc Shimmer */}
                  <pointLight position={[0, 0.08, 0]} color="#00F0FF" intensity={1.8} distance={4} />
                </group>
              </group>
            </group>
          </group>
        )}

        {/* Front & Rear Bogies */}
        {renderBogie(`${coachId}-bogie-f`, 5.4)}
        {renderBogie(`${coachId}-bogie-r`, -5.4)}
      </group>
    );
  };

  // ---------------------------------------------------------------------------
  // 7. HELPER: INTER-CAR GANGWAY BELLOWS (RUBBER DIAPHRAGM)
  // ---------------------------------------------------------------------------
  const renderGangway = (key: string, xPos: number) => {
    return (
      <group key={key} position={[xPos, 2.45, 0]}>
        <mesh material={materials.gangwayRubber}>
          <boxGeometry args={[1.35, 2.50, 2.75]} />
        </mesh>
        {showTelemetry && (
          <lineSegments>
            <edgesGeometry args={[new THREE.BoxGeometry(1.36, 2.51, 2.76)]} />
            <lineBasicMaterial color="#38BDF8" transparent opacity={0.35} />
          </lineSegments>
        )}
      </group>
    );
  };

  return (
    <group
      ref={trainGroupRef}
      position={[2.0, 0, trackZ]}
      onClick={(e) => {
        e.stopPropagation();
        onSelectTrain?.();
      }}
    >
      {/* ==================================================================== */}
      {/* 1. LEAD DRIVING CAR (AERODYNAMIC BULLET NOSE + CABIN)                */}
      {/* ==================================================================== */}
      <group position={[0, 0, 0]}>
        {/* Streamlined Solid Metallic Fuselage Hull (Sleek platinum-silver aerodynamic nose) */}
        <mesh
          geometry={leadHullGeom}
          material={materials.hullSilver}
          castShadow
          receiveShadow
        />

        {/* Restrained Digital-Twin Wireframe Mesh */}
        <lineSegments
          geometry={leadWireGeom}
          material={materials.lineCyan}
          ref={wireframeMaterialRef}
        />

        {/* Glowing Cyan Telemetry Vertex Nodes on Nose Prow */}
        <points
          geometry={leadPointsGeom}
          material={materials.pointsCyan}
          ref={pointsMaterialRef}
        />

        {/* Aerodynamic Cockpit Panoramic Windshield */}
        <mesh
          geometry={windshieldGeom}
          material={materials.darkGlass}
          castShadow
        />
        {/* Windshield Cyan Structural Outline & Center Mullion */}
        <lineSegments
          geometry={windshieldWireGeom}
          material={materials.lineAccent}
          ref={accentWireMaterialRef}
        />

        {/* Lead Car Passenger Cabin Windows & Rear Entrance Door */}
        <group position={[-7.0, 0, 0]}>
          {renderWindowsAndDoors([-4.8, -3.2, -1.6, 0.0, 1.6, 3.2, 4.8], [-6.2])}
        </group>

        {/* Aerodynamic Cobalt Blue Speed Stripe along nose flanks */}
        <mesh material={materials.speedStripe} position={[0.5, 1.95, 1.556]}>
          <boxGeometry args={[4.2, 0.18, 0.012]} />
        </mesh>
        <mesh material={materials.speedStripe} position={[0.5, 1.95, -1.556]}>
          <boxGeometry args={[4.2, 0.18, 0.012]} />
        </mesh>

        {/* ------------------------------------------------------------------ */}
        {/* RECESSED AUTOMATIC SCHARFENBERG COUPLER POCKET IN LOWER NOSE       */}
        {/* Authentically embedded inside the aerodynamic nose cowl            */}
        {/* ------------------------------------------------------------------ */}
        <group position={[4.88, 1.15, 0]}>
          {/* Recessed Coupler Cavity */}
          <mesh material={materials.hullDarkAccent}>
            <boxGeometry args={[0.32, 0.38, 0.72]} />
          </mesh>
          {showTelemetry && (
            <lineSegments>
              <edgesGeometry args={[new THREE.BoxGeometry(0.33, 0.39, 0.73)]} />
              <lineBasicMaterial color="#38BDF8" transparent opacity={0.40} />
            </lineSegments>
          )}
          {/* Coupler Shank Bar */}
          <mesh position={[0.12, 0, 0]} material={materials.bogieSteel} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.06, 0.06, 0.22, 12]} />
          </mesh>
          {/* Scharfenberg Mechanical Coupling Head */}
          <mesh position={[0.22, 0, 0]} material={materials.steelWheels}>
            <boxGeometry args={[0.16, 0.18, 0.26]} />
          </mesh>
        </group>

        {/* Lower Nose Pilot Skirt Diffuser Strakes */}
        <group position={[5.15, 0.82, 0]}>
          <mesh position={[0, 0, 0.52]} material={materials.headlightHalo}>
            <boxGeometry args={[0.25, 0.03, 0.22]} />
          </mesh>
          <mesh position={[0, 0, -0.52]} material={materials.headlightHalo}>
            <boxGeometry args={[0.25, 0.03, 0.22]} />
          </mesh>
        </group>

        {/* ------------------------------------------------------------------ */}
        {/* DUAL SWEPT PROJECTOR HEADLIGHT CLUSTERS (MATCHING REFERENCE IMAGE) */}
        {/* Integrated into aerodynamic nose fenders with dual projector lenses */}
        {/* ------------------------------------------------------------------ */}
        {/* Left Swept Headlight Assembly */}
        <group position={[4.62, 1.48, -0.84]} rotation={[0, -0.28, -0.14]}>
          {/* Swept Dark Bezel Housing */}
          <mesh material={materials.hullDarkAccent}>
            <boxGeometry args={[0.55, 0.30, 0.30]} />
          </mesh>
          {showTelemetry && (
            <lineSegments>
              <edgesGeometry args={[new THREE.BoxGeometry(0.56, 0.31, 0.31)]} />
              <lineBasicMaterial color="#38BDF8" transparent opacity={0.50} />
            </lineSegments>
          )}

          {/* Projector Lens 1 (Outer Main Beam) */}
          <mesh position={[0.26, 0.02, -0.06]} material={materials.headlightCore} rotation={[0, Math.PI / 2, 0]}>
            <sphereGeometry args={[0.11, 16, 16]} />
          </mesh>
          <mesh position={[0.24, 0.02, -0.06]} material={materials.headlightHalo} rotation={[0, Math.PI / 2, 0]}>
            <ringGeometry args={[0.115, 0.165, 20]} />
          </mesh>

          {/* Projector Lens 2 (Inner High Beam) */}
          <mesh position={[0.26, -0.02, 0.06]} material={materials.headlightCore} rotation={[0, Math.PI / 2, 0]}>
            <sphereGeometry args={[0.085, 16, 16]} />
          </mesh>
          <mesh position={[0.24, -0.02, 0.06]} material={materials.headlightHalo} rotation={[0, Math.PI / 2, 0]}>
            <ringGeometry args={[0.09, 0.135, 20]} />
          </mesh>

          {/* Cyan DRL Light-Guide Eyebrow */}
          <mesh position={[0.26, 0.12, 0]} material={materials.headlightHalo}>
            <boxGeometry args={[0.06, 0.035, 0.28]} />
          </mesh>

          {/* High-intensity forward brilliant white projector headlight */}
          <pointLight position={[0.4, 0, 0]} color="#FFFDF0" intensity={8.0} distance={25} />
        </group>

        {/* Right Swept Headlight Assembly */}
        <group position={[4.62, 1.48, 0.84]} rotation={[0, 0.28, -0.14]}>
          <mesh material={materials.hullDarkAccent}>
            <boxGeometry args={[0.55, 0.30, 0.30]} />
          </mesh>
          {showTelemetry && (
            <lineSegments>
              <edgesGeometry args={[new THREE.BoxGeometry(0.56, 0.31, 0.31)]} />
              <lineBasicMaterial color="#38BDF8" transparent opacity={0.25} />
            </lineSegments>
          )}

          {/* Projector Lens 1 (Outer Main Beam) */}
          <mesh position={[0.26, 0.02, 0.06]} material={materials.headlightCore} rotation={[0, Math.PI / 2, 0]}>
            <sphereGeometry args={[0.11, 16, 16]} />
          </mesh>
          <mesh position={[0.24, 0.02, 0.06]} material={materials.headlightHalo} rotation={[0, Math.PI / 2, 0]}>
            <ringGeometry args={[0.115, 0.165, 20]} />
          </mesh>

          {/* Projector Lens 2 (Inner High Beam) */}
          <mesh position={[0.26, -0.02, -0.06]} material={materials.headlightCore} rotation={[0, Math.PI / 2, 0]}>
            <sphereGeometry args={[0.085, 16, 16]} />
          </mesh>
          <mesh position={[0.24, -0.02, -0.06]} material={materials.headlightHalo} rotation={[0, Math.PI / 2, 0]}>
            <ringGeometry args={[0.09, 0.135, 20]} />
          </mesh>

          {/* Cyan DRL Light-Guide Eyebrow */}
          <mesh position={[0.26, 0.12, 0]} material={materials.headlightHalo}>
            <boxGeometry args={[0.06, 0.035, 0.28]} />
          </mesh>

          <pointLight position={[0.4, 0, 0]} color="#FFFDF0" intensity={8.0} distance={25} />
        </group>

        {/* Front Nose Prow Digital-Twin Luminescence (Restrained subtle sensor accent) */}
        {showTelemetry && (
          <pointLight
            position={[5.1, 1.6, 0]}
            color="#00F0FF"
            intensity={1.2}
            distance={8}
          />
        )}

        {/* Upper Cab Brow Cyclops High-Beam Light */}
        <group position={[1.90, 3.68, 0]}>
          <mesh material={materials.headlightCore} rotation={[0, Math.PI / 2, 0]}>
            <sphereGeometry args={[0.08, 16, 16]} />
          </mesh>
          <mesh position={[-0.01, 0, 0]} material={materials.headlightHalo} rotation={[0, Math.PI / 2, 0]}>
            <ringGeometry args={[0.085, 0.13, 16]} />
          </mesh>
          <pointLight position={[0.3, 0, 0]} color="#FFFDF0" intensity={4.0} distance={15} />
        </group>

        {/* Forward Track Illuminator Spotlights (Illuminating track & ballast ahead) */}
        <spotLight
          position={[4.8, 1.48, -0.84]}
          target-position={[55, 0.44, -2.0]}
          color="#F0F9FF"
          intensity={16.0}
          distance={85}
          angle={Math.PI / 5.2}
          penumbra={0.65}
          castShadow
        />
        <spotLight
          position={[4.8, 1.48, 0.84]}
          target-position={[55, 0.44, -2.0]}
          color="#F0F9FF"
          intensity={16.0}
          distance={85}
          angle={Math.PI / 5.2}
          penumbra={0.65}
          castShadow
        />

        {/* Lead Car Bogies */}
        {renderBogie('lead-bogie-f', 1.8)}
        {renderBogie('lead-bogie-r', -10.2)}
      </group>

      {/* ==================================================================== */}
      {/* 2. ARTICULATED GANGWAY 1                                             */}
      {/* ==================================================================== */}
      {renderGangway('gangway-1', -14.9)}

      {/* ==================================================================== */}
      {/* 3. INTERMEDIATE PASSENGER COACH 1 (WITH 25 kV AC PANTOGRAPH)         */}
      {/* Center at X = -24.0m, Length 16.5m                                   */}
      {/* ==================================================================== */}
      {renderCoach(
        'coach-mid',
        -24.0,
        [-6.0, -4.5, -3.0, -1.5, 0.0, 1.5, 3.0, 4.5, 6.0],
        true
      )}

      {/* ==================================================================== */}
      {/* 4. ARTICULATED GANGWAY 2                                             */}
      {/* ==================================================================== */}
      {renderGangway('gangway-2', -33.1)}

      {/* ==================================================================== */}
      {/* 5. TRAILING PASSENGER COACH 2 (RECEDING INTO PERSPECTIVE HORIZON)    */}
      {/* Center at X = -42.2m, Length 16.5m                                   */}
      {/* ==================================================================== */}
      {renderCoach(
        'coach-rear',
        -42.2,
        [-6.0, -4.5, -3.0, -1.5, 0.0, 1.5, 3.0, 4.5, 6.0],
        false
      )}
    </group>
  );
};
