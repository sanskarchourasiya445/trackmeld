'use client';

import React, { useState, useSyncExternalStore } from 'react';
import dynamic from 'next/dynamic';
import { Corridor, MaintenanceTask, TrainMovement } from '@/types/railway';
import { ScheduleResult } from '@/types/planning';
import { RailwayFallback2D } from './RailwayFallback2D';
import {
  Plus,
  Minus,
  Crosshair,
  Layers,
  Maximize2,
  ChevronDown,
  Navigation,
} from 'lucide-react';

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
  const [isLegendOpen, setIsLegendOpen] = useState(true);

  const use3D = use3DOverride !== null ? use3DOverride : (webglSupported && !prefersReducedMotion);

  return (
    <div className="relative h-full w-full bg-[#070B12] border border-[#1E2D4A] rounded-lg overflow-hidden select-none font-sans flex flex-col">
      {/* 1. Railway View Top Toolbar (Direct match to reference comp) */}
      <div className="h-10 bg-[#0F172A]/90 backdrop-blur-xs border-b border-[#1E2D4A] px-3.5 flex items-center justify-between z-20 shrink-0">
        <div>
          <span className="font-semibold text-xs text-[#F8FAFC]">Railway View</span>
          <span className="text-[11px] text-[#64748B] ml-2 font-mono">
            {corridor.name || 'Northern Corridor'} • {corridor.total_length_km || 440} km
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* 3D / 2D Pill Toggle */}
          <div className="flex items-center bg-[#0A0E17] border border-[#1E2D4A] rounded p-0.5 text-[10px] font-mono">
            <button
              onClick={() => setUse3DOverride(true)}
              disabled={!webglSupported}
              className={`px-2 py-0.5 rounded transition-colors ${
                use3D ? 'bg-[#2563EB] text-white font-bold' : 'text-[#64748B] hover:text-white'
              }`}
            >
              3D
            </button>
            <button
              onClick={() => setUse3DOverride(false)}
              className={`px-2 py-0.5 rounded transition-colors ${
                !use3D ? 'bg-[#2563EB] text-white font-bold' : 'text-[#64748B] hover:text-white'
              }`}
            >
              2D
            </button>
          </div>

          {/* Layers Dropdown */}
          <button
            className="flex items-center gap-1.5 bg-[#0A0E17] hover:bg-[#141F36] border border-[#1E2D4A] rounded px-2.5 py-1 text-[11px] text-[#CBD5E1] transition-colors"
          >
            <Layers className="w-3 h-3 text-[#3B82F6]" />
            <span>Layers</span>
            <ChevronDown className="w-3 h-3 text-[#64748B]" />
          </button>

          {/* Fullscreen Button */}
          <button
            onClick={() => {
              const el = document.getElementById('railway-canvas-container');
              if (el) {
                if (!document.fullscreenElement) {
                  el.requestFullscreen?.();
                } else {
                  document.exitFullscreen?.();
                }
              }
            }}
            className="p-1.5 text-[#64748B] hover:text-white bg-[#0A0E17] hover:bg-[#141F36] border border-[#1E2D4A] rounded transition-colors"
            title="Toggle Fullscreen"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 2. Main Map / Canvas Area */}
      <div id="railway-canvas-container" className="relative flex-1 w-full overflow-hidden">
        {/* Left Map Navigation Controls Overlay */}
        <div className="absolute top-3 left-3 z-20 flex flex-col gap-1 bg-[#0F172A]/90 backdrop-blur-xs border border-[#1E2D4A] rounded-md p-1 shadow-lg">
          <button
            className="p-1.5 text-[#94A3B8] hover:text-white hover:bg-[#141F36] rounded transition-colors"
            title="Zoom In"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
          <button
            className="p-1.5 text-[#94A3B8] hover:text-white hover:bg-[#141F36] rounded transition-colors"
            title="Zoom Out"
          >
            <Minus className="w-3.5 h-3.5" />
          </button>
          <div className="h-[1px] bg-[#1E2D4A] my-0.5" />
          <button
            className="p-1.5 text-[#94A3B8] hover:text-white hover:bg-[#141F36] rounded transition-colors"
            title="Recenter Corridor View"
          >
            <Crosshair className="w-3.5 h-3.5" />
          </button>
          <button
            className="p-1.5 text-[#94A3B8] hover:text-white hover:bg-[#141F36] rounded transition-colors"
            title="Toggle Map Layers"
          >
            <Layers className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* 3D Scene or 2D Schematic */}
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

        {/* Bottom-Left Map Legend (Matching Reference Comp) */}
        <div className="absolute bottom-3 left-3 z-20 bg-[#0F172A]/90 backdrop-blur-md border border-[#1E2D4A] rounded-md px-3 py-1.5 shadow-lg text-[10px] font-sans">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 text-[#CBD5E1]">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span>Scheduled Possession</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                <span>Unscheduled / Conflict</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-[#64748B]" />
                <span>Block Section</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full border border-[#94A3B8]" />
                <span>Station</span>
              </span>
            </div>

            <button
              onClick={() => setIsLegendOpen((prev) => !prev)}
              className="text-[#64748B] hover:text-[#CBD5E1] text-[9.5px] ml-1"
            >
              {isLegendOpen ? 'Hide' : 'Show'}
            </button>
          </div>
        </div>

        {/* Bottom-Right Scale Bar & Compass (Matching Reference Comp) */}
        <div className="absolute bottom-3 right-3 z-20 flex items-center gap-3 bg-[#0F172A]/85 backdrop-blur-md border border-[#1E2D4A] rounded-md px-2.5 py-1 text-[9.5px] font-mono text-[#64748B]">
          <div className="flex items-center gap-1.5">
            <span>0</span>
            <div className="w-8 h-[2px] bg-[#94A3B8]" />
            <span>10</span>
            <div className="w-8 h-[2px] bg-[#94A3B8]" />
            <span>20</span>
            <div className="w-8 h-[2px] bg-[#94A3B8]" />
            <span>30 km</span>
          </div>
          <div className="w-[1px] h-3 bg-[#1E2D4A]" />
          <div className="flex items-center gap-1 text-[#CBD5E1]">
            <Navigation className="w-3 h-3 text-[#3B82F6] rotate-45" />
            <span className="font-bold">N</span>
          </div>
        </div>
      </div>
    </div>
  );
};
