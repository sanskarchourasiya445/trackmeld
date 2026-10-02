'use client';

import React, { useState, useSyncExternalStore } from 'react';
import dynamic from 'next/dynamic';
import { Corridor, MaintenanceTask, TrainMovement } from '@/types/railway';
import { ScheduleResult } from '@/types/planning';
import { RailwayFallback2D } from './RailwayFallback2D';
import { Box, Layers } from 'lucide-react';
import { Button } from '@/components/ui/button';

const Canvas = dynamic(
  () => import('@react-three/fiber').then((mod) => mod.Canvas),
  { ssr: false }
);

const CorridorScene3D = dynamic(
  () => import('./CorridorScene3D').then((mod) => mod.CorridorScene3D),
  { ssr: false }
);

function getWebGLSnapshot(): boolean {
  if (typeof window === 'undefined') return true;
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'));
  } catch {
    return false;
  }
}

function getReducedMotionSnapshot(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function noopSubscribe() {
  return () => {};
}

function subscribeReducedMotion(callback: () => void) {
  if (typeof window === 'undefined') return () => {};
  const media = window.matchMedia('(prefers-reduced-motion: reduce)');
  media.addEventListener('change', callback);
  return () => media.removeEventListener('change', callback);
}

interface RailwayCanvasProps {
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

export const RailwayCanvas: React.FC<RailwayCanvasProps> = ({
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
  const webglSupported = useSyncExternalStore(noopSubscribe, getWebGLSnapshot, () => true);
  const prefersReducedMotion = useSyncExternalStore(subscribeReducedMotion, getReducedMotionSnapshot, () => false);

  const [use3DOverride, setUse3DOverride] = useState<boolean | null>(null);

  const use3D = use3DOverride !== null ? use3DOverride : (webglSupported && !prefersReducedMotion);

  return (
    <div className="relative h-full w-full bg-[#0A0A0A] border border-[#202024] rounded-md overflow-hidden select-none font-mono">
      {/* Visualizer Mode Toggle */}
      <div className="absolute top-2.5 right-2.5 z-20 flex items-center gap-1.5 bg-[#141418]/90 backdrop-blur-xs border border-[#29292F] p-1 rounded-md text-[10px]">
        <Button
          variant="ghost"
          size="xs"
          onClick={() => setUse3DOverride(true)}
          disabled={!webglSupported}
          className={`h-6 px-2 ${
            use3D ? 'bg-[#4C87E7] text-white' : 'text-[#A1A1AA] hover:text-white'
          }`}
        >
          <Box className="w-3 h-3 mr-1" />
          3D Corridor
        </Button>
        <Button
          variant="ghost"
          size="xs"
          onClick={() => setUse3DOverride(false)}
          className={`h-6 px-2 ${
            !use3D ? 'bg-[#4C87E7] text-white' : 'text-[#A1A1AA] hover:text-white'
          }`}
        >
          <Layers className="w-3 h-3 mr-1" />
          2D Schematic
        </Button>
      </div>

      {/* Render 3D Scene or 2D Schematic */}
      {use3D && webglSupported ? (
        <Canvas
          camera={{ position: [0, 24, 46], fov: 45 }}
          className="w-full h-full"
        >
          <CorridorScene3D
            corridor={corridor}
            tasks={tasks}
            trains={trains}
            scheduleResult={scheduleResult}
            selectedTaskId={selectedTaskId}
            selectedSectionCode={selectedSectionCode}
            selectedTrainId={selectedTrainId}
            onSelectTask={onSelectTask}
            onSelectSection={onSelectSection}
            onSelectTrain={onSelectTrain}
          />
        </Canvas>
      ) : (
        <RailwayFallback2D
          corridor={corridor}
          tasks={tasks}
          scheduleResult={scheduleResult}
          selectedTaskId={selectedTaskId}
          selectedSectionCode={selectedSectionCode}
          onSelectTask={onSelectTask}
          onSelectSection={onSelectSection}
        />
      )}
    </div>
  );
};
