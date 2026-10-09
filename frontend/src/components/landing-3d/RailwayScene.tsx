'use client';

import React, { useMemo } from 'react';
import * as THREE from 'three';
import { TrackMeldTrainLoader } from './TrackMeldTrainLoader';
import { CameraMode, LightingPreset } from './types';

interface RailwaySceneProps {
  cameraMode: CameraMode;
  lighting: LightingPreset;
  trainSpeedKmh: number;
  isPlaying: boolean;
  onSelectTrain: () => void;
  onSelectPossession: (id: string) => void;
  selectedEntity: string | null;
}

/**
 * 3D Railway Infrastructure Environment:
 * - Dual broad-gauge tracks (UP MAIN and DOWN MAIN)
 * - Gleaming UIC 60 steel rails with high metallic specular response
 * - Pre-stressed concrete sleepers with Pandrol fastening clips
 * - Realistic crushed-stone ballast embankment bed
 * - 25 kV AC Catenary Masts, Cantilevers, and Dropper Wires
 * - 4-Aspect LED Railway Signals with atmospheric lens glow
 * - Digital twin maintenance possession zones with hazard warning lights
 */
export const RailwayScene: React.FC<RailwaySceneProps> = ({
  lighting,
  trainSpeedKmh,
  isPlaying,
  onSelectTrain,
  onSelectPossession,
  selectedEntity,
}) => {
  const visibleCorridorLength = 180; // 180m high-detail track segment centered on train
  const fullCorridorLength = 320;
  const sleeperSpacing = 0.65;
  const trackGauge = 1.676; // Broad gauge distance between rail centers
  const upTrackZ = -2.0;
  const downTrackZ = 2.0;

  // Cinematic blue-hour / industrial lighting configurations
  const lightConfig = useMemo(() => {
    switch (lighting) {
      case 'night':
        return {
          fogColor: '#04070F',
          ambientColor: '#0F172A',
          ambientIntensity: 0.70,
          sunColor: '#93C5FD',
          sunIntensity: 1.5,
          sunPosition: [18, 22, 16] as [number, number, number],
          rimColor: '#38BDF8',
          rimIntensity: 1.6,
          rimPosition: [-25, 18, -20] as [number, number, number],
          fillColor: '#1E293B',
          fillIntensity: 0.5,
        };
      case 'overcast':
        return {
          fogColor: '#0A101D',
          ambientColor: '#334155',
          ambientIntensity: 1.1,
          sunColor: '#E2E8F0',
          sunIntensity: 1.8,
          sunPosition: [15, 26, 15] as [number, number, number],
          rimColor: '#94A3B8',
          rimIntensity: 1.2,
          rimPosition: [-25, 20, -20] as [number, number, number],
          fillColor: '#475569',
          fillIntensity: 0.8,
        };
      case 'dawn':
      default:
        return {
          fogColor: '#060A13', // Deep blue-hour railway night
          ambientColor: '#1E293B',
          ambientIntensity: 0.90,
          sunColor: '#F1F5F9', // Crisp neutral daylight key on train nose and side
          sunIntensity: 2.1,
          sunPosition: [18, 22, 16] as [number, number, number],
          rimColor: '#7DD3FC', // Restrained sky blue rim on roof cantrail
          rimIntensity: 1.8,
          rimPosition: [-25, 18, -20] as [number, number, number],
          fillColor: '#334155',
          fillIntensity: 0.7,
        };
    }
  }, [lighting]);

  // Shared high-visibility physical railway materials
  const envMaterials = useMemo(() => {
    return {
      ground: new THREE.MeshStandardMaterial({
        color: '#050811',
        roughness: 0.95,
        metalness: 0.05,
      }),
      ballast: new THREE.MeshStandardMaterial({
        color: '#141C28', // Realistic dark charcoal crushed stone embankment
        roughness: 0.90,
        metalness: 0.05,
      }),
      sleeperConcrete: new THREE.MeshStandardMaterial({
        color: '#334155', // Pre-stressed concrete ties
        roughness: 0.85,
        metalness: 0.10,
      }),
      fastenerSteel: new THREE.MeshStandardMaterial({
        color: '#475569',
        roughness: 0.35,
        metalness: 0.85,
      }),
      railSteel: new THREE.MeshStandardMaterial({
        color: '#E2E8F0', // Highly reflective, gleaming steel rail heads
        roughness: 0.15,
        metalness: 0.96,
        envMapIntensity: 1.8,
      }),
      catenarySteel: new THREE.MeshStandardMaterial({
        color: '#334155', // Galvanized structural steel lattice mast
        roughness: 0.50,
        metalness: 0.70,
      }),
      catenaryWire: new THREE.MeshStandardMaterial({
        color: '#64748B',
        roughness: 0.30,
        metalness: 0.90,
      }),
      insulatorBrown: new THREE.MeshStandardMaterial({
        color: '#991B1B',
        roughness: 0.35,
      }),
      signalHousing: new THREE.MeshStandardMaterial({
        color: '#0F172A',
        roughness: 0.5,
        metalness: 0.8,
      }),
      signalGreen: new THREE.MeshBasicMaterial({
        color: '#10B981',
      }),
      signalYellow: new THREE.MeshBasicMaterial({
        color: '#F59E0B',
      }),
      signalRed: new THREE.MeshBasicMaterial({
        color: '#EF4444',
      }),
      possessionCage: new THREE.MeshStandardMaterial({
        color: '#F59E0B',
        transparent: true,
        opacity: 0.35,
        wireframe: true,
      }),
      possessionSolid: new THREE.MeshStandardMaterial({
        color: '#F59E0B',
        transparent: true,
        opacity: 0.15,
        roughness: 0.2,
      }),
    };
  }, []);

  // Sleepers generation along active viewing window
  const sleeperCount = Math.floor(visibleCorridorLength / sleeperSpacing);
  const sleeperOffsets = useMemo(() => {
    const list: number[] = [];
    const half = visibleCorridorLength / 2;
    for (let i = 0; i < sleeperCount; i++) {
      list.push(-half + i * sleeperSpacing);
    }
    return list;
  }, [sleeperCount, visibleCorridorLength, sleeperSpacing]);

  return (
    <>
      {/* Fog for atmospheric depth (distant horizon smoothly blends into deep slate night) */}
      <fog attach="fog" args={[lightConfig.fogColor, 35, 160]} />

      {/* ------------------------------------------------------------------ */}
      {/* CONTROLLED CINEMATIC LIGHTING SETUP                                */}
      {/* ------------------------------------------------------------------ */}
      <ambientLight color={lightConfig.ambientColor} intensity={lightConfig.ambientIntensity} />

      {/* Strong Directional Key Sun/Sky Light */}
      <directionalLight
        position={lightConfig.sunPosition}
        intensity={lightConfig.sunIntensity}
        color={lightConfig.sunColor}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-60}
        shadow-camera-right={60}
        shadow-camera-top={40}
        shadow-camera-bottom={-40}
        shadow-bias={-0.0005}
      />

      {/* Razor-Sharp Electric Blue Rim Backlight (Traces train roof & silhouette) */}
      <directionalLight
        position={lightConfig.rimPosition}
        intensity={lightConfig.rimIntensity}
        color={lightConfig.rimColor}
      />

      {/* Soft Side Track Fill Light */}
      <directionalLight
        position={[25, 8, 30]}
        intensity={lightConfig.fillIntensity}
        color={lightConfig.fillColor}
      />

      {/* Subtle track-level upward fill */}
      <directionalLight position={[0, -5, 10]} intensity={0.2} color="#1E293B" />

      {/* Ground Landscape */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.4, 0]} receiveShadow material={envMaterials.ground}>
        <planeGeometry args={[500, 250]} />
      </mesh>

      {/* ------------------------------------------------------------------ */}
      {/* BALLAST EMBANKMENT BED (Trapezoidal profile under dual tracks)      */}
      {/* ------------------------------------------------------------------ */}
      <mesh position={[0, -0.1, 0]} receiveShadow material={envMaterials.ballast}>
        <boxGeometry args={[fullCorridorLength, 0.5, 11]} />
      </mesh>

      {/* ------------------------------------------------------------------ */}
      {/* CONCRETE SLEEPERS WITH PANDROL CLIPS (Dual Tracks)                 */}
      {/* ------------------------------------------------------------------ */}
      {sleeperOffsets.map((x, idx) => (
        <group key={idx} position={[x, 0, 0]}>
          {/* UP MAIN Sleeper */}
          <mesh position={[0, 0.08, upTrackZ]} receiveShadow material={envMaterials.sleeperConcrete}>
            <boxGeometry args={[0.26, 0.22, 2.75]} />
          </mesh>
          {/* Fastener Pandrol Clips */}
          <mesh position={[0, 0.18, upTrackZ - trackGauge / 2]} material={envMaterials.fastenerSteel}>
            <boxGeometry args={[0.18, 0.04, 0.22]} />
          </mesh>
          <mesh position={[0, 0.18, upTrackZ + trackGauge / 2]} material={envMaterials.fastenerSteel}>
            <boxGeometry args={[0.18, 0.04, 0.22]} />
          </mesh>

          {/* DOWN MAIN Sleeper */}
          <mesh position={[0, 0.08, downTrackZ]} receiveShadow material={envMaterials.sleeperConcrete}>
            <boxGeometry args={[0.26, 0.22, 2.75]} />
          </mesh>
          <mesh position={[0, 0.18, downTrackZ - trackGauge / 2]} material={envMaterials.fastenerSteel}>
            <boxGeometry args={[0.18, 0.04, 0.22]} />
          </mesh>
          <mesh position={[0, 0.18, downTrackZ + trackGauge / 2]} material={envMaterials.fastenerSteel}>
            <boxGeometry args={[0.18, 0.04, 0.22]} />
          </mesh>
        </group>
      ))}

      {/* ------------------------------------------------------------------ */}
      {/* CONTINUOUS STEEL RAILS (Gleaming UIC 60 Profile)                   */}
      {/* Rails sit from Y = 0.20 to Y = 0.42                                */}
      {/* ------------------------------------------------------------------ */}
      {/* UP MAIN TRACK (Z = upTrackZ = -2.0) */}
      <mesh position={[0, 0.32, upTrackZ - trackGauge / 2]} material={envMaterials.railSteel} castShadow receiveShadow>
        <boxGeometry args={[fullCorridorLength, 0.24, 0.12]} />
      </mesh>
      <mesh position={[0, 0.32, upTrackZ + trackGauge / 2]} material={envMaterials.railSteel} castShadow receiveShadow>
        <boxGeometry args={[fullCorridorLength, 0.24, 0.12]} />
      </mesh>

      {/* DOWN MAIN TRACK (Z = downTrackZ = +2.0) */}
      <mesh position={[0, 0.32, downTrackZ - trackGauge / 2]} material={envMaterials.railSteel} castShadow receiveShadow>
        <boxGeometry args={[fullCorridorLength, 0.24, 0.12]} />
      </mesh>
      <mesh position={[0, 0.32, downTrackZ + trackGauge / 2]} material={envMaterials.railSteel} castShadow receiveShadow>
        <boxGeometry args={[fullCorridorLength, 0.24, 0.12]} />
      </mesh>

      {/* ------------------------------------------------------------------ */}
      {/* OVERHEAD CATENARY SYSTEM (25 kV AC OHE)                            */}
      {/* Steel lattice masts, cantilever registration arms, dropper wires   */}
      {/* ------------------------------------------------------------------ */}
      {/* Continuous Contact Wire (at Y = 5.38m, touches pantograph strip) */}
      <mesh position={[0, 5.38, upTrackZ]} material={envMaterials.catenaryWire}>
        <boxGeometry args={[fullCorridorLength, 0.022, 0.022]} />
      </mesh>
      <mesh position={[0, 5.38, downTrackZ]} material={envMaterials.catenaryWire}>
        <boxGeometry args={[fullCorridorLength, 0.022, 0.022]} />
      </mesh>

      {/* Continuous Messenger Wire (at Y = 6.45m) */}
      <mesh position={[0, 6.45, upTrackZ]} material={envMaterials.catenaryWire}>
        <boxGeometry args={[fullCorridorLength, 0.028, 0.028]} />
      </mesh>
      <mesh position={[0, 6.45, downTrackZ]} material={envMaterials.catenaryWire}>
        <boxGeometry args={[fullCorridorLength, 0.028, 0.028]} />
      </mesh>

      {/* Catenary Steel Lattice Masts Spaced Every 36 Meters */}
      {[-72, -36, 0, 36, 72, 108].map((mastX) => (
        <group key={`mast-${mastX}`} position={[mastX, 0, -5.8]}>
          {/* Concrete Mast Foundation Pier */}
          <mesh position={[0, 0.35, 0]} material={envMaterials.sleeperConcrete}>
            <boxGeometry args={[0.9, 0.9, 0.9]} />
          </mesh>

          {/* Galvanized Steel H-Beam Mast Column */}
          <mesh position={[0, 4.2, 0]} material={envMaterials.catenarySteel} castShadow>
            <boxGeometry args={[0.35, 7.8, 0.35]} />
          </mesh>

          {/* Upper Cantilever Outreach Arm bridging across UP MAIN track */}
          <mesh position={[0, 7.2, 2.4]} material={envMaterials.catenarySteel}>
            <boxGeometry args={[0.18, 0.18, 4.8]} />
          </mesh>

          {/* Ceramic Insulators */}
          <mesh position={[0, 6.5, 3.8]} material={envMaterials.insulatorBrown}>
            <cylinderGeometry args={[0.14, 0.14, 0.55, 12]} />
          </mesh>

          {/* Vertical Dropper Strut down to Contact Wire */}
          <mesh position={[0, 5.9, 3.8]} material={envMaterials.catenaryWire}>
            <cylinderGeometry args={[0.012, 0.012, 1.1, 8]} />
          </mesh>

          {/* Warm Amber Inspection Lamp on Mast */}
          <pointLight position={[0, 5.5, 0.4]} color="#F59E0B" intensity={1.5} distance={12} />
        </group>
      ))}

      {/* ------------------------------------------------------------------ */}
      {/* 4-ASPECT AUTOMATIC BLOCK RAILWAY SIGNAL                            */}
      {/* Located at X = 25m, beside the UP MAIN track                       */}
      {/* ------------------------------------------------------------------ */}
      <group position={[28, 0, -4.8]}>
        {/* Signal Post Mast */}
        <mesh position={[0, 3.0, 0]} material={envMaterials.catenarySteel}>
          <cylinderGeometry args={[0.12, 0.12, 6.0, 12]} />
        </mesh>

        {/* Rectangular Signal Head Board with Sun Visors */}
        <mesh position={[0, 5.2, 0.5]} material={envMaterials.signalHousing}>
          <boxGeometry args={[0.55, 1.8, 0.3]} />
        </mesh>

        {/* Aspect 1: Green LED (Proceed - Clear Section) */}
        <mesh position={[0, 5.7, 0.66]} material={envMaterials.signalGreen}>
          <circleGeometry args={[0.14, 16]} />
        </mesh>
        <pointLight position={[0, 5.7, 0.9]} color="#10B981" intensity={3.5} distance={8} />

        {/* Aspect 2: Yellow LED */}
        <mesh position={[0, 5.3, 0.66]} material={envMaterials.signalHousing}>
          <circleGeometry args={[0.14, 16]} />
        </mesh>

        {/* Aspect 3: Red LED */}
        <mesh position={[0, 4.9, 0.66]} material={envMaterials.signalHousing}>
          <circleGeometry args={[0.14, 16]} />
        </mesh>
      </group>

      {/* ------------------------------------------------------------------ */}
      {/* DIGITAL TWIN POSSESSION ENVELOPE (ON DOWN MAIN LINE)               */}
      {/* Demonstrates active maintenance block S-04 scheduled by TrackMeld  */}
      {/* ------------------------------------------------------------------ */}
      <group
        position={[65, 1.4, downTrackZ]}
        onClick={(e) => {
          e.stopPropagation();
          onSelectPossession('possession-s04');
        }}
      >
        {/* Holographic Wireframe Boundary Cage */}
        <mesh material={envMaterials.possessionCage}>
          <boxGeometry args={[32, 3.2, 3.6]} />
        </mesh>
        <mesh material={envMaterials.possessionSolid}>
          <boxGeometry args={[31.8, 3.16, 3.56]} />
        </mesh>

        {/* Hazard Warning Markers along the worksite perimeter */}
        {[-18, -6, 6, 18].map((offset, idx) => (
          <group key={idx} position={[offset, -1.2, 2.1]}>
            <mesh material={envMaterials.signalHousing}>
              <cylinderGeometry args={[0.04, 0.04, 1.2, 8]} />
            </mesh>
            <mesh position={[0, 0.6, 0]} material={envMaterials.signalYellow}>
              <boxGeometry args={[0.22, 0.22, 0.04]} />
            </mesh>
            <pointLight position={[0, 0.6, 0.2]} color="#F59E0B" intensity={1.8} distance={6} />
          </group>
        ))}
      </group>

      {/* ------------------------------------------------------------------ */}
      {/* HIGH-FIDELITY HIGH-SPEED EXPRESS TRAIN (ON UP MAIN TRACK)          */}
      {/* ------------------------------------------------------------------ */}
      <TrackMeldTrainLoader
        speedKmh={trainSpeedKmh}
        isPlaying={isPlaying}
        onSelectTrain={onSelectTrain}
        isSelected={selectedEntity === 'train-express07'}
        trackZ={upTrackZ}
      />
    </>
  );
};
