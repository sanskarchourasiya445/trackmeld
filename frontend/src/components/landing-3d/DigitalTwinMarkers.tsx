'use client';

import React, { useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { TelemetryMarker } from './types';

interface DigitalTwinMarkersProps {
  markers: TelemetryMarker[];
  selectedMarkerId: string | null;
  onSelectMarker: (markerId: string) => void;
  showTelemetry: boolean;
}

interface BeaconProps {
  marker: TelemetryMarker;
  isSelected: boolean;
  onSelect: () => void;
}

const BeaconItem: React.FC<BeaconProps> = ({ marker, isSelected, onSelect }) => {
  const [hovered, setHovered] = useState(false);
  const beaconRef = useRef<THREE.Group>(null);
  const ringRef = useRef<THREE.Mesh>(null);

  const colorHex = React.useMemo(() => {
    switch (marker.tagColor) {
      case 'amber':
        return '#F59E0B';
      case 'rose':
        return '#F43F5E';
      case 'emerald':
        return '#10B981';
      case 'cyan':
        return '#06B6D4';
      case 'blue':
      default:
        return '#38BDF8';
    }
  }, [marker.tagColor]);

  useFrame((state, delta) => {
    if (beaconRef.current) {
      // Gentle floating bob and slow tactical rotation
      beaconRef.current.rotation.y += delta * (isSelected ? 2.0 : 0.8);
      beaconRef.current.position.y =
        marker.position[1] + Math.sin(state.clock.elapsedTime * 2.0 + marker.position[0]) * 0.08;
    }
    if (ringRef.current) {
      // Pulsing ground radar ring
      const scale = 1.0 + ((state.clock.elapsedTime * 1.5 + marker.position[0]) % 1.0) * 0.8;
      ringRef.current.scale.set(scale, scale, 1);
    }
  });

  return (
    <group position={[marker.position[0], 0, marker.position[2]]}>
      {/* Ground Anchor Rings */}
      <mesh
        position={[0, 0.05, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        <ringGeometry args={[0.25, 0.30, 24]} />
        <meshBasicMaterial color={colorHex} transparent opacity={0.7} />
      </mesh>
      <mesh
        ref={ringRef}
        position={[0, 0.04, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        <ringGeometry args={[0.35, 0.40, 24]} />
        <meshBasicMaterial color={colorHex} transparent opacity={0.35} />
      </mesh>

      {/* Vertical Hairline Telemetry Connector Post */}
      <mesh position={[0, marker.position[1] / 2, 0]}>
        <cylinderGeometry args={[0.015, 0.015, marker.position[1], 8]} />
        <meshBasicMaterial color={colorHex} transparent opacity={0.65} />
      </mesh>

      {/* Floating Holographic 3D Beacon Head */}
      <group
        ref={beaconRef}
        position={[0, marker.position[1], 0]}
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          document.body.style.cursor = 'pointer';
        }}
        onPointerOut={() => {
          setHovered(false);
          document.body.style.cursor = 'auto';
        }}
      >
        {/* Diamond Outer Cage */}
        <mesh scale={hovered || isSelected ? 1.3 : 1.0}>
          <octahedronGeometry args={[0.30, 0]} />
          <meshBasicMaterial color={colorHex} wireframe transparent opacity={0.8} />
        </mesh>

        {/* Solid Glowing Core */}
        <mesh scale={hovered || isSelected ? 1.2 : 1.0}>
          <sphereGeometry args={[0.12, 16, 16]} />
          <meshBasicMaterial color="#FFFFFF" />
        </mesh>

        {/* Orbiting Telemetry Reticle Ring */}
        <mesh rotation={[Math.PI / 3, 0, 0]} scale={hovered || isSelected ? 1.3 : 1.0}>
          <ringGeometry args={[0.42, 0.46, 20]} />
          <meshBasicMaterial color={colorHex} side={THREE.DoubleSide} transparent opacity={0.6} />
        </mesh>
      </group>
    </group>
  );
};

/**
 * 3D Anchored Digital-Twin Telemetry Beacons:
 * Interactive 3D holographic markers attached to physical railway track, train, and possession entities.
 * Fully compatible with React 19 concurrent renderer (zero Drei createRoot sub-tree locks).
 */
export const DigitalTwinMarkers: React.FC<DigitalTwinMarkersProps> = ({
  markers,
  selectedMarkerId,
  onSelectMarker,
  showTelemetry,
}) => {
  if (!showTelemetry) return null;

  return (
    <>
      {markers.map((marker) => (
        <BeaconItem
          key={marker.id}
          marker={marker}
          isSelected={selectedMarkerId === marker.id}
          onSelect={() => onSelectMarker(marker.id)}
        />
      ))}
    </>
  );
};
