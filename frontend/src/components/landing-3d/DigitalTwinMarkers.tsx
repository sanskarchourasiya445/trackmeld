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

/**
 * Authentic Railway Trackside Balise / Digital-Twin Telemetry Sensor
 * Grounded at track level (Y ~ 0.15m) without giant sci-fi poles or floating wireframe diamonds.
 */
const BeaconItem: React.FC<BeaconProps> = ({ marker, isSelected, onSelect }) => {
  const [hovered, setHovered] = useState(false);
  const ringRef = useRef<THREE.Mesh>(null);
  const sensorRef = useRef<THREE.Group>(null);

  const colorHex = React.useMemo(() => {
    switch (marker.tagColor) {
      case 'amber':
        return '#F59E0B';
      case 'rose':
        return '#EF4444';
      case 'emerald':
        return '#10B981';
      case 'cyan':
        return '#00F0FF';
      case 'blue':
      default:
        return '#38BDF8';
    }
  }, [marker.tagColor]);

  useFrame((state, delta) => {
    if (sensorRef.current) {
      // Gentle pulse on sensor head
      const scale = 1.0 + (hovered || isSelected ? 0.15 : 0.05 * Math.sin(state.clock.elapsedTime * 3.0));
      sensorRef.current.scale.set(scale, scale, scale);
    }
    if (ringRef.current) {
      // Subtle ground ring ping
      const ringScale = 1.0 + ((state.clock.elapsedTime * 1.2 + marker.position[0]) % 1.0) * 0.4;
      ringRef.current.scale.set(ringScale, ringScale, 1);
    }
  });

  return (
    <group position={[marker.position[0], 0.12, marker.position[2]]}>
      {/* 1. Trackside Electronic Balise Housing (Yellow/Graphite durable enclosure) */}
      <mesh
        position={[0, 0.04, 0]}
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
        castShadow
      >
        <boxGeometry args={[0.42, 0.08, 0.28]} />
        <meshStandardMaterial
          color={isSelected ? '#1E293B' : '#0F172A'}
          metalness={0.7}
          roughness={0.3}
        />
      </mesh>

      {/* 2. Embedded Status Indicator LED */}
      <group ref={sensorRef} position={[0, 0.10, 0]}>
        <mesh>
          <cylinderGeometry args={[0.04, 0.04, 0.03, 16]} />
          <meshBasicMaterial color={colorHex} />
        </mesh>
        {/* Subtle Halo Rim */}
        <mesh position={[0, 0.01, 0]}>
          <ringGeometry args={[0.045, 0.07, 16]} />
          <meshBasicMaterial color={colorHex} transparent opacity={0.6} side={THREE.DoubleSide} />
        </mesh>
      </group>

      {/* 3. Concentric Ground Inspection Perimeter Rings */}
      <mesh
        position={[0, 0.02, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        <ringGeometry args={[0.22, 0.26, 24]} />
        <meshBasicMaterial color={colorHex} transparent opacity={isSelected ? 0.6 : 0.3} />
      </mesh>
      <mesh
        ref={ringRef}
        position={[0, 0.01, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        <ringGeometry args={[0.28, 0.32, 24]} />
        <meshBasicMaterial color={colorHex} transparent opacity={isSelected ? 0.3 : 0.12} />
      </mesh>
    </group>
  );
};

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
