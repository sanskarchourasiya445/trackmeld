'use client';

import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { CameraMode, LightingPreset, TelemetryMarker } from '@/components/landing-3d/types';
import { CameraRig } from '@/components/landing-3d/CameraRig';
import { RailwayScene } from '@/components/landing-3d/RailwayScene';
import { DigitalTwinMarkers } from '@/components/landing-3d/DigitalTwinMarkers';
import { DigitalTwinHUD } from '@/components/landing-3d/DigitalTwinHUD';
import { FallbackRailwayCanvas } from '@/components/landing-3d/FallbackRailwayCanvas';
import {
  X,
  Maximize2,
  Minimize2,
  Box,
  Layers,
  Radio,
  ShieldCheck,
  Zap,
  Info,
} from 'lucide-react';

const Canvas = dynamic(
  () => import('@react-three/fiber').then((mod) => mod.Canvas),
  { ssr: false }
);

const INSPECTION_MARKERS: TelemetryMarker[] = [
  {
    id: 'marker-train',
    title: 'Swarna Shatabdi Express',
    subtitle: 'WAP-7 / 22-Coach Rake',
    tag: '120 km/h · ON TIME',
    tagColor: 'blue',
    position: [12.0, 2.8, -2.0],
    entityType: 'train',
    details: [
      { label: 'Train Number', value: '12004' },
      { label: 'Axle Load', value: '20.5 T' },
      { label: 'Track Gauge', value: '1676 mm' },
    ],
  },
  {
    id: 'marker-possession',
    title: 'Planned Possession Zone S-04',
    subtitle: 'Track Tamping Requisition',
    tag: 'POSSESSION BLOCKED',
    tagColor: 'amber',
    position: [65.0, 3.2, 2.0],
    entityType: 'possession',
    details: [
      { label: 'Work Order', value: 'WO-1847' },
      { label: 'Window', value: '14:20 – 16:10 UTC' },
      { label: 'Track Machine', value: 'CSM 01' },
    ],
  },
];

interface DigitalTwinInspectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  sectionCode?: string | null;
  sectionName?: string | null;
  kmRange?: string | null;
  workOrderTitle?: string | null;
}

export const DigitalTwinInspectionModal: React.FC<DigitalTwinInspectionModalProps> = ({
  isOpen,
  onClose,
  sectionCode = 'SEC-12',
  sectionName = 'Tundla – Etawah Mainline',
  kmRange = 'km 209.0 – 301.0',
  workOrderTitle = 'WO-1847 Plain Track CSM Tamping',
}) => {
  const [cameraMode, setCameraMode] = useState<CameraMode>('cinematic');
  const [lighting, setLighting] = useState<LightingPreset>('dawn');
  const [showTelemetry, setShowTelemetry] = useState(true);
  const [trainSpeedKmh, setTrainSpeedKmh] = useState(120);
  const [isPlaying, setIsPlaying] = useState(true);
  const [selectedMarkerId, setSelectedMarkerId] = useState<string | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<string | null>('train-express07');
  const [isMounted, setIsMounted] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isOpen) return null;

  const selectedMarker = INSPECTION_MARKERS.find((m) => m.id === selectedMarkerId) || null;

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md animate-in fade-in duration-200 ${isExpanded ? 'p-0' : 'p-2 sm:p-4'}`}>
      <div
        className={`relative bg-[#060A13] border border-[#1E2D4A] shadow-2xl flex flex-col overflow-hidden transition-all duration-300 ${
          isExpanded ? 'w-screen h-screen rounded-none' : 'w-full max-w-6xl h-[88vh] rounded-xl'
        }`}
      >
        {/* Top Header Bar */}
        <div className="h-12 bg-[#0B101C] border-b border-[#1E2D4A] px-4 flex items-center justify-between z-30 shrink-0">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-xs font-bold text-white font-mono tracking-wider">
              <Box className="w-4 h-4 text-[#38BDF8]" />
              <span>DIGITAL TWIN INSPECTION</span>
            </span>
            <div className="h-4 w-[1px] bg-[#1E2D4A]" />
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
              className="p-1.5 text-[#94A3B8] hover:text-white rounded hover:bg-[#141F36] transition-colors"
              title={isExpanded ? 'Collapse' : 'Expand full screen'}
            >
              {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-[#94A3B8] hover:text-white rounded hover:bg-rose-500/20 hover:text-rose-400 transition-colors"
              title="Close inspection"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* 3D Canvas Scene Area */}
        <div className="relative flex-1 w-full h-full overflow-hidden bg-[#04070D]">
          {isMounted ? (
            <Canvas
              shadows
              dpr={[1, 1.5]}
              gl={{
                antialias: true,
                powerPreference: 'high-performance',
                stencil: false,
                depth: true,
              }}
              camera={{ position: [-14, 5.2, 16], fov: 42, near: 0.1, far: 250 }}
              className="w-full h-full"
            >
              <CameraRig cameraMode={cameraMode} />
              <RailwayScene
                cameraMode={cameraMode}
                lighting={lighting}
                trainSpeedKmh={trainSpeedKmh}
                isPlaying={isPlaying}
                onSelectTrain={() => setSelectedEntity('train-express07')}
                onSelectPossession={(id) => setSelectedEntity(id)}
                selectedEntity={selectedEntity}
              />
              <DigitalTwinMarkers
                markers={INSPECTION_MARKERS}
                selectedMarkerId={selectedMarkerId}
                onSelectMarker={(id) => setSelectedMarkerId(id)}
                showTelemetry={showTelemetry}
              />
            </Canvas>
          ) : (
            <FallbackRailwayCanvas />
          )}

          {/* Interactive Floating HUD Controls Dock */}
          <div className="absolute top-3 right-3 z-30 pointer-events-auto">
            <DigitalTwinHUD
              cameraMode={cameraMode}
              onSetCameraMode={(mode) => setCameraMode(mode)}
              lighting={lighting}
              onSetLighting={(preset) => setLighting(preset)}
              trainSpeedKmh={trainSpeedKmh}
              onSetTrainSpeedKmh={(speed) => setTrainSpeedKmh(speed)}
              isPlaying={isPlaying}
              onTogglePlay={() => setIsPlaying((p) => !p)}
              showTelemetry={showTelemetry}
              onToggleTelemetry={() => setShowTelemetry((t) => !t)}
              selectedMarker={selectedMarker}
              onCloseSelectedMarker={() => setSelectedMarkerId(null)}
            />
          </div>

          {/* Bottom Left Contextual Metadata Callout */}
          <div className="absolute bottom-3 left-3 z-20 bg-[#0B101C]/90 backdrop-blur-md border border-[#1E2D4A] rounded-lg p-3 max-w-sm text-xs">
            <div className="flex items-center justify-between pb-1 mb-1.5 border-b border-[#1E2D4A]">
              <span className="font-bold text-white flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#38BDF8]" />
                Corridor Section Telemetry
              </span>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 px-1.5 py-0.2 rounded border border-emerald-500/30">
                ACTIVE
              </span>
            </div>
            <div className="text-[11px] text-[#CBD5E1] space-y-1 font-mono">
              <div className="flex justify-between">
                <span className="text-[#64748B]">Section:</span>
                <span className="text-[#F8FAFC] font-bold">{sectionCode}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Gauge / Rails:</span>
                <span className="text-[#F8FAFC]">1676mm Broad Gauge · UIC 60</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Traction OHE:</span>
                <span className="text-amber-400">25 kV AC 50 Hz</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Worksite:</span>
                <span className="text-[#38BDF8] truncate max-w-[200px]">{workOrderTitle}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
