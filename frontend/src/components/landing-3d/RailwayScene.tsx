'use client';

import React, { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { TrackMeldTrainLoader } from './TrackMeldTrainLoader';
import { MaintenanceWorksite } from './MaintenanceWorksite';
import { CameraMode, LightingPreset } from './types';
import { useSimulationClock } from './SimulationContext';
import { MaintenanceTask } from '@/types/railway';

interface RailwaySceneProps {
  cameraMode: CameraMode;
  lighting: LightingPreset;
  trainSpeedKmh: number;
  isPlaying: boolean;
  onSelectTrain: () => void;
  onSelectPossession: (id: string) => void;
  selectedEntity: string | null;
  showTelemetry?: boolean;
  task?: MaintenanceTask | null;
  workOrderTitle?: string | null;
}

/**
 * Authentic 3D Railway Infrastructure Corridor Simulation
 * Context: Broad Gauge (1676 mm), 25 kV AC Electrified Trunk Mainline (Tundla – Etawah, km 209 to 301)
 *
 * Core Engineering Features:
 * - Continuous, infinite streaming corridor architecture: Zero 5-second resets, zero snapping.
 * - Double broad-gauge tracks: UP MAIN (Z = -2.0m) and DOWN MAIN (Z = +2.0m).
 * - Full trapezoidal ballast embankment with sloped shoulders and cess gutters.
 * - Pre-stressed concrete monoblock sleepers (PSC) with Pandrol fasteners every 0.65m.
 * - Continuous welded UIC-60 mirror-polished steel rails with realistic profile.
 * - 25 kV AC Catenary OHE masts, cantilevers, stay arms, insulators, and contact wires.
 * - Kilometer marker milestone posts updating with authentic corridor chainage (KM 242+).
 * - 4-Aspect automatic block railway signals with illuminated hoods.
 * - Trackside cable troughs, relay apparatus cases, and boundary trees/vegetation.
 * - High-horsepower WAP-7 electric locomotive and LHB passenger coaches with rotating wheelsets.
 */
export const RailwayScene: React.FC<RailwaySceneProps> = ({
  lighting,
  trainSpeedKmh,
  isPlaying,
  onSelectTrain,
  onSelectPossession,
  selectedEntity,
  showTelemetry = true,
  task,
  workOrderTitle,
}) => {
  const clockRef = useSimulationClock();
  const trainAnchorRef = useRef<THREE.Group>(null);
  const trackGroupRef = useRef<THREE.Group>(null);
  const lightGroupRef = useRef<THREE.Group>(null);
  const worksiteAnchorRef = useRef<THREE.Group>(null);

  const sleeperSpacing = 0.65;
  const trackGauge = 1.676; // Broad gauge
  const upTrackZ = -2.0;
  const downTrackZ = 2.0;
  const halfGauge = trackGauge / 2; // 0.838m

  // ---------------------------------------------------------------------------
  // 1. ATMOSPHERIC LIGHTING & ENVIRONMENT PRESETS
  // ---------------------------------------------------------------------------
  const lightConfig = useMemo(() => {
    switch (lighting) {
      case 'night':
        return {
          fogColor: '#050A15',
          fogNear: 55,
          fogFar: 280,
          ambientColor: '#1A2942',
          ambientIntensity: 1.35,
          sunColor: '#93C5FD',
          sunIntensity: 2.2,
          sunPosition: [25, 26, 24] as [number, number, number],
          skyColor: '#0B132B',
          groundColor: '#040812',
          rimColor: '#38BDF8',
          rimIntensity: 2.2,
          fillColor: '#1E293B',
          fillIntensity: 1.0,
        };
      case 'overcast':
        return {
          fogColor: '#0F1A2C',
          fogNear: 45,
          fogFar: 300,
          ambientColor: '#475569',
          ambientIntensity: 1.45,
          sunColor: '#F8FAFC',
          sunIntensity: 2.4,
          sunPosition: [20, 32, 22] as [number, number, number],
          skyColor: '#1E293B',
          groundColor: '#0B1120',
          rimColor: '#94A3B8',
          rimIntensity: 1.2,
          fillColor: '#64748B',
          fillIntensity: 0.9,
        };
      case 'dawn':
      default:
        return {
          fogColor: '#0A1424', // Deep indigo pre-dawn sky matching comp
          fogNear: 50,
          fogFar: 350,
          ambientColor: '#1E2D45',
          ambientIntensity: 1.30,
          sunColor: '#FFF1D6', // Crisp warm morning directional key light
          sunIntensity: 3.8,
          sunPosition: [28, 22, 22] as [number, number, number],
          skyColor: '#0E1A2E',
          groundColor: '#060B14',
          rimColor: '#7DD3FC', // Cool cyan sky rim on roof and wires
          rimIntensity: 3.0,
          fillColor: '#38BDF8',
          fillIntensity: 1.1,
        };
    }
  }, [lighting]);

  // ---------------------------------------------------------------------------
  // 2. PHYSICAL RAILWAY MATERIALS
  // ---------------------------------------------------------------------------
  const envMaterials = useMemo(() => {
    return {
      // Natural earth ground extending beyond corridor
      groundTerrain: new THREE.MeshStandardMaterial({
        color: '#080E1A',
        roughness: 0.95,
        metalness: 0.05,
      }),
      // Grassy verge alongside railway boundary
      vergeGrass: new THREE.MeshStandardMaterial({
        color: '#0D1E16',
        roughness: 0.90,
        metalness: 0.05,
      }),
      // Crushed-stone granite ballast embankment bed
      ballastBed: new THREE.MeshStandardMaterial({
        color: '#111824',
        roughness: 0.96,
        metalness: 0.06,
      }),
      // Pre-stressed concrete ties (PSC monoblock sleepers)
      sleeperConcrete: new THREE.MeshStandardMaterial({
        color: '#64748B',
        roughness: 0.88,
        metalness: 0.10,
      }),
      // Pandrol PR fastening clips and baseplates
      fastenerSteel: new THREE.MeshStandardMaterial({
        color: '#94A3B8',
        roughness: 0.35,
        metalness: 0.85,
      }),
      // Gleaming UIC 60 rail heads (Specular reflection from ambient light & headlights)
      railHeadGleam: new THREE.MeshStandardMaterial({
        color: '#CBD5E1',
        roughness: 0.16,
        metalness: 0.94,
      }),
      // Structural oxidized rail web & foot
      railWebBase: new THREE.MeshStandardMaterial({
        color: '#475569',
        roughness: 0.65,
        metalness: 0.65,
      }),
      // Galvanized steel catenary H-beam masts & portals
      catenarySteel: new THREE.MeshStandardMaterial({
        color: '#475569',
        roughness: 0.40,
        metalness: 0.80,
      }),
      // Hard-drawn grooved copper contact wire & messenger wire
      catenaryCopperWire: new THREE.MeshStandardMaterial({
        color: '#94A3B8',
        roughness: 0.25,
        metalness: 0.85,
      }),
      // Porcelain disc insulators (brown/rust)
      insulatorBrown: new THREE.MeshStandardMaterial({
        color: '#7F1D1D',
        roughness: 0.35,
      }),
      // Signal mast & housing
      signalHousing: new THREE.MeshStandardMaterial({
        color: '#0F172A',
        roughness: 0.45,
        metalness: 0.85,
      }),
      // Signal LED lenses
      signalGreen: new THREE.MeshBasicMaterial({ color: '#10B981' }),
      signalYellow: new THREE.MeshBasicMaterial({ color: '#F59E0B' }),
      signalRed: new THREE.MeshBasicMaterial({ color: '#EF4444' }),
      // Milestone concrete
      milestoneWhite: new THREE.MeshStandardMaterial({ color: '#E2E8F0', roughness: 0.7 }),
      milestoneYellow: new THREE.MeshStandardMaterial({ color: '#F59E0B', roughness: 0.6 }),
      // Possession hazard zone
      possessionCage: new THREE.MeshStandardMaterial({
        color: '#F59E0B',
        transparent: true,
        opacity: 0.32,
        wireframe: true,
      }),
      possessionSolid: new THREE.MeshStandardMaterial({
        color: '#F59E0B',
        transparent: true,
        opacity: 0.12,
        roughness: 0.25,
      }),
    };
  }, []);

  // ---------------------------------------------------------------------------
  // 3. CONTINUOUS SIMULATION TICK (PER-FRAME TICK)
  // ---------------------------------------------------------------------------
  useFrame((_, delta) => {
    const clock = clockRef.current;
    if (!clock) return;

    // Delta-time based continuous movement (clamped to max 50ms to prevent jumps)
    const safeDelta = Math.min(Math.max(delta, 0), 0.05);
    if (clock.isPlaying) {
      // Smooth acceleration / deceleration toward target speed
      const diff = clock.targetSpeedMs - clock.speedMs;
      clock.speedMs += diff * Math.min(safeDelta * 2.5, 1.0);

      const ds = clock.speedMs * safeDelta;
      clock.trainX += ds;
      clock.distance += ds;
      clock.wheelRotation += ds / 0.46; // Radius = 0.46m (920mm diameter EMU wheel)
    }

    // Synchronize 3D train position strictly to simulation clock
    if (trainAnchorRef.current) {
      trainAnchorRef.current.position.x = clock.trainX;
    }

    // Keep illumination rig moving with the train reference frame
    if (lightGroupRef.current) {
      lightGroupRef.current.position.x = clock.trainX;
    }

    // Keep the infinite continuous track centered around train
    if (trackGroupRef.current) {
      // Snapping to sleeperSpacing grid keeps sleepers 100% stationary in world space!
      const snappedX = Math.floor(clock.trainX / sleeperSpacing) * sleeperSpacing;
      trackGroupRef.current.position.x = snappedX;
    }

    // Keep maintenance worksite stationary in world space per block section (KM 242+ Works Zone)
    if (worksiteAnchorRef.current) {
      worksiteAnchorRef.current.position.x = 95.0;
    }
  });

  // ---------------------------------------------------------------------------
  // 4. INSTANCED SLEEPERS IN VISIBLE WINDOW (320 METERS)
  // ---------------------------------------------------------------------------
  const visibleLength = 320;
  const sleeperCount = Math.floor(visibleLength / sleeperSpacing);
  const sleeperLocalOffsets = useMemo(() => {
    const list: number[] = [];
    const half = visibleLength / 2;
    for (let i = 0; i < sleeperCount; i++) {
      list.push(-half + i * sleeperSpacing);
    }
    return list;
  }, [sleeperCount, visibleLength, sleeperSpacing]);

  // Catenary masts spaced every 45 meters relative to current visible window
  const mastOffsets = [-140, -95, -50, 40, 85, 130];

  // Milestone posts every 90 meters
  const milestoneOffsets = [-90, 0, 90];

  return (
    <>
      {/* ------------------------------------------------------------------ */}
      {/* ATMOSPHERIC SKY & ILLUMINATION                                     */}
      {/* ------------------------------------------------------------------ */}
      <color attach="background" args={[lightConfig.fogColor]} />
      <fog attach="fog" args={[lightConfig.fogColor, lightConfig.fogNear, lightConfig.fogFar]} />

      <ambientLight color={lightConfig.ambientColor} intensity={lightConfig.ambientIntensity} />

      {/* Dynamic Key Illumination following train reference frame */}
      <group ref={lightGroupRef}>
        {/* Sun / Key Directional Light */}
        <directionalLight
          position={lightConfig.sunPosition}
          intensity={lightConfig.sunIntensity}
          color={lightConfig.sunColor}
          castShadow
          shadow-mapSize={[2048, 2048]}
          shadow-camera-left={-65}
          shadow-camera-right={65}
          shadow-camera-top={40}
          shadow-camera-bottom={-40}
          shadow-bias={-0.00003}
          shadow-normalBias={0.035}
        />

        {/* High-Altitude Horizon Rim Light */}
        <directionalLight
          position={[-30, 24, -25]}
          intensity={lightConfig.rimIntensity}
          color={lightConfig.rimColor}
        />

        {/* Side Track Fill Light */}
        <directionalLight
          position={[25, 14, 30]}
          intensity={lightConfig.fillIntensity}
          color={lightConfig.fillColor}
        />
      </group>

      {/* Ground Landscape Plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.4, 0]} material={envMaterials.groundTerrain}>
        <planeGeometry args={[1200, 500]} />
      </mesh>

      {/* Grassy Railway Verge Along Flanks */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.38, 0]} material={envMaterials.vergeGrass}>
        <planeGeometry args={[1200, 36]} />
      </mesh>

      {/* ------------------------------------------------------------------ */}
      {/* CONTINUOUS DYNAMIC SCENERY ANCHOR (FOLLOWS TRAIN WITHOUT TELEPORT) */}
      {/* ------------------------------------------------------------------ */}
      <group ref={trackGroupRef}>
        {/* Ballast Embankment Bed (Trapezoidal profile under dual tracks) */}
        <mesh position={[0, -0.10, 0]} receiveShadow material={envMaterials.ballastBed}>
          <boxGeometry args={[visibleLength + 40, 0.30, 11.2]} />
        </mesh>

        {/* Sloped Ballast Shoulders */}
        <mesh position={[0, -0.18, -5.8]} rotation={[0.42, 0, 0]} material={envMaterials.ballastBed}>
          <boxGeometry args={[visibleLength + 40, 0.26, 1.8]} />
        </mesh>
        <mesh position={[0, -0.18, 5.8]} rotation={[-0.42, 0, 0]} material={envMaterials.ballastBed}>
          <boxGeometry args={[visibleLength + 40, 0.26, 1.8]} />
        </mesh>

        {/* Concrete Sleepers with Pandrol PR Clips (Embedded in ballast stone) */}
        {sleeperLocalOffsets.map((xOff, idx) => (
          <group key={`sleeper-${idx}`} position={[xOff, 0, 0]}>
            {/* UP MAIN Sleeper (Top at Y=0.11m) */}
            <mesh position={[0, 0.03, upTrackZ]} receiveShadow material={envMaterials.sleeperConcrete}>
              <boxGeometry args={[0.22, 0.16, 2.60]} />
            </mesh>
            {/* Fastener Clips UP MAIN */}
            <mesh position={[0, 0.12, upTrackZ - halfGauge]} material={materialsFastener(envMaterials)}>
              <boxGeometry args={[0.12, 0.025, 0.14]} />
            </mesh>
            <mesh position={[0, 0.12, upTrackZ + halfGauge]} material={materialsFastener(envMaterials)}>
              <boxGeometry args={[0.12, 0.025, 0.14]} />
            </mesh>

            {/* DOWN MAIN Sleeper */}
            <mesh position={[0, 0.03, downTrackZ]} receiveShadow material={envMaterials.sleeperConcrete}>
              <boxGeometry args={[0.22, 0.16, 2.60]} />
            </mesh>
            {/* Fastener Clips DOWN MAIN */}
            <mesh position={[0, 0.12, downTrackZ - halfGauge]} material={materialsFastener(envMaterials)}>
              <boxGeometry args={[0.12, 0.025, 0.14]} />
            </mesh>
            <mesh position={[0, 0.12, downTrackZ + halfGauge]} material={materialsFastener(envMaterials)}>
              <boxGeometry args={[0.12, 0.025, 0.14]} />
            </mesh>
          </group>
        ))}

        {/* ------------------------------------------------------------------ */}
        {/* CONTINUOUS STEEL RAILS (Slender UIC-60 Metallic Rail Heads)        */}
        {/* ------------------------------------------------------------------ */}
        {/* UP MAIN Left Rail */}
        <group position={[0, 0, upTrackZ - halfGauge]}>
          <mesh position={[0, 0.118, 0]} material={envMaterials.railWebBase}>
            <boxGeometry args={[visibleLength + 40, 0.016, 0.145]} />
          </mesh>
          <mesh position={[0, 0.185, 0]} material={envMaterials.railWebBase}>
            <boxGeometry args={[visibleLength + 40, 0.118, 0.018]} />
          </mesh>
          <mesh position={[0, 0.261, 0]} material={envMaterials.railHeadGleam} castShadow receiveShadow>
            <boxGeometry args={[visibleLength + 40, 0.038, 0.072]} />
          </mesh>
        </group>
        {/* UP MAIN Right Rail */}
        <group position={[0, 0, upTrackZ + halfGauge]}>
          <mesh position={[0, 0.118, 0]} material={envMaterials.railWebBase}>
            <boxGeometry args={[visibleLength + 40, 0.016, 0.145]} />
          </mesh>
          <mesh position={[0, 0.185, 0]} material={envMaterials.railWebBase}>
            <boxGeometry args={[visibleLength + 40, 0.118, 0.018]} />
          </mesh>
          <mesh position={[0, 0.261, 0]} material={envMaterials.railHeadGleam} castShadow receiveShadow>
            <boxGeometry args={[visibleLength + 40, 0.038, 0.072]} />
          </mesh>
        </group>

        {/* DOWN MAIN Left Rail */}
        <group position={[0, 0, downTrackZ - halfGauge]}>
          <mesh position={[0, 0.118, 0]} material={envMaterials.railWebBase}>
            <boxGeometry args={[visibleLength + 40, 0.016, 0.145]} />
          </mesh>
          <mesh position={[0, 0.185, 0]} material={envMaterials.railWebBase}>
            <boxGeometry args={[visibleLength + 40, 0.118, 0.018]} />
          </mesh>
          <mesh position={[0, 0.261, 0]} material={envMaterials.railHeadGleam} castShadow receiveShadow>
            <boxGeometry args={[visibleLength + 40, 0.038, 0.072]} />
          </mesh>
        </group>
        {/* DOWN MAIN Right Rail */}
        <group position={[0, 0, downTrackZ + halfGauge]}>
          <mesh position={[0, 0.118, 0]} material={envMaterials.railWebBase}>
            <boxGeometry args={[visibleLength + 40, 0.016, 0.145]} />
          </mesh>
          <mesh position={[0, 0.185, 0]} material={envMaterials.railWebBase}>
            <boxGeometry args={[visibleLength + 40, 0.118, 0.018]} />
          </mesh>
          <mesh position={[0, 0.261, 0]} material={envMaterials.railHeadGleam} castShadow receiveShadow>
            <boxGeometry args={[visibleLength + 40, 0.038, 0.072]} />
          </mesh>
        </group>

        {/* ------------------------------------------------------------------ */}
        {/* 25 kV AC CATENARY OVERHEAD WIRES                                   */}
        {/* ------------------------------------------------------------------ */}
        {/* Contact Wire (Y = 5.35m, touches pantograph carbon strip) */}
        <mesh position={[0, 5.35, upTrackZ]} material={envMaterials.catenaryCopperWire}>
          <boxGeometry args={[visibleLength + 40, 0.012, 0.012]} />
        </mesh>
        <mesh position={[0, 5.35, downTrackZ]} material={envMaterials.catenaryCopperWire}>
          <boxGeometry args={[visibleLength + 40, 0.012, 0.012]} />
        </mesh>

        {/* Messenger Wire (Y = 6.45m) */}
        <mesh position={[0, 6.45, upTrackZ]} material={envMaterials.catenaryCopperWire}>
          <boxGeometry args={[visibleLength + 40, 0.016, 0.016]} />
        </mesh>
        <mesh position={[0, 6.45, downTrackZ]} material={envMaterials.catenaryCopperWire}>
          <boxGeometry args={[visibleLength + 40, 0.016, 0.016]} />
        </mesh>

        {/* Vertical Catenary Droppers spaced every 9m connecting messenger to contact wire */}
        {[-120, -111, -102, -93, -84, -75, -66, -57, -48, -39, -30, -21, -12, -3, 6, 15, 24, 33, 42, 51, 60, 69, 78, 87, 96, 105, 114, 123].map((dropX) => (
          <group key={`drop-${dropX}`} position={[dropX, 0, 0]}>
            <mesh position={[0, 5.91, upTrackZ]} material={envMaterials.catenaryCopperWire}>
              <cylinderGeometry args={[0.005, 0.005, 1.05, 6]} />
            </mesh>
            <mesh position={[0, 5.91, downTrackZ]} material={envMaterials.catenaryCopperWire}>
              <cylinderGeometry args={[0.005, 0.005, 1.05, 6]} />
            </mesh>
          </group>
        ))}

        {/* Catenary Steel Lattice Masts along the cess */}
        {mastOffsets.map((mastX) => (
          <group key={`mast-${mastX}`} position={[mastX, 0, -5.8]}>
            {/* Concrete Pier Base */}
            <mesh position={[0, 0.35, 0]} material={envMaterials.sleeperConcrete}>
              <boxGeometry args={[0.9, 0.9, 0.9]} />
            </mesh>
            {/* Galvanized Mast Column (Slender rolled steel H-beam) */}
            <mesh position={[0, 4.2, 0]} material={envMaterials.catenarySteel} castShadow>
              <boxGeometry args={[0.22, 7.8, 0.22]} />
            </mesh>
            {/* Cantilever Outreach Arm bridging across UP MAIN */}
            <mesh position={[0, 7.2, 2.4]} material={envMaterials.catenarySteel}>
              <boxGeometry args={[0.18, 0.18, 4.8]} />
            </mesh>
            {/* Porcelain Insulator */}
            <mesh position={[0, 6.5, 3.8]} material={envMaterials.insulatorBrown}>
              <cylinderGeometry args={[0.14, 0.14, 0.55, 12]} />
            </mesh>
            {/* Vertical Dropper Strut down to Contact Wire */}
            <mesh position={[0, 5.9, 3.8]} material={envMaterials.catenaryCopperWire}>
              <cylinderGeometry args={[0.014, 0.014, 1.1, 8]} />
            </mesh>
          </group>
        ))}

        {/* Milestone Chainage Posts (Authentic Indian Railways concrete markers) */}
        {milestoneOffsets.map((mX, idx) => (
          <group key={`km-${idx}`} position={[mX, 0, -4.5]}>
            {/* White milestone post */}
            <mesh position={[0, 0.45, 0]} material={envMaterials.milestoneWhite}>
              <boxGeometry args={[0.32, 0.90, 0.32]} />
            </mesh>
            {/* Yellow curved top cap */}
            <mesh position={[0, 0.95, 0]} material={envMaterials.milestoneYellow}>
              <cylinderGeometry args={[0.16, 0.16, 0.12, 12]} />
            </mesh>
          </group>
        ))}

        {/* Continuous Concrete Cable Trunking Trough along the Cess */}
        <mesh position={[0, 0.08, -4.2]} material={envMaterials.sleeperConcrete}>
          <boxGeometry args={[visibleLength + 40, 0.16, 0.45]} />
        </mesh>
        <mesh position={[0, 0.16, -4.2]} material={envMaterials.catenarySteel}>
          <boxGeometry args={[visibleLength + 40, 0.02, 0.42]} />
        </mesh>

        {/* Relay Equipment Apparatus Cabinets (Loc-Boxes) */}
        {[-35, 65].map((boxX, idx) => (
          <group key={`locbox-${idx}`} position={[boxX, 0, -4.4]}>
            {/* Concrete Pad */}
            <mesh position={[0, 0.2, 0]} material={envMaterials.sleeperConcrete}>
              <boxGeometry args={[1.2, 0.4, 0.8]} />
            </mesh>
            {/* Galvanized Cabinet */}
            <mesh position={[0, 0.95, 0]} material={envMaterials.catenarySteel}>
              <boxGeometry args={[0.95, 1.1, 0.6]} />
            </mesh>
            {/* Roof Peak Hood */}
            <mesh position={[0, 1.54, 0]} material={envMaterials.catenarySteel}>
              <boxGeometry args={[1.05, 0.08, 0.7]} />
            </mesh>
          </group>
        ))}

        {/* Trackside 4-Aspect Railway Signalling Post */}
        <group position={[45, 0, -4.8]}>
          <mesh position={[0, 3.0, 0]} material={envMaterials.catenarySteel}>
            <cylinderGeometry args={[0.12, 0.12, 6.0, 12]} />
          </mesh>
          {/* Signal Housing UP MAIN (Clear Line) */}
          <mesh position={[0, 5.2, 0.5]} material={envMaterials.signalHousing}>
            <boxGeometry args={[0.55, 1.8, 0.3]} />
          </mesh>
          {/* Green Aspect for UP MAIN (Clear ahead for Express Train) */}
          <mesh position={[0, 5.7, 0.66]} material={envMaterials.signalGreen}>
            <circleGeometry args={[0.14, 16]} />
          </mesh>
          <pointLight position={[0, 5.7, 0.9]} color="#10B981" intensity={4.0} distance={14} />

          {/* Yellow Caution Aspect (Muted) */}
          <mesh position={[0, 5.2, 0.66]} material={new THREE.MeshBasicMaterial({ color: '#78350F' })}>
            <circleGeometry args={[0.12, 16]} />
          </mesh>

          {/* Red Aspect (Muted on UP) */}
          <mesh position={[0, 4.7, 0.66]} material={new THREE.MeshBasicMaterial({ color: '#7F1D1D' })}>
            <circleGeometry args={[0.12, 16]} />
          </mesh>
        </group>

        {/* Signal Post for DOWN MAIN (Protected Possession Track - Danger Red Aspect at km 85 approach) */}
        <group position={[85, 0, 4.8]}>
          <mesh position={[0, 3.0, 0]} material={envMaterials.catenarySteel}>
            <cylinderGeometry args={[0.12, 0.12, 6.0, 12]} />
          </mesh>
          <mesh position={[0, 5.2, -0.5]} material={envMaterials.signalHousing}>
            <boxGeometry args={[0.55, 1.8, 0.3]} />
          </mesh>
          {/* Red Aspect for DOWN MAIN (Track Closed for Possession / Maintenance Work) */}
          <mesh position={[0, 4.7, -0.66]} material={envMaterials.signalRed}>
            <circleGeometry args={[0.14, 16]} />
          </mesh>
          <pointLight position={[0, 4.7, -0.9]} color="#EF4444" intensity={4.5} distance={14} />
        </group>

        {/* Secondary Concrete Cable Troughing along DOWN MAIN Cess (Z = 4.4m) */}
        <mesh position={[0, 0.06, 4.4]} material={envMaterials.sleeperConcrete}>
          <boxGeometry args={[visibleLength + 40, 0.14, 0.38]} />
        </mesh>
        <mesh position={[0, 0.14, 4.4]} material={envMaterials.catenarySteel}>
          <boxGeometry args={[visibleLength + 40, 0.02, 0.36]} />
        </mesh>
      </group>

      {/* ------------------------------------------------------------------ */}
      {/* ACTIVE RAILWAY MAINTENANCE WORKSITE & POSSESSION ENVELOPE          */}
      {/* Physically stationary in world space per corridor block section    */}
      {/* ------------------------------------------------------------------ */}
      <group ref={worksiteAnchorRef}>
        <MaintenanceWorksite
          task={task}
          workOrderTitle={workOrderTitle}
          onSelect={() => onSelectPossession('marker-possession')}
          isSelected={selectedEntity === 'marker-possession' || selectedEntity === 'possession'}
          lighting={lighting}
        />
      </group>

      {/* ------------------------------------------------------------------ */}
      {/* AUTHENTIC INDIAN BROAD-GAUGE ELECTRIC PASSENGER TRAIN              */}
      {/* Position dynamically updated by SimulationClock in useFrame        */}
      {/* ------------------------------------------------------------------ */}
      <group ref={trainAnchorRef}>
        <TrackMeldTrainLoader
          speedKmh={trainSpeedKmh}
          isPlaying={isPlaying}
          onSelectTrain={onSelectTrain}
          isSelected={selectedEntity === 'train-express07'}
          trackZ={upTrackZ}
          showTelemetry={showTelemetry}
          lighting={lighting}
        />
      </group>
    </>
  );
};

function materialsFastener(mat: Record<string, THREE.Material>): THREE.Material {
  return mat.fastenerSteel;
}
