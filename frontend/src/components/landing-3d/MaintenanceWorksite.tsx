'use client';

import React, { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { MaintenanceTask } from '@/types/railway';

interface MaintenanceWorksiteProps {
  task?: MaintenanceTask | null;
  workOrderTitle?: string | null;
  onSelect?: () => void;
  isSelected?: boolean;
  lighting?: 'dawn' | 'night' | 'overcast';
}

/**
 * Authentic 3D Railway Maintenance Worksite
 * Renders data-driven track machinery, high-vis maintenance crew,
 * portable LED floodlight towers, and safety possession boundary markers.
 */
export const MaintenanceWorksite: React.FC<MaintenanceWorksiteProps> = ({
  task,
  workOrderTitle = 'WO-1847 Plain Track CSM Tamping',
  onSelect,
  isSelected = false,
  lighting = 'dawn',
}) => {
  const beaconLightRef = useRef<THREE.PointLight>(null);
  const strobeMeshRef = useRef<THREE.Mesh>(null);

  // Determine track assignment: if task specifies UP, place on UP; otherwise default to DOWN MAIN (Z = +2.0m)
  const trackZ = task?.track_type === 'UP' ? -2.0 : 2.0;
  const worksiteCenterX = 0.0; // Anchored at parent group position

  // Determine machinery type from task metadata or title
  const taskText = `${task?.title || ''} ${task?.task_code || ''} ${task?.department || ''} ${workOrderTitle || ''}`.toUpperCase();
  const machineType = useMemo<'CSM' | 'TOWER_WAGON' | 'USFD'>(() => {
    if (taskText.includes('OHE') || taskText.includes('CATENARY') || taskText.includes('ELECTRICAL') || taskText.includes('TRD')) {
      return 'TOWER_WAGON';
    }
    if (taskText.includes('USFD') || taskText.includes('ULTRASONIC') || taskText.includes('FLAW') || taskText.includes('TESTING')) {
      return 'USFD';
    }
    return 'CSM'; // Default to Continuous Action Tamper CSM-01
  }, [taskText]);

  // Amber warning beacon strobe oscillation
  useFrame((state) => {
    const time = state.clock.elapsedTime;
    const strobe = Math.sin(time * 8.0) > 0.2 ? 1.0 : 0.15;
    if (beaconLightRef.current) {
      beaconLightRef.current.intensity = strobe * (lighting === 'night' ? 4.5 : 2.5);
    }
    if (strobeMeshRef.current) {
      (strobeMeshRef.current.material as THREE.MeshBasicMaterial).opacity = strobe;
    }
  });

  // ---------------------------------------------------------------------------
  // PBR MATERIALS FOR WORKSITE INFRASTRUCTURE
  // ---------------------------------------------------------------------------
  const mats = useMemo(() => {
    return {
      // Track Machinery Yellow
      machineYellow: new THREE.MeshStandardMaterial({
        color: '#EAB308',
        metalness: 0.45,
        roughness: 0.35,
      }),
      // Track Machinery Industrial Orange Accent
      machineOrange: new THREE.MeshStandardMaterial({
        color: '#EA580C',
        metalness: 0.40,
        roughness: 0.35,
      }),
      // Heavy Cast Steel Chassis & Underframe
      heavySteelDark: new THREE.MeshStandardMaterial({
        color: '#1E293B',
        metalness: 0.85,
        roughness: 0.45,
      }),
      // Hydraulic Cylinders & Chrome Pistons
      chromeHydraulic: new THREE.MeshStandardMaterial({
        color: '#E2E8F0',
        metalness: 0.95,
        roughness: 0.12,
      }),
      // Tamping Tines (Hardened Alloy Steel)
      tampingTineSteel: new THREE.MeshStandardMaterial({
        color: '#475569',
        metalness: 0.90,
        roughness: 0.30,
      }),
      // Operator Cab Glass
      cabGlass: new THREE.MeshStandardMaterial({
        color: '#0A1220',
        metalness: 0.85,
        roughness: 0.10,
        transparent: true,
        opacity: 0.80,
      }),
      // High-Vis PPE Fluorescent Orange
      ppeOrange: new THREE.MeshStandardMaterial({
        color: '#FF5400',
        roughness: 0.65,
      }),
      // Reflective Silver Stripe on Vests
      ppeReflective: new THREE.MeshStandardMaterial({
        color: '#F8FAFC',
        metalness: 0.90,
        roughness: 0.15,
      }),
      // Safety Hard Hat Yellow
      hardHatYellow: new THREE.MeshStandardMaterial({
        color: '#FACC15',
        roughness: 0.30,
      }),
      // Safety Hard Hat White (Supervisor / SSE)
      hardHatWhite: new THREE.MeshStandardMaterial({
        color: '#FFFFFF',
        roughness: 0.30,
      }),
      // Dark Work Trousers
      trousersNavy: new THREE.MeshStandardMaterial({
        color: '#0F172A',
        roughness: 0.85,
      }),
      // Safety Barrier Red
      barrierRed: new THREE.MeshStandardMaterial({
        color: '#DC2626',
        roughness: 0.40,
      }),
      // Safety Barrier White
      barrierWhite: new THREE.MeshStandardMaterial({
        color: '#F8FAFC',
        roughness: 0.40,
      }),
      // Portable Floodlight Metal Tripod
      tripodSteel: new THREE.MeshStandardMaterial({
        color: '#334155',
        metalness: 0.80,
        roughness: 0.35,
      }),
      // LED Floodlight Emitter
      floodlightEmitter: new THREE.MeshBasicMaterial({
        color: '#FEF08A',
      }),
      // Amber Warning Beacon Core
      strobeAmber: new THREE.MeshBasicMaterial({
        color: '#F59E0B',
        transparent: true,
      }),
      // Translucent Safety Possession Cage
      possessionZone: new THREE.MeshStandardMaterial({
        color: isSelected ? '#38BDF8' : '#F59E0B',
        transparent: true,
        opacity: isSelected ? 0.22 : 0.10,
        roughness: 0.2,
      }),
      possessionBorder: new THREE.MeshStandardMaterial({
        color: isSelected ? '#38BDF8' : '#F59E0B',
        transparent: true,
        opacity: isSelected ? 0.60 : 0.35,
        wireframe: true,
      }),
    };
  }, [isSelected]);

  // ---------------------------------------------------------------------------
  // HELPER: RENDER HUMAN MAINTENANCE CREW MEMBER
  // ---------------------------------------------------------------------------
  const renderCrewMember = (id: string, x: number, z: number, rotationY = 0, isSupervisor = false) => {
    return (
      <group key={id} position={[x, 0.44, z]} rotation={[0, rotationY, 0]}>
        {/* Work Boots */}
        <mesh position={[-0.08, 0.05, 0]} material={mats.heavySteelDark}>
          <boxGeometry args={[0.12, 0.10, 0.18]} />
        </mesh>
        <mesh position={[0.08, 0.05, 0]} material={mats.heavySteelDark}>
          <boxGeometry args={[0.12, 0.10, 0.18]} />
        </mesh>

        {/* Legs / Trousers */}
        <mesh position={[-0.08, 0.42, 0]} material={mats.trousersNavy}>
          <cylinderGeometry args={[0.065, 0.07, 0.68, 8]} />
        </mesh>
        <mesh position={[0.08, 0.42, 0]} material={mats.trousersNavy}>
          <cylinderGeometry args={[0.065, 0.07, 0.68, 8]} />
        </mesh>

        {/* Torso with High-Vis Orange Safety Vest */}
        <mesh position={[0, 1.05, 0]} material={mats.ppeOrange} castShadow>
          <boxGeometry args={[0.34, 0.58, 0.22]} />
        </mesh>

        {/* Horizontal Retro-Reflective Silver Stripes on Vest */}
        <mesh position={[0, 0.98, 0.115]} material={mats.ppeReflective}>
          <boxGeometry args={[0.32, 0.04, 0.01]} />
        </mesh>
        <mesh position={[0, 1.12, 0.115]} material={mats.ppeReflective}>
          <boxGeometry args={[0.32, 0.04, 0.01]} />
        </mesh>

        {/* Arms */}
        <mesh position={[-0.20, 1.0, 0]} material={mats.ppeOrange}>
          <cylinderGeometry args={[0.045, 0.045, 0.50, 8]} />
        </mesh>
        <mesh position={[0.20, 1.0, 0]} material={mats.ppeOrange}>
          <cylinderGeometry args={[0.045, 0.045, 0.50, 8]} />
        </mesh>

        {/* Head */}
        <mesh position={[0, 1.44, 0]} material={mats.ppeReflective}>
          <sphereGeometry args={[0.09, 10, 10]} />
        </mesh>

        {/* Safety Hard Hat with Brim */}
        <group position={[0, 1.51, 0]}>
          <mesh material={isSupervisor ? mats.hardHatWhite : mats.hardHatYellow}>
            <sphereGeometry args={[0.115, 12, 10, 0, Math.PI * 2, 0, Math.PI / 2]} />
          </mesh>
          <mesh position={[0, -0.01, 0.03]} rotation={[-0.1, 0, 0]} material={isSupervisor ? mats.hardHatWhite : mats.hardHatYellow}>
            <cylinderGeometry args={[0.13, 0.13, 0.02, 12]} />
          </mesh>
        </group>
      </group>
    );
  };

  // ---------------------------------------------------------------------------
  // HELPER: PORTABLE LED FLOODLIGHT TRIPOD TOWER
  // ---------------------------------------------------------------------------
  const renderFloodlight = (id: string, x: number, z: number, targetPos: [number, number, number]) => {
    return (
      <group key={id} position={[x, 0.44, z]}>
        {/* Tripod Stand Legs */}
        <mesh position={[0, 0.8, 0]} material={mats.tripodSteel}>
          <cylinderGeometry args={[0.03, 0.03, 1.6, 6]} />
        </mesh>
        <mesh position={[-0.35, 0.35, -0.2]} rotation={[0, 0, 0.5]} material={mats.tripodSteel}>
          <cylinderGeometry args={[0.02, 0.02, 0.8, 6]} />
        </mesh>
        <mesh position={[0.35, 0.35, -0.2]} rotation={[0, 0, -0.5]} material={mats.tripodSteel}>
          <cylinderGeometry args={[0.02, 0.02, 0.8, 6]} />
        </mesh>
        <mesh position={[0, 0.35, 0.4]} rotation={[-0.5, 0, 0]} material={mats.tripodSteel}>
          <cylinderGeometry args={[0.02, 0.02, 0.8, 6]} />
        </mesh>

        {/* Dual LED Head Fixture */}
        <mesh position={[0, 1.65, 0]} material={mats.heavySteelDark}>
          <boxGeometry args={[0.42, 0.18, 0.14]} />
        </mesh>
        <mesh position={[0, 1.65, 0.08]} material={mats.floodlightEmitter}>
          <boxGeometry args={[0.38, 0.14, 0.02]} />
        </mesh>

        {/* Targeted Task Illumination Spot */}
        <spotLight
          position={[0, 1.65, 0.1]}
          target-position={targetPos}
          color="#FEF9C3"
          intensity={lighting === 'night' ? 18.0 : 8.0}
          distance={22}
          angle={Math.PI / 4.2}
          penumbra={0.4}
          castShadow
        />
      </group>
    );
  };

  return (
    <group
      position={[worksiteCenterX, 0, trackZ]}
      onClick={(e) => {
        e.stopPropagation();
        onSelect?.();
      }}
    >
      {/* ------------------------------------------------------------------ */}
      {/* 1. SAFETY POSSESSION ENVELOPE (Semi-transparent perimeter boundary)*/}
      {/* ------------------------------------------------------------------ */}
      <group position={[0, 1.8, 0]}>
        <mesh material={mats.possessionZone}>
          <boxGeometry args={[36.0, 3.6, 4.6]} />
        </mesh>
        <mesh material={mats.possessionBorder}>
          <boxGeometry args={[36.0, 3.6, 4.6]} />
        </mesh>
      </group>

      {/* ------------------------------------------------------------------ */}
      {/* 2. TRACK CLEARANCE SAFETY CONES & BOUNDARY CHAIN (Inter-Track Cess)*/}
      {/* ------------------------------------------------------------------ */}
      {[-16, -12, -8, -4, 0, 4, 8, 12, 16].map((coneX, idx) => (
        <group key={`cone-${idx}`} position={[coneX, 0.44, trackZ > 0 ? -1.8 : 1.8]}>
          {/* Base */}
          <mesh material={mats.barrierRed}>
            <boxGeometry args={[0.26, 0.04, 0.26]} />
          </mesh>
          {/* Conical Post with Alternating Red/White Bands */}
          <mesh position={[0, 0.25, 0]} material={mats.barrierRed}>
            <cylinderGeometry args={[0.04, 0.11, 0.46, 10]} />
          </mesh>
          <mesh position={[0, 0.26, 0]} material={mats.barrierWhite}>
            <cylinderGeometry args={[0.065, 0.085, 0.12, 10]} />
          </mesh>
        </group>
      ))}

      {/* Continuous Red/White Safety Boundary Barrier Tape along the Cess */}
      <mesh position={[0, 0.76, trackZ > 0 ? -1.8 : 1.8]} material={mats.barrierRed}>
        <boxGeometry args={[32.0, 0.04, 0.02]} />
      </mesh>
      <mesh position={[0, 0.64, trackZ > 0 ? -1.8 : 1.8]} material={mats.barrierWhite}>
        <boxGeometry args={[32.0, 0.04, 0.02]} />
      </mesh>

      {/* ------------------------------------------------------------------ */}
      {/* 2B. INDIAN RAILWAYS OFFICIAL POSSESSION LIMIT BOARD                 */}
      {/* ------------------------------------------------------------------ */}
      <group position={[15.5, 0.44, trackZ > 0 ? -2.2 : 2.2]} rotation={[0, Math.PI / 2, 0]}>
        {/* Steel Mounting Stanchions */}
        <mesh position={[-0.6, 0.9, 0]} material={mats.tripodSteel}>
          <cylinderGeometry args={[0.035, 0.035, 1.8, 8]} />
        </mesh>
        <mesh position={[0.6, 0.9, 0]} material={mats.tripodSteel}>
          <cylinderGeometry args={[0.035, 0.035, 1.8, 8]} />
        </mesh>
        {/* High-Vis Board Backing (Red Border & White Face) */}
        <mesh position={[0, 1.35, 0]} material={mats.barrierRed}>
          <boxGeometry args={[1.5, 0.85, 0.04]} />
        </mesh>
        <mesh position={[0, 1.35, 0.025]} material={mats.barrierWhite}>
          <boxGeometry args={[1.42, 0.77, 0.02]} />
        </mesh>
        {/* Warning Red Chevron Header Strip */}
        <mesh position={[0, 1.62, 0.038]} material={mats.barrierRed}>
          <boxGeometry args={[1.38, 0.16, 0.01]} />
        </mesh>
        {/* Tactical Text Simulation Lines */}
        <mesh position={[0, 1.44, 0.038]} material={mats.heavySteelDark}>
          <boxGeometry args={[1.2, 0.04, 0.01]} />
        </mesh>
        <mesh position={[0, 1.34, 0.038]} material={mats.heavySteelDark}>
          <boxGeometry args={[1.0, 0.03, 0.01]} />
        </mesh>
        <mesh position={[0, 1.24, 0.038]} material={mats.barrierRed}>
          <boxGeometry args={[0.9, 0.04, 0.01]} />
        </mesh>
      </group>

      {/* ------------------------------------------------------------------ */}
      {/* 2C. LOOKOUT / FLAGMAN WITH RED SAFETY SIGNAL FLAG                   */}
      {/* Stationed at approach boundary facing oncoming traffic              */}
      {/* ------------------------------------------------------------------ */}
      <group position={[17.0, 0.44, trackZ > 0 ? -1.3 : 1.3]} rotation={[0, -Math.PI / 2, 0]}>
        {renderCrewMember('flagman-lookout', 0, 0, 0, false)}
        {/* Red Warning Signal Flag extended toward live line */}
        <group position={[0.22, 1.15, 0.2]}>
          <mesh rotation={[0.4, 0, 0]} material={mats.tripodSteel}>
            <cylinderGeometry args={[0.015, 0.015, 1.1, 8]} />
          </mesh>
          <mesh position={[0, 0.35, 0.24]} material={mats.barrierRed}>
            <boxGeometry args={[0.01, 0.42, 0.52]} />
          </mesh>
        </group>
      </group>

      {/* ------------------------------------------------------------------ */}
      {/* 2D. TRACKSIDE MAINTENANCE TOOL TROLLEY & HYDRAULIC POWER PACK       */}
      {/* ------------------------------------------------------------------ */}
      <group position={[-12.0, 0.44, trackZ > 0 ? 1.6 : -1.6]}>
        {/* Portable Generator / Hydraulic Unit */}
        <mesh position={[0, 0.4, 0]} material={mats.machineYellow}>
          <boxGeometry args={[1.1, 0.7, 0.75]} />
        </mesh>
        <mesh position={[0, 0.78, 0]} material={mats.tripodSteel}>
          <boxGeometry args={[1.15, 0.06, 0.8]} />
        </mesh>
        {/* Grease / Lubricant Drum for Switch Expansion Joint Greasing */}
        <mesh position={[0.9, 0.45, 0]} material={mats.heavySteelDark}>
          <cylinderGeometry args={[0.28, 0.28, 0.85, 14]} />
        </mesh>
        {/* Pressure Gauge & Wand */}
        <mesh position={[0.9, 0.92, 0]} material={mats.chromeHydraulic}>
          <cylinderGeometry args={[0.06, 0.06, 0.12, 10]} />
        </mesh>
      </group>

      {/* ------------------------------------------------------------------ */}
      {/* 2E. TACTICAL 3D POSSESSION INFORMATION STATUS DISPLAY               */}
      {/* ------------------------------------------------------------------ */}
      <group position={[0, 5.2, 0]}>
        {/* Floating Background Banner Plate */}
        <mesh material={mats.heavySteelDark}>
          <boxGeometry args={[9.5, 1.15, 0.08]} />
        </mesh>
        {/* Status Border Frame */}
        <mesh position={[0, 0, 0.045]} material={mats.possessionBorder}>
          <boxGeometry args={[9.4, 1.05, 0.02]} />
        </mesh>
        {/* Amber Safety Header Strip */}
        <mesh position={[0, 0.38, 0.05]} material={mats.strobeAmber}>
          <boxGeometry args={[9.2, 0.16, 0.02]} />
        </mesh>
        {/* Work Order Title Indicator Band */}
        <mesh position={[-1.2, 0.05, 0.05]} material={mats.ppeReflective}>
          <boxGeometry args={[6.2, 0.22, 0.02]} />
        </mesh>
        {/* Approved Status Badge */}
        <mesh position={[3.2, 0.05, 0.05]} material={mats.hardHatYellow}>
          <boxGeometry args={[2.2, 0.22, 0.02]} />
        </mesh>
        {/* Simulated Demo Disclaimer Band */}
        <mesh position={[0, -0.32, 0.05]} material={mats.barrierRed}>
          <boxGeometry args={[9.2, 0.18, 0.02]} />
        </mesh>
      </group>

      {/* ------------------------------------------------------------------ */}
      {/* 3. DATA-DRIVEN RAILWAY MACHINERY                                    */}
      {/* ------------------------------------------------------------------ */}

      {/* --- MACHINERY CASE A: CONTINUOUS ACTION TAMPER CSM-01 --- */}
      {machineType === 'CSM' && (
        <group position={[0, 0, 0]}>
          {/* Heavy Steel Chassis */}
          <mesh position={[0, 1.25, 0]} material={mats.heavySteelDark} castShadow receiveShadow>
            <boxGeometry args={[15.6, 0.60, 2.90]} />
          </mesh>

          {/* Machine Yellow Primary Superstructure Body */}
          <mesh position={[-0.8, 2.35, 0]} material={mats.machineYellow} castShadow receiveShadow>
            <boxGeometry args={[12.2, 1.65, 2.85]} />
          </mesh>

          {/* Forward Operator Driving Cab (Right side / +X) */}
          <group position={[6.0, 2.50, 0]}>
            {/* Cab Structure */}
            <mesh material={mats.machineYellow} castShadow>
              <boxGeometry args={[3.2, 1.95, 2.90]} />
            </mesh>
            {/* Front Cab Windshield Glass */}
            <mesh position={[1.61, 0.25, 0]} material={mats.cabGlass}>
              <boxGeometry args={[0.02, 1.05, 2.45]} />
            </mesh>
            {/* Side Cab Windows */}
            <mesh position={[0.2, 0.25, 1.46]} material={mats.cabGlass}>
              <boxGeometry args={[1.8, 0.90, 0.02]} />
            </mesh>
            <mesh position={[0.2, 0.25, -1.46]} material={mats.cabGlass}>
              <boxGeometry args={[1.8, 0.90, 0.02]} />
            </mesh>
            {/* Twin High-Intensity Work Searchlights */}
            <mesh position={[1.62, -0.45, -0.9]} rotation={[0, 0, Math.PI / 2]} material={mats.chromeHydraulic}>
              <cylinderGeometry args={[0.12, 0.12, 0.10, 12]} />
            </mesh>
            <mesh position={[1.62, -0.45, 0.9]} rotation={[0, 0, Math.PI / 2]} material={mats.chromeHydraulic}>
              <cylinderGeometry args={[0.12, 0.12, 0.10, 12]} />
            </mesh>
          </group>

          {/* Roof Engine Louvers & Radiator Grill */}
          <mesh position={[-2.5, 3.25, 0]} material={mats.heavySteelDark}>
            <boxGeometry args={[6.8, 0.22, 2.4]} />
          </mesh>

          {/* Diesel Exhaust Stack */}
          <group position={[-5.2, 3.8, 0.8]}>
            <mesh material={mats.heavySteelDark}>
              <cylinderGeometry args={[0.10, 0.10, 1.2, 10]} />
            </mesh>
            <mesh position={[0, 0.65, 0]} material={mats.heavySteelDark} rotation={[0, 0, 0.4]}>
              <cylinderGeometry args={[0.10, 0.10, 0.25, 10]} />
            </mesh>
          </group>

          {/* Hydraulic Tamping Work Units (Suspended under center chassis) */}
          <group position={[0.6, 0.85, 0]}>
            {/* Left Rail Tamping Bank (Inserts into ballast around rail) */}
            <group position={[0, 0, -0.838]}>
              <mesh position={[0, 0.2, 0]} material={mats.machineOrange}>
                <boxGeometry args={[1.2, 0.45, 0.55]} />
              </mesh>
              {/* Hydraulic Actuator Rams */}
              <mesh position={[-0.35, 0.05, 0]} material={mats.chromeHydraulic}>
                <cylinderGeometry args={[0.06, 0.06, 0.45, 8]} />
              </mesh>
              <mesh position={[0.35, 0.05, 0]} material={mats.chromeHydraulic}>
                <cylinderGeometry args={[0.06, 0.06, 0.45, 8]} />
              </mesh>
              {/* Tamping Tines entering ballast */}
              <mesh position={[-0.40, -0.35, 0.16]} rotation={[0, 0, 0.15]} material={mats.tampingTineSteel}>
                <boxGeometry args={[0.08, 0.52, 0.10]} />
              </mesh>
              <mesh position={[0.40, -0.35, -0.16]} rotation={[0, 0, -0.15]} material={mats.tampingTineSteel}>
                <boxGeometry args={[0.08, 0.52, 0.10]} />
              </mesh>
            </group>

            {/* Right Rail Tamping Bank */}
            <group position={[0, 0, 0.838]}>
              <mesh position={[0, 0.2, 0]} material={mats.machineOrange}>
                <boxGeometry args={[1.2, 0.45, 0.55]} />
              </mesh>
              <mesh position={[-0.35, 0.05, 0]} material={mats.chromeHydraulic}>
                <cylinderGeometry args={[0.06, 0.06, 0.45, 8]} />
              </mesh>
              <mesh position={[0.35, 0.05, 0]} material={mats.chromeHydraulic}>
                <cylinderGeometry args={[0.06, 0.06, 0.45, 8]} />
              </mesh>
              <mesh position={[-0.40, -0.35, 0.16]} rotation={[0, 0, 0.15]} material={mats.tampingTineSteel}>
                <boxGeometry args={[0.08, 0.52, 0.10]} />
              </mesh>
              <mesh position={[0.40, -0.35, -0.16]} rotation={[0, 0, -0.15]} material={mats.tampingTineSteel}>
                <boxGeometry args={[0.08, 0.52, 0.10]} />
              </mesh>
            </group>
          </group>

          {/* Machine Bogies & Steel Wheelsets */}
          {[-5.2, 5.2].map((bx, idx) => (
            <group key={`csm-bogie-${idx}`} position={[bx, 0.55, 0]}>
              <mesh material={mats.heavySteelDark}>
                <boxGeometry args={[2.4, 0.35, 2.1]} />
              </mesh>
              {[-0.8, 0.8].map((wx, wIdx) => (
                <group key={`csm-wh-${wIdx}`} position={[wx, 0.35, 0]}>
                  <mesh rotation={[Math.PI / 2, 0, 0]} material={mats.heavySteelDark}>
                    <cylinderGeometry args={[0.42, 0.42, 1.85, 16]} />
                  </mesh>
                </group>
              ))}
            </group>
          ))}

          {/* Flashing Amber Hazard Strobe Beacon atop Cab */}
          <group position={[6.0, 3.65, 0]}>
            <mesh ref={strobeMeshRef} material={mats.strobeAmber}>
              <cylinderGeometry args={[0.16, 0.16, 0.28, 12]} />
            </mesh>
            <pointLight
              ref={beaconLightRef}
              color="#F59E0B"
              intensity={3.5}
              distance={18}
            />
          </group>
        </group>
      )}

      {/* --- MACHINERY CASE B: 25 kV AC OHE WIRING TOWER WAGON --- */}
      {machineType === 'TOWER_WAGON' && (
        <group position={[0, 0, 0]}>
          {/* Railcar Body */}
          <mesh position={[0, 2.1, 0]} material={mats.machineOrange} castShadow receiveShadow>
            <boxGeometry args={[14.2, 2.2, 2.95]} />
          </mesh>

          {/* Raised Hydraulic Scissor Lift Platform Reaching Contact Wire (Y = 5.2m) */}
          <group position={[0, 3.3, 0]}>
            {/* Scissor Braces */}
            <mesh position={[0, 0.75, -0.8]} rotation={[0.4, 0, 0]} material={mats.heavySteelDark}>
              <boxGeometry args={[3.2, 0.08, 0.08]} />
            </mesh>
            <mesh position={[0, 0.75, 0.8]} rotation={[-0.4, 0, 0]} material={mats.heavySteelDark}>
              <boxGeometry args={[3.2, 0.08, 0.08]} />
            </mesh>
            {/* Elevated Work Basket */}
            <group position={[0, 1.85, 0]}>
              {/* Floor Grid */}
              <mesh material={mats.heavySteelDark}>
                <boxGeometry args={[4.2, 0.10, 2.2]} />
              </mesh>
              {/* Safety Railings */}
              <mesh position={[0, 0.55, -1.05]} material={mats.machineYellow}>
                <boxGeometry args={[4.2, 1.0, 0.06]} />
              </mesh>
              <mesh position={[0, 0.55, 1.05]} material={mats.machineYellow}>
                <boxGeometry args={[4.2, 1.0, 0.06]} />
              </mesh>
              {/* Linemen working aloft on wire */}
              {renderCrewMember('lineman-1', -0.8, 0, 0)}
              {renderCrewMember('lineman-2', 0.8, 0, Math.PI)}
            </group>
          </group>

          {/* Underframe & Bogies */}
          {[-4.6, 4.6].map((bx, idx) => (
            <group key={`tw-bogie-${idx}`} position={[bx, 0.55, 0]}>
              <mesh material={mats.heavySteelDark}>
                <boxGeometry args={[2.2, 0.35, 2.1]} />
              </mesh>
            </group>
          ))}
        </group>
      )}

      {/* --- MACHINERY CASE C: USFD ULTRASONIC RAIL FLAW TESTING CART --- */}
      {machineType === 'USFD' && (
        <group position={[0, 0, 0]}>
          {/* Hand Cart Tubular Aluminium Frame */}
          <mesh position={[0, 0.8, 0]} material={mats.chromeHydraulic}>
            <boxGeometry args={[1.8, 0.65, 1.75]} />
          </mesh>
          {/* Couplant Water Storage Tank */}
          <mesh position={[-0.3, 1.05, 0]} material={mats.heavySteelDark}>
            <cylinderGeometry args={[0.22, 0.22, 0.55, 12]} />
          </mesh>
          {/* Multi-Channel Flaw Detector Console Display */}
          <mesh position={[0.4, 1.15, 0]} material={mats.machineYellow}>
            <boxGeometry args={[0.45, 0.35, 0.55]} />
          </mesh>
          <mesh position={[0.42, 1.25, 0]} material={mats.cabGlass}>
            <boxGeometry args={[0.35, 0.20, 0.02]} />
          </mesh>
          {/* Four Small Flanged Sled Wheels on Rails */}
          {[-0.6, 0.6].map((wx, wIdx) => (
            <group key={`usfd-wh-${wIdx}`}>
              <mesh position={[wx, 0.44, -0.838]} rotation={[Math.PI / 2, 0, 0]} material={mats.heavySteelDark}>
                <cylinderGeometry args={[0.12, 0.12, 0.08, 12]} />
              </mesh>
              <mesh position={[wx, 0.44, 0.838]} rotation={[Math.PI / 2, 0, 0]} material={mats.heavySteelDark}>
                <cylinderGeometry args={[0.12, 0.12, 0.08, 12]} />
              </mesh>
            </group>
          ))}
        </group>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* 4. GROUND MAINTENANCE CREW PERSONNEL                               */}
      {/* ------------------------------------------------------------------ */}
      {/* Worker 1: Banksman directing machine with hand signals */}
      {renderCrewMember('crew-banksman', 10.5, 0.8, -Math.PI / 2)}

      {/* Worker 2: Track technician with rail wrench inspecting sleepers */}
      {renderCrewMember('crew-tech1', -9.2, -0.6, Math.PI / 4)}

      {/* Worker 3: Track technician kneeling / inspecting fasteners */}
      {renderCrewMember('crew-tech2', 4.5, 1.6, Math.PI / 3)}

      {/* Worker 4: Senior Section Engineer (Supervisor with white hard hat) */}
      {renderCrewMember('crew-sse', 8.2, -1.8, 0, true)}

      {/* ------------------------------------------------------------------ */}
      {/* 5. PORTABLE LED TASK FLOODLIGHT TOWERS                              */}
      {/* ------------------------------------------------------------------ */}
      {renderFloodlight('flood-1', 11.0, -2.4, [6.0, 0.44, 0])}
      {renderFloodlight('flood-2', -10.5, -2.4, [-4.0, 0.44, 0])}
    </group>
  );
};
