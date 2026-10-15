'use client';

import React, { useState, useEffect, useMemo, useSyncExternalStore } from 'react';
import dynamic from 'next/dynamic';

const emptySubscribe = () => () => {};
import { CameraMode, LightingPreset, TelemetryMarker } from '@/components/landing-3d/types';
import { CameraRig } from '@/components/landing-3d/CameraRig';
import { RailwayScene } from '@/components/landing-3d/RailwayScene';
import { DigitalTwinMarkers } from '@/components/landing-3d/DigitalTwinMarkers';
import { FallbackRailwayCanvas } from '@/components/landing-3d/FallbackRailwayCanvas';
import { SimulationProvider } from '@/components/landing-3d/SimulationContext';
import { MaintenanceTask } from '@/types/railway';
import {
  X,
  Maximize2,
  Minimize2,
  Box,
  Radio,
  Video,
  Eye,
  Layers,
  Compass,
  Sun,
  Moon,
  Cloud,
  Play,
  Pause,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

const Canvas = dynamic(
  () => import('@react-three/fiber').then((mod) => mod.Canvas),
  { ssr: false }
);

interface DigitalTwinInspectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  sectionCode?: string | null;
  sectionName?: string | null;
  kmRange?: string | null;
  workOrderTitle?: string | null;
  task?: MaintenanceTask | null;
}

export const DigitalTwinInspectionModal: React.FC<DigitalTwinInspectionModalProps> = ({
  isOpen,
  onClose,
  sectionCode = 'SEC-12',
  sectionName = 'Tundla – Etawah Mainline',
  kmRange = 'km 209.0 – 301.0',
  workOrderTitle = 'WO-1847 Plain Track CSM Tamping',
  task,
}) => {
  const [cameraMode, setCameraMode] = useState<CameraMode>('cinematic');
  const [lighting, setLighting] = useState<LightingPreset>('dawn');
  const [showTelemetry, setShowTelemetry] = useState(true);
  const [trainSpeedKmh, setTrainSpeedKmh] = useState(120);
  const [isPlaying, setIsPlaying] = useState(true);
  const [selectedMarkerId, setSelectedMarkerId] = useState<string | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<string | null>('train-express07');
  const isMounted = useSyncExternalStore(emptySubscribe, () => true, () => false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [hasWebGLError, setHasWebGLError] = useState(false);
  const [showExpandedDetails, setShowExpandedDetails] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // View descriptions matching reference comp
  const viewMeta: Record<CameraMode, { title: string; desc: string }> = {
    cinematic: {
      title: 'CINEMATIC VIEW',
      desc: '3/4 Trackside corridor perspective',
    },
    cab: {
      title: 'DRIVER CAB VIEW',
      desc: 'Forward driver cab perspective along UP MAIN line',
    },
    drone: {
      title: 'AERIAL DRONE SURVEY',
      desc: 'High-angle survey of multi-track corridor & catenary',
    },
    orbit: {
      title: 'ORBIT INSPECTION',
      desc: 'Interactive 3D orbit (drag to rotate, scroll to zoom)',
    },
  };

  const activeMeta = viewMeta[cameraMode] || viewMeta.cinematic;

  // Dynamic telemetry markers driven by current task and corridor data
  const inspectionMarkers = useMemo<TelemetryMarker[]>(() => {
    const taskCode = task?.work_order_id || task?.task_code || 'WO-1847';
    const taskTitle = task?.title || workOrderTitle || 'Plain Track CSM Tamping';
    const dept = task?.department || 'Civil Engineering (P-Way)';
    const machine = task?.machinery_required?.[0] || 'CSM-01 Continuous Action Tamper';
    const windowStr =
      task?.window_start && task?.window_end
        ? `${task.window_start.slice(11, 16)} – ${task.window_end.slice(11, 16)} UTC`
        : '14:20 – 16:10 UTC';

    return [
      {
        id: 'marker-train',
        title: 'Vande Bharat Express (Train 22436)',
        subtitle: 'Streamlined Broad-Gauge Electric Trainset',
        tag: `${trainSpeedKmh} km/h · UP MAIN`,
        tagColor: 'blue',
        position: [12.0, 2.8, -2.0],
        entityType: 'train',
        details: [
          { label: 'Train Number', value: '22436 (Vande Bharat)' },
          { label: 'Running Line', value: 'UP MAIN (km 242.4)' },
          { label: 'Track Gauge', value: '1676 mm Broad Gauge' },
          { label: 'Axle Load / Max Speed', value: '19.5 T / 130 km/h' },
          { label: 'Traction Power', value: '25 kV AC 50 Hz' },
          { label: 'Block Signal Ahead', value: 'SIGNAL S-142 (GREEN · CLEAR)' },
        ],
      },
      {
        id: 'marker-possession',
        title: `${taskCode} Possession Worksite`,
        subtitle: taskTitle,
        tag: 'POSSESSION BLOCKED · PTW ACTIVE',
        tagColor: 'amber',
        position: [25.0, 3.2, 2.0],
        entityType: 'possession',
        details: [
          { label: 'Requisition Code', value: taskCode },
          { label: 'Department', value: dept },
          { label: 'Track Possession', value: `DOWN MAIN (${kmRange})` },
          { label: 'Machinery Deployed', value: machine },
          { label: 'Permitted Window', value: windowStr },
          { label: 'Adjacent Line Rule', value: task?.adjacent_track_impact || 'CAUTION ORDER (45 km/h)' },
          { label: 'Electrical Isolation', value: task?.requires_power_block ? 'DE-ENERGIZED & EARTHED' : '25kV ACTIVE (MAST CLEAR)' },
          { label: 'Safety Permit', value: 'PTW GR-1678 AUTHORIZED' },
        ],
      },
    ];
  }, [task, workOrderTitle, kmRange, trainSpeedKmh]);

  if (!isOpen) return null;

  const selectedMarker = inspectionMarkers.find((m) => m.id === selectedMarkerId) || null;

  return (
    <div
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      className={`fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md animate-in fade-in duration-200 ${
        isExpanded ? 'p-0' : 'p-2 sm:p-4'
      }`}
      role="dialog"
      aria-modal="true"
      aria-label="Digital Twin Inspection Modal"
    >
      <div
        className={`relative bg-[#060A13] border border-[#1E2D4A] shadow-2xl flex flex-col overflow-hidden transition-all duration-300 ${
          isExpanded ? 'w-screen h-screen rounded-none' : 'w-full max-w-6xl h-[88vh] rounded-xl'
        }`}
      >
        {/* Top Minimal Window Bar with Title & Modal Actions */}
        <div className="h-10 bg-[#070D18] border-b border-[#1E2D4A] px-4 flex items-center justify-between z-30 shrink-0">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-xs font-bold text-white font-mono tracking-wider">
              <Box className="w-3.5 h-3.5 text-[#38BDF8]" />
              <span>DIGITAL TWIN INSPECTION</span>
            </span>
            <div className="h-3.5 w-[1px] bg-[#1E2D4A]" />
            <span className="text-xs font-semibold text-[#93C5FD]">
              {sectionCode} • {sectionName}
            </span>
            <span className="hidden sm:inline text-[11px] font-mono text-[#64748B]">
              ({kmRange})
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden md:inline-flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              PHYSICAL UIC-60 / 25kV OHE MODEL
            </span>
            <button
              onClick={() => setIsExpanded((prev) => !prev)}
              className="p-1 text-[#94A3B8] hover:text-white rounded hover:bg-[#141F36] transition-colors cursor-pointer"
              title={isExpanded ? 'Collapse' : 'Expand full screen'}
            >
              {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>
            <button
              onClick={onClose}
              className="p-1 text-[#94A3B8] hover:text-white rounded hover:bg-rose-500/20 hover:text-rose-400 transition-colors cursor-pointer"
              title="Close inspection"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* 3D Canvas Scene Area with Overlaid HUD Controls */}
        <div className="relative flex-1 w-full h-full overflow-hidden bg-[#04070D]">
          {isMounted && !hasWebGLError ? (
            <Canvas
              shadows
              dpr={[1, 1.5]}
              camera={{ position: [19.5, 2.1, 7.2], fov: 38, near: 0.1, far: 500 }}
              gl={{
                antialias: true,
                alpha: false,
                preserveDrawingBuffer: true,
                powerPreference: 'high-performance',
              }}
              onCreated={({ gl }) => {
                gl.setClearColor(lighting === 'night' ? '#050A15' : lighting === 'overcast' ? '#0E1726' : '#0A1424');
              }}
              onError={() => setHasWebGLError(true)}
              className="w-full h-full"
            >
              <SimulationProvider speedKmh={trainSpeedKmh} isPlaying={isPlaying}>
                <CameraRig
                  cameraMode={cameraMode}
                  targetMarkerPosition={selectedMarker?.position ?? null}
                />
                <RailwayScene
                  cameraMode={cameraMode}
                  lighting={lighting}
                  trainSpeedKmh={trainSpeedKmh}
                  isPlaying={isPlaying}
                  onSelectTrain={() => {
                    setSelectedEntity('train-express07');
                    setSelectedMarkerId('marker-train');
                  }}
                  onSelectPossession={() => {
                    setSelectedEntity('marker-possession');
                    setSelectedMarkerId('marker-possession');
                  }}
                  selectedEntity={selectedEntity}
                  task={task}
                  workOrderTitle={workOrderTitle}
                />
                <DigitalTwinMarkers
                  markers={inspectionMarkers}
                  selectedMarkerId={selectedMarkerId}
                  onSelectMarker={(id) => {
                    setSelectedMarkerId(id);
                    setSelectedEntity(id);
                  }}
                  showTelemetry={showTelemetry}
                />
              </SimulationProvider>
            </Canvas>
          ) : (
            <FallbackRailwayCanvas />
          )}

          {/* ================================================================ */}
          {/* FLOATING HUD CONTROLS OVERLAY (MATCHING USER REFERENCE COMP)     */}
          {/* ================================================================ */}
          <div className="absolute top-3 inset-x-3 sm:inset-x-5 z-20 flex flex-wrap items-start justify-between gap-3 pointer-events-none">
            {/* Top Left: Title, Subtitle, Atmosphere, Anchors, Playback & Speed */}
            <div className="flex flex-col gap-2 pointer-events-auto">
              {/* Badge row */}
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-sky-950/70 border border-sky-500/40 text-[10px] font-mono font-bold text-[#38BDF8] uppercase tracking-wider backdrop-blur-md shadow-md">
                  <Radio className="w-2.5 h-2.5 text-[#38BDF8] animate-pulse" />
                  DIGITAL TWIN VIEW
                </span>
                <span className="text-[10px] font-mono text-[#64748B] font-bold">
                  DIGITAL TWIN HUD
                </span>
              </div>

              {/* View title and description */}
              <div>
                <span className="text-xs sm:text-sm font-bold text-white tracking-tight">
                  {activeMeta.title}
                </span>
                <span className="text-[11px] font-mono text-[#94A3B8]">
                  {' '}— {activeMeta.desc}
                </span>
              </div>

              {/* Controls bar: Atmosphere, Anchors, Play/Pause, Velocity */}
              <div className="flex flex-wrap items-center gap-2.5 mt-0.5">
                {/* Atmosphere Preset Selector */}
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-mono uppercase text-[#64748B]">
                    ATMOSPHERE
                  </span>
                  <div className="inline-flex items-center p-0.5 rounded-lg bg-[#070D18]/90 border border-[#1E293B] backdrop-blur-md shadow-md">
                    {[
                      { id: 'dawn' as LightingPreset, label: 'Dawn', icon: Sun },
                      { id: 'night' as LightingPreset, label: 'Night', icon: Moon },
                      { id: 'overcast' as LightingPreset, label: 'Overcast', icon: Cloud },
                    ].map((btn) => {
                      const Icon = btn.icon;
                      const isActive = lighting === btn.id;
                      return (
                        <button
                          key={btn.id}
                          onClick={() => setLighting(btn.id)}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-mono transition-all cursor-pointer ${
                            isActive
                              ? 'bg-[#1E293B] text-[#38BDF8] border border-[#38BDF8]/40 shadow-sm'
                              : 'text-[#64748B] hover:text-[#94A3B8]'
                          }`}
                          title={`Lighting Preset: ${btn.label}`}
                        >
                          <Icon className="w-3 h-3" />
                          <span>{btn.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Anchors Toggle */}
                <button
                  onClick={() => setShowTelemetry((prev) => !prev)}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-mono transition-all border backdrop-blur-md cursor-pointer ${
                    showTelemetry
                      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                      : 'bg-[#070D18]/90 text-[#64748B] border-[#1E293B]'
                  }`}
                  title="Toggle 3D telemetry anchors"
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      showTelemetry ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'
                    }`}
                  />
                  <span>{showTelemetry ? 'Anchors: ON' : 'Anchors: OFF'}</span>
                </button>

                {/* Play/Pause Button */}
                <button
                  onClick={() => setIsPlaying((p) => !p)}
                  className="w-7 h-7 rounded-lg bg-[#070D18]/90 border border-[#1E293B] text-[#F1F5F9] hover:bg-[#1E293B] transition-colors flex items-center justify-center cursor-pointer shadow-md backdrop-blur-md"
                  title={isPlaying ? 'Pause simulation' : 'Resume simulation'}
                >
                  {isPlaying ? (
                    <Pause className="w-3.5 h-3.5" />
                  ) : (
                    <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
                  )}
                </button>

                {/* Speed Slider */}
                <div className="flex items-center gap-2 px-2 py-1 rounded-lg bg-[#070D18]/90 border border-[#1E293B] backdrop-blur-md shadow-md">
                  <input
                    type="range"
                    min="0"
                    max="160"
                    step="5"
                    value={trainSpeedKmh}
                    onChange={(e) => setTrainSpeedKmh(Number(e.target.value))}
                    className="w-20 accent-[#2563EB] h-1.5 bg-[#0F172A] rounded cursor-pointer"
                    title={`Train Velocity: ${trainSpeedKmh} km/h`}
                  />
                  <span className="text-[11px] font-mono font-bold text-[#F1F5F9] min-w-[50px] text-right">
                    {isPlaying ? `${trainSpeedKmh} km/h` : 'PAUSED'}
                  </span>
                </div>
              </div>
            </div>

            {/* Top Right: Camera View Selection */}
            <div className="flex items-center gap-1.5 pointer-events-auto">
              <span className="text-[10px] font-mono uppercase text-[#64748B] hidden sm:inline">
                CAMERA VIEW
              </span>
              <div className="inline-flex items-center p-1 rounded-lg bg-[#070D18]/90 border border-[#1E293B] shadow-lg backdrop-blur-md gap-1">
                {[
                  { id: 'cinematic' as CameraMode, label: 'Cinematic', icon: Video },
                  { id: 'cab' as CameraMode, label: 'Cab', icon: Eye },
                  { id: 'drone' as CameraMode, label: 'Drone', icon: Layers },
                  { id: 'orbit' as CameraMode, label: 'Orbit', icon: Compass },
                ].map((btn) => {
                  const Icon = btn.icon;
                  const isActive = cameraMode === btn.id;
                  return (
                    <button
                      key={btn.id}
                      onClick={() => setCameraMode(btn.id)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-mono font-medium transition-all cursor-pointer ${
                        isActive
                          ? 'bg-[#2563EB] text-white shadow-md shadow-blue-600/30 ring-1 ring-blue-400/40'
                          : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#1E293B]/70'
                      }`}
                      title={`Switch to ${btn.label} camera perspective`}
                    >
                      <Icon className="w-3.5 h-3.5 shrink-0" />
                      <span>{btn.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* ================================================================ */}
          {/* BOTTOM-LEFT: CORRIDOR SECTION TELEMETRY (MATCHING COMP)          */}
          {/* ================================================================ */}
          <div className="absolute bottom-4 left-4 z-20 bg-[#070D18]/95 backdrop-blur-md border border-[#1E2D4A] rounded-xl p-3.5 max-w-xs sm:max-w-sm text-xs font-mono shadow-2xl pointer-events-auto">
            <div className="flex items-center justify-between pb-2 border-b border-[#1E2D4A]">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#38BDF8] animate-pulse" />
                <span className="text-xs font-bold text-white tracking-wide">Corridor Section Telemetry</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[9.5px] font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
                  ACTIVE
                </span>
                <button
                  onClick={() => setShowExpandedDetails((prev) => !prev)}
                  className="text-[#64748B] hover:text-white p-0.5 rounded transition-colors cursor-pointer"
                  title="Toggle full requisition telemetry"
                >
                  {showExpandedDetails ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            <div className="mt-2.5 space-y-1.5 text-[11px]">
              <div className="flex items-center justify-between">
                <span className="text-[#64748B]">Section:</span>
                <span className="text-white font-medium">{sectionCode || 'SEC-12'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#64748B]">Gauge / Rails:</span>
                <span className="text-[#E2E8F0] font-medium">1676mm Broad Gauge &nbsp;·&nbsp; UIC 60</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#64748B]">Traction OHE:</span>
                <span className="text-amber-400 font-bold">25 kV AC 50 Hz</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#64748B]">Worksite:</span>
                <span
                  className="text-[#38BDF8] truncate max-w-[190px] sm:max-w-[210px]"
                  title={task?.title || workOrderTitle || 'Switch Expansion Joint Greasing'}
                >
                  {task?.title || workOrderTitle || 'Switch Expansion Joint Greasing...'}
                </span>
              </div>
            </div>

            {/* Expandable Requisition & Safety Details */}
            {showExpandedDetails && (
              <div className="mt-3 pt-2 border-t border-[#1E2D4A] space-y-1.5 text-[10px] text-[#CBD5E1] animate-in fade-in duration-200">
                <div className="flex justify-between">
                  <span className="text-[#64748B]">Requisition ID:</span>
                  <span className="text-amber-300 font-bold">{task?.work_order_id || task?.task_code || 'WO-1847'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#64748B]">Department:</span>
                  <span>{task?.department || 'Civil Engineering (P-Way)'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#64748B]">Possession Track:</span>
                  <span className="text-amber-400 font-bold">DOWN MAIN · {kmRange}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#64748B]">Track Machine:</span>
                  <span className="text-[#38BDF8]">{task?.machinery_required?.[0] || 'CSM-01 Continuous Action Tamper'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#64748B]">Safety Permit:</span>
                  <span className="text-emerald-400 flex items-center gap-1">
                    <ShieldCheck className="w-3 h-3" /> PTW GR-1678 ACTIVE
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#64748B]">Adjacent UP Line:</span>
                  <span className="text-sky-300">CAUTION ORDER (45 km/h)</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
