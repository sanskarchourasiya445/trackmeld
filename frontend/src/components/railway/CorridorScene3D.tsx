'use client';

import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { OrbitControls, Text } from '@react-three/drei';
import * as THREE from 'three';
import { Corridor, MaintenanceTask, TrainMovement } from '@/types/railway';
import { ScheduleResult } from '@/types/planning';

interface CorridorScene3DProps {
  corridor: Corridor;
  tasks: MaintenanceTask[];
  trains: TrainMovement[];
  scheduleResult?: ScheduleResult | null;
  selectedTaskId?: string | null;
  selectedSectionCode?: string | null;
  selectedTrainId?: string | null;
  onSelectTask?: (taskId: string) => void;
  onSelectSection?: (sectionCode: string) => void;
  onSelectTrain?: (trainId: string) => void;
}

// Convert Corridor km (0 to 440) to 3D X space (-50 to +50)
const KM_TO_3D = (km: number, totalKm: number) => {
  return (km / totalKm) * 100 - 50;
};

export const CorridorScene3D: React.FC<CorridorScene3DProps> = ({
  corridor,
  tasks,
  trains,
  scheduleResult,
  selectedTaskId,
  selectedSectionCode,
  selectedTrainId,
  onSelectTask,
  onSelectSection,
  onSelectTrain,
}) => {
  const totalKm = corridor.total_length_km || 440;
  const stations = corridor.stations;

  const scheduledTaskIds = useMemo(
    () => new Set(scheduleResult?.scheduled_tasks.map((st) => st.task_id) || []),
    [scheduleResult]
  );

  // Controlled, gentle train rake movement
  const trainRakeRef = useRef<THREE.Group>(null);
  useFrame((_, delta) => {
    if (trainRakeRef.current) {
      trainRakeRef.current.position.x += delta * 3.5;
      if (trainRakeRef.current.position.x > 50) {
        trainRakeRef.current.position.x = -50;
      }
    }
  });

  return (
    <>
      <OrbitControls
        enableRotate={true}
        enablePan={true}
        enableZoom={true}
        minDistance={15}
        maxDistance={120}
        maxPolarAngle={Math.PI / 2.15}
      />

      <ambientLight intensity={0.45} />
      <directionalLight position={[20, 40, 20]} intensity={1.1} color="#F5F5F5" />
      <directionalLight position={[-20, 20, -10]} intensity={0.5} color="#4C87E7" />

      {/* Ground plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.5, 0]}>
        <planeGeometry args={[160, 40]} />
        <meshStandardMaterial color="#0A0A0A" roughness={0.9} />
      </mesh>

      {/* Ballast gravel bed */}
      <mesh position={[0, -0.2, 0]}>
        <boxGeometry args={[110, 0.4, 6]} />
        <meshStandardMaterial color="#141418" roughness={0.95} />
      </mesh>

      {/* Track UP (Z = -1.2) */}
      <mesh position={[0, 0.1, -1.8]}>
        <boxGeometry args={[110, 0.2, 0.15]} />
        <meshStandardMaterial color="#71717A" metalness={0.8} roughness={0.3} />
      </mesh>
      <mesh position={[0, 0.1, -0.6]}>
        <boxGeometry args={[110, 0.2, 0.15]} />
        <meshStandardMaterial color="#71717A" metalness={0.8} roughness={0.3} />
      </mesh>

      {/* Track DOWN (Z = +1.2) */}
      <mesh position={[0, 0.1, 0.6]}>
        <boxGeometry args={[110, 0.2, 0.15]} />
        <meshStandardMaterial color="#71717A" metalness={0.8} roughness={0.3} />
      </mesh>
      <mesh position={[0, 0.1, 1.8]}>
        <boxGeometry args={[110, 0.2, 0.15]} />
        <meshStandardMaterial color="#71717A" metalness={0.8} roughness={0.3} />
      </mesh>

      {/* Sleepers along corridor */}
      {Array.from({ length: 100 }).map((_, i) => {
        const x = -50 + i * 1.0;
        return (
          <mesh key={i} position={[x, -0.05, 0]}>
            <boxGeometry args={[0.3, 0.15, 4.4]} />
            <meshStandardMaterial color="#1E1E24" roughness={0.9} />
          </mesh>
        );
      })}

      {/* Physical Block Sections Markers & Active Highlighting */}
      {corridor.sections?.map((sec) => {
        const fromSt = stations.find((s) => s.code === sec.from_station_code);
        const toSt = stations.find((s) => s.code === sec.to_station_code);
        const x1 = KM_TO_3D(fromSt?.distance_km ?? 0, totalKm);
        const x2 = KM_TO_3D(toSt?.distance_km ?? 50, totalKm);
        const xCenter = (x1 + x2) / 2;
        const width = Math.max(2, Math.abs(x2 - x1));
        const isSectionSelected =
          selectedSectionCode &&
          (sec.code?.includes(selectedSectionCode) || sec.section_id?.includes(selectedSectionCode));

        return (
          <group
            key={sec.code || sec.section_id}
            position={[xCenter, -0.1, 0]}
            onClick={(e) => {
              e.stopPropagation();
              onSelectSection?.(sec.code || sec.section_id || '');
            }}
          >
            {/* Section Boundary Bed Indicator */}
            {isSectionSelected && (
              <mesh position={[0, 0.05, 0]}>
                <boxGeometry args={[width, 0.25, 6.2]} />
                <meshStandardMaterial
                  color="#3B82F6"
                  transparent
                  opacity={0.3}
                />
              </mesh>
            )}
          </group>
        );
      })}

      {/* Station Gantries and Signage */}
      {stations.map((st) => {
        const x = KM_TO_3D(st.distance_km, totalKm);
        return (
          <group
            key={st.code}
            position={[x, 0, 0]}
            onClick={(e) => {
              e.stopPropagation();
              onSelectSection?.(st.code);
            }}
          >
            {/* Gantry Arch */}
            <mesh position={[0, 2.5, -2.8]}>
              <cylinderGeometry args={[0.1, 0.1, 5, 8]} />
              <meshStandardMaterial color="#29292F" />
            </mesh>
            <mesh position={[0, 2.5, 2.8]}>
              <cylinderGeometry args={[0.1, 0.1, 5, 8]} />
              <meshStandardMaterial color="#29292F" />
            </mesh>
            <mesh position={[0, 5, 0]}>
              <boxGeometry args={[0.2, 0.2, 6]} />
              <meshStandardMaterial color="#29292F" />
            </mesh>

            {/* Station Code Label */}
            <Text
              position={[0, 5.8, 0]}
              fontSize={1.2}
              color="#F5F5F5"
              anchorX="center"
              anchorY="middle"
            >
              {st.code}
            </Text>
            <Text
              position={[0, 4.4, 0]}
              fontSize={0.6}
              color="#4C87E7"
              anchorX="center"
              anchorY="middle"
            >
              {`${st.distance_km} km`}
            </Text>
          </group>
        );
      })}

      {/* Possession Maintenance Zones */}
      {tasks.map((task) => {
        const section = corridor.sections?.find(
          (s) => s.code === task.section_code || s.section_id === task.section_id
        );
        const fromSt = stations.find((s) => s.code === section?.from_station_code);
        const toSt = stations.find((s) => s.code === section?.to_station_code);

        const x1 = KM_TO_3D(fromSt?.distance_km ?? 0, totalKm);
        const x2 = KM_TO_3D(toSt?.distance_km ?? 80, totalKm);
        const xCenter = (x1 + x2) / 2;
        const width = Math.max(4, Math.abs(x2 - x1));

        const isScheduled = scheduledTaskIds.has(task.task_id);
        const isSelected = selectedTaskId === task.task_id;
        const zPos = task.track_type === 'DOWN' ? 1.2 : -1.2;

        const zoneColor = isSelected
          ? '#3B82F6'
          : isScheduled
          ? '#35B779'
          : '#F06464';

        return (
          <group
            key={task.task_id}
            position={[xCenter, 0.8, zPos]}
            onClick={(e) => {
              e.stopPropagation();
              onSelectTask?.(task.task_id);
            }}
          >
            {/* Possession cage */}
            <mesh>
              <boxGeometry args={[width, 1.6, 2.2]} />
              <meshStandardMaterial
                color={zoneColor}
                transparent
                opacity={isSelected ? 0.65 : 0.22}
                wireframe={!isSelected}
              />
            </mesh>

            {/* Floating Task Indicator */}
            <Text
              position={[0, 1.6, 0]}
              fontSize={0.8}
              color={zoneColor}
              anchorX="center"
              anchorY="middle"
            >
              {task.task_code || task.task_id}
            </Text>
          </group>
        );
      })}

      {/* Animated Train Rake Model */}
      <group
        ref={trainRakeRef}
        position={[-30, 0.4, -1.2]}
        onClick={(e) => {
          e.stopPropagation();
          onSelectTrain?.(trains[0]?.train_id || trains[0]?.movement_id || 'TR-12004');
        }}
      >
        {/* Locomotive */}
        <mesh position={[0, 0.4, 0]}>
          <boxGeometry args={[4.5, 1.2, 1.4]} />
          <meshStandardMaterial
            color={selectedTrainId ? '#F4B740' : '#4C87E7'}
            metalness={0.6}
            roughness={0.3}
          />
        </mesh>
        <Text
          position={[0, 1.2, 0]}
          fontSize={0.5}
          color="#FFFFFF"
          anchorX="center"
          anchorY="middle"
        >
          {trains[0]?.train_number || '12004'}
        </Text>
        {/* Coaches */}
        <mesh position={[-5, 0.4, 0]}>
          <boxGeometry args={[4.8, 1.1, 1.3]} />
          <meshStandardMaterial color="#1E1E24" metalness={0.4} roughness={0.4} />
        </mesh>
        <mesh position={[-10.2, 0.4, 0]}>
          <boxGeometry args={[4.8, 1.1, 1.3]} />
          <meshStandardMaterial color="#1E1E24" metalness={0.4} roughness={0.4} />
        </mesh>
        <pointLight position={[2.5, 0.4, 0]} intensity={1.8} color="#FFFFFF" distance={8} />
      </group>
    </>
  );
};
