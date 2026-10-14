'use client';

import React, { useRef, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { CameraMode } from './types';
import { useSimulationClock } from './SimulationContext';

import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';

interface CameraRigProps {
  cameraMode: CameraMode;
  targetMarkerPosition?: [number, number, number] | null;
}

/**
 * Dynamic Railway Simulation Camera Rig:
 * - Cinematic: Dynamic 3/4 trackside telephoto framing tracking train advance
 * - Cab: Forward driver cab perspective inside WAP-7 cabin looking down illuminated rails
 * - Drone: High-angle aerial survey tracking locomotive, rake, double tracks, and OHE catenary
 * - Orbit: 360-degree interactive inspection locked onto locomotive reference frame
 */
export const CameraRig: React.FC<CameraRigProps> = ({
  cameraMode,
  targetMarkerPosition,
}) => {
  const clockRef = useSimulationClock();
  const orbitControlsRef = useRef<OrbitControlsImpl | null>(null);
  const prevTrainX = useRef<number>(0);

  const targetCamPos = useRef(new THREE.Vector3(36.0, 4.2, 22.0));
  const targetLookAt = useRef(new THREE.Vector3(10.0, 2.2, -2.0));
  const currentLookTarget = useRef(new THREE.Vector3(10.0, 2.2, -2.0));

  // Reset initial camera alignment when switching to orbit mode
  useEffect(() => {
    if (cameraMode === 'orbit' && orbitControlsRef.current) {
      const trainX = clockRef.current ? clockRef.current.trainX : 0;
      orbitControlsRef.current.target.set(trainX + 8.0, 2.0, -2.0);
      if (orbitControlsRef.current.object) {
        orbitControlsRef.current.object.position.set(trainX + 24.0, 4.8, 16.0);
      }
      orbitControlsRef.current.update();
    }
  }, [cameraMode, clockRef]);

  useFrame(({ camera }) => {
    try {
      const globalSim = typeof window !== 'undefined' ? (window as unknown as { __trackmeld_sim_clock?: { trainX: number; distance: number } }).__trackmeld_sim_clock : undefined;
      const clock = globalSim ?? clockRef.current;
      const trainX = clock ? clock.trainX : 0;

      // -------------------------------------------------------------------------
      // 1. ORBIT CAMERA MODE (Continuous tracking along +X)
      // -------------------------------------------------------------------------
      if (cameraMode === 'orbit') {
        if (orbitControlsRef.current) {
          const deltaX = trainX - prevTrainX.current;
          if (Math.abs(deltaX) > 0.0001 && Math.abs(deltaX) < 10.0) {
            orbitControlsRef.current.target.x += deltaX;
            camera.position.x += deltaX;
            orbitControlsRef.current.update();
          }
        }
        prevTrainX.current = trainX;
        return;
      }

      // -------------------------------------------------------------------------
      // 2. TARGET COORDINATES BASED ON CAMERA MODE & TRAIN VELOCITY
      // -------------------------------------------------------------------------
      if (targetMarkerPosition) {
        const isPossession = targetMarkerPosition[2] > 0;
        if (isPossession) {
          const worksiteX = 95.0;
          targetCamPos.current.set(worksiteX + 12.0, 3.2, 8.5);
          targetLookAt.current.set(worksiteX, 1.8, 2.0);
        } else {
          targetCamPos.current.set(trainX + 19.5, 2.2, 5.8);
          targetLookAt.current.set(trainX + 7.5, 1.75, -2.0);
        }
      } else {
        switch (cameraMode) {
          case 'cab':
            targetCamPos.current.set(trainX + 12.8, 3.25, -2.0);
            targetLookAt.current.set(trainX + 120.0, 1.8, -2.0);
            break;

          case 'drone':
            targetCamPos.current.set(trainX + 20.0, 26.0, 22.0);
            targetLookAt.current.set(trainX + 6.0, 1.5, 0.0);
            break;

          case 'cinematic':
          default:
            targetCamPos.current.set(trainX + 19.5, 2.2, 5.8);
            targetLookAt.current.set(trainX + 7.5, 1.75, -2.0);
            break;
        }
      }

      if (cameraMode === 'cab') {
        camera.position.copy(targetCamPos.current);
        const vibration = Math.sin((clock?.distance ?? 0) * 8.0) * 0.003;
        camera.position.y += vibration;
        currentLookTarget.current.copy(targetLookAt.current);
      } else {
        camera.position.copy(targetCamPos.current);
        currentLookTarget.current.copy(targetLookAt.current);
      }

      camera.lookAt(currentLookTarget.current);
      prevTrainX.current = trainX;
      if (typeof window !== 'undefined') {
        const win = window as unknown as Record<string, unknown>;
        const fc = ((win.__camera_frame_count as number) || 0) + 1;
        win.__camera_frame_count = fc;
        win.__camera_debug = {
          fc,
          pos: [camera.position.x, camera.position.y, camera.position.z],
          look: [currentLookTarget.current.x, currentLookTarget.current.y, currentLookTarget.current.z],
          mode: cameraMode,
          trainX: trainX,
        };
      }
    } catch (err: unknown) {
      if (typeof window !== 'undefined') {
        const win = window as unknown as Record<string, unknown>;
        win.__camera_error = String(err instanceof Error && err.stack ? err.stack : err);
      }
    }
  });

  return (
    <>
      {cameraMode === 'orbit' && (
        <OrbitControls
          ref={orbitControlsRef}
          enableRotate={true}
          enablePan={true}
          enableZoom={true}
          minDistance={6}
          maxDistance={80}
          maxPolarAngle={Math.PI / 2.05} // Prevent camera going below ground plane
          target={[5.0, 2.2, -2.0]}
        />
      )}
    </>
  );
};

