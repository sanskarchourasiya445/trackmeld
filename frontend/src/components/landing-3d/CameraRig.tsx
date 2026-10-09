'use client';

import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { CameraMode } from './types';

interface CameraRigProps {
  cameraMode: CameraMode;
  targetMarkerPosition?: [number, number, number] | null;
}

/**
 * Cinematic Trackside Camera System:
 * - Frames high-speed train in right-center 45-55% visual area
 * - Slightly below window level (Y = 2.3m) with 3/4 quarter perspective
 * - Telephoto focal depth rendering realistic railway proportions
 * - Smoothly glides between viewpoints (Cinematic, Cab, Drone, Orbit)
 */
export const CameraRig: React.FC<CameraRigProps> = ({
  cameraMode,
  targetMarkerPosition,
}) => {
  const targetCamPos = useRef(new THREE.Vector3(24.0, 4.5, 14.5));
  const targetLookAt = useRef(new THREE.Vector3(11.0, 2.2, -1.8));

  useFrame(({ camera }, delta) => {
    if (cameraMode === 'orbit') return; // Handled by OrbitControls

    // Determine target camera and look-at positions
    if (targetMarkerPosition) {
      // Focus on selected marker with comfortable viewing offset
      targetCamPos.current.set(
        targetMarkerPosition[0] + 6,
        targetMarkerPosition[1] + 2,
        targetMarkerPosition[2] + 7
      );
      targetLookAt.current.set(
        targetMarkerPosition[0],
        targetMarkerPosition[1],
        targetMarkerPosition[2]
      );
    } else {
      switch (cameraMode) {
        case 'cab':
          // Driver cab perspective looking forward along UP line
          targetCamPos.current.set(16.5, 2.7, -2.0);
          targetLookAt.current.set(65, 2.4, -2.0);
          break;
        case 'drone':
          // High-angle aerial inspection of multi-track corridor & catenary
          targetCamPos.current.set(28, 20, 24);
          targetLookAt.current.set(12, 1.0, -2.0);
          break;
        case 'cinematic':
        default:
          // Cinematic trackside perspective: diagonal view framing train in right 35-40%
          targetCamPos.current.set(24.0, 4.5, 14.5);
          targetLookAt.current.set(11.0, 2.2, -1.8);
          break;
      }
    }

    // Smooth exponential damping (heavy physical camera feel)
    const damping = Math.min(delta * 2.8, 0.1);
    camera.position.lerp(targetCamPos.current, damping);

    const currentLookAt = new THREE.Vector3();
    camera.getWorldDirection(currentLookAt);
    const desiredDirection = new THREE.Vector3()
      .subVectors(targetLookAt.current, camera.position)
      .normalize();

    currentLookAt.lerp(desiredDirection, damping);
    camera.lookAt(
      camera.position.x + currentLookAt.x,
      camera.position.y + currentLookAt.y,
      camera.position.z + currentLookAt.z
    );
  });

  return (
    <>
      {cameraMode === 'orbit' && (
        <OrbitControls
          enableRotate={true}
          enablePan={true}
          enableZoom={true}
          minDistance={6}
          maxDistance={90}
          maxPolarAngle={Math.PI / 2.05} // Prevent camera going below ground plane
          target={[14, 2.0, -2.0]}
        />
      )}
    </>
  );
};
