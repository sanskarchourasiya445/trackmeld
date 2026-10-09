'use client';

import React, { useState, useEffect, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { CameraMode, LightingPreset, TelemetryMarker } from './types';
import { RailwayScene } from './RailwayScene';
import { DigitalTwinMarkers } from './DigitalTwinMarkers';
import { DigitalTwinHUD } from './DigitalTwinHUD';
import { CameraRig } from './CameraRig';
import { FallbackRailwayCanvas } from './FallbackRailwayCanvas';
import {
  ArrowRight,
  ShieldCheck,
  Cpu,
  Lock,
} from 'lucide-react';

// Dynamic import of Three.js Canvas with SSR disabled to prevent server hydration mismatches
const Canvas = dynamic(
  () => import('@react-three/fiber').then((mod) => mod.Canvas),
  { ssr: false }
);

interface LandingHero3DProps {
  onRequestDemo: () => void;
}

export const LandingHero3D: React.FC<LandingHero3DProps> = ({ onRequestDemo }) => {
  const [mounted, setMounted] = useState<boolean>(false);
  const [cameraMode, setCameraMode] = useState<CameraMode>('cinematic');
  const [lighting, setLighting] = useState<LightingPreset>('dawn');
  const [trainSpeedKmh, setTrainSpeedKmh] = useState<number>(120);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [showTelemetry, setShowTelemetry] = useState<boolean>(true);
  const [selectedMarkerId, setSelectedMarkerId] = useState<string | null>(null);
  const [hasWebGLError, setHasWebGLError] = useState<boolean>(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Digital Twin Telemetry Markers in 3D Space
  const markers: TelemetryMarker[] = useMemo(
    () => [
      {
        id: 'train-express07',
        title: 'EXPRESS-07',
        subtitle: 'High-Speed Express Rake',
        tag: 'ON TIME',
        tagColor: 'blue',
        position: [12.0, 4.4, -2.0],
        entityType: 'train',
        details: [
          { label: 'VELOCITY', value: `${trainSpeedKmh} km/h` },
          { label: 'BLOCK SECTION', value: 'SEC-03 (UP MAIN)' },
          { label: 'CHAINAGE', value: 'KM 14.2 to 28.6' },
          { label: 'TRACTION', value: '25 kV AC Electric' },
        ],
      },
      {
        id: 'possession-s04',
        title: 'MAINTENANCE S-04',
        subtitle: 'P-Way Ballast Tamping',
        tag: 'APPROVED',
        tagColor: 'amber',
        position: [42.0, 3.2, 2.0],
        entityType: 'possession',
        details: [
          { label: 'WINDOW', value: '14:20 — 16:10 UTC' },
          { label: 'TRACK', value: 'LINE 02 (DOWN MAIN)' },
          { label: 'MACHINERY', value: 'Plasser 08-32 Tamping Unit' },
          { label: 'TRACTION ISOLATION', value: 'FEEDER FS-02 ISOLATED' },
        ],
      },
      {
        id: 'conflict-headway',
        title: 'CONFLICT RESOLVED',
        subtitle: 'Headway Verification',
        tag: 'CP-SAT VALID',
        tagColor: 'emerald',
        position: [26.0, 2.8, 0.0],
        entityType: 'conflict',
        details: [
          { label: 'INITIAL CONTENTION', value: 'EXPRESS-07 × TSK-127' },
          { label: 'TEMPORAL DELTA', value: '+18.4 min Safety Gap' },
          { label: 'ADJACENT IMPACT', value: 'CAUTION_ORDER (45 km/h)' },
          { label: 'SOLVER STATUS', value: 'OPTIMAL (Single-Worker)' },
        ],
      },
      {
        id: 'catenary-sector',
        title: 'CATENARY SECTOR 02',
        subtitle: 'OHE Feeder Substation',
        tag: '25.4 kV AC',
        tagColor: 'cyan',
        position: [32.0, 7.8, -5.8],
        entityType: 'catenary',
        details: [
          { label: 'NOMINAL VOLTAGE', value: '25 kV AC 50 Hz' },
          { label: 'PERMIT TO WORK', value: 'OHE-PTW-8819 ISSUED' },
          { label: 'EARTHING DISCONNECT', value: 'MAST 44/12 EARTHED' },
        ],
      },
    ],
    [trainSpeedKmh]
  );

  const selectedMarker = useMemo(
    () => markers.find((m) => m.id === selectedMarkerId) || null,
    [markers, selectedMarkerId]
  );

  return (
    <section className="relative w-full h-screen min-h-[760px] max-h-[1080px] bg-[#04070D] overflow-hidden flex flex-col justify-between">
      {/* ------------------------------------------------------------------ */}
      {/* 3D WEBGL RAILWAY CANVAS OR FALLBACK                                 */}
      {/* ------------------------------------------------------------------ */}
      <div className="absolute inset-0 z-0">
        {mounted && !hasWebGLError ? (
          <Canvas
            shadows
            camera={{ position: [24.0, 4.5, 14.5], fov: 36, near: 0.1, far: 500 }}
            gl={{ antialias: true, alpha: false, powerPreference: 'high-performance' }}
            onCreated={({ gl }) => {
              gl.setClearColor(lighting === 'night' ? '#050A15' : lighting === 'overcast' ? '#0E1726' : '#060A13');
            }}
            onError={() => setHasWebGLError(true)}
          >
            {/* Cinematic Trackside Camera Rig */}
            <CameraRig
              cameraMode={cameraMode}
              targetMarkerPosition={selectedMarker?.position ?? null}
            />

            {/* 3D Railway Environment & High-Fidelity Passenger Train */}
            <RailwayScene
              cameraMode={cameraMode}
              lighting={lighting}
              trainSpeedKmh={trainSpeedKmh}
              isPlaying={isPlaying}
              onSelectTrain={() => setSelectedMarkerId('train-express07')}
              onSelectPossession={(id) => setSelectedMarkerId(id)}
              selectedEntity={selectedMarkerId}
            />

            {/* Anchored 3D Digital Twin Overlays */}
            <DigitalTwinMarkers
              markers={markers}
              selectedMarkerId={selectedMarkerId}
              onSelectMarker={(id) => setSelectedMarkerId(id)}
              showTelemetry={showTelemetry}
            />
          </Canvas>
        ) : (
          <div className="p-8 h-full">
            <FallbackRailwayCanvas />
          </div>
        )}
      </div>

      {/* Localized soft vignette behind left typography column, leaving center and right 3D railway crystal clear */}
      <div className="absolute inset-y-0 left-0 w-full lg:w-[46%] pointer-events-none bg-gradient-to-r from-[#04070D]/90 via-[#04070D]/40 to-transparent z-10" />
      <div className="absolute bottom-0 inset-x-0 h-28 pointer-events-none bg-gradient-to-t from-[#04070D] to-transparent z-10" />

      {/* ------------------------------------------------------------------ */}
      {/* TOP HUD CONTROLS DOCK                                              */}
      {/* ------------------------------------------------------------------ */}
      <DigitalTwinHUD
        cameraMode={cameraMode}
        onSetCameraMode={(mode) => {
          setCameraMode(mode);
          setSelectedMarkerId(null);
        }}
        lighting={lighting}
        onSetLighting={setLighting}
        trainSpeedKmh={trainSpeedKmh}
        onSetTrainSpeedKmh={setTrainSpeedKmh}
        isPlaying={isPlaying}
        onTogglePlay={() => setIsPlaying(!isPlaying)}
        showTelemetry={showTelemetry}
        onToggleTelemetry={() => setShowTelemetry(!showTelemetry)}
        selectedMarker={selectedMarker}
        onCloseSelectedMarker={() => setSelectedMarkerId(null)}
      />

      {/* ------------------------------------------------------------------ */}
      {/* HERO TYPOGRAPHIC CONTENT (Target 1440 × 900)                        */}
      {/* ------------------------------------------------------------------ */}
      <div className="relative z-20 pt-28 sm:pt-36 px-6 sm:px-12 lg:px-20 max-w-xl pointer-events-none">
        {/* Technical Status Pill */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#080D1A]/90 border border-[#1E293B] text-[11px] font-mono text-[#94A3B8] backdrop-blur-md shadow-lg pointer-events-auto">
          <span className="w-2 h-2 rounded-full bg-[#38BDF8] animate-pulse"></span>
          <span className="text-[#F1F5F9] font-medium">DIGITAL TWIN & POSSESSION OPTIMIZATION</span>
          <span className="text-[#64748B] hidden sm:inline">• CP-SAT DISCRETE SOLVER</span>
        </div>

        {/* Large Editorial Headline */}
        <h1 className="mt-4 text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-[#F8FAFC] leading-[1.05]">
          SMARTER
          <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#F8FAFC] via-[#E2E8F0] to-[#94A3B8]">
            RAILWAY
          </span>
          <br />
          <span className="text-[#38BDF8]">PLANNING.</span>
        </h1>

        {/* Supporting Copy */}
        <p className="mt-6 text-sm sm:text-base lg:text-lg text-[#94A3B8] max-w-md leading-relaxed font-normal">
          Plan maintenance windows around real railway constraints — then validate every decision before it reaches the track.
        </p>

        {/* Primary and Secondary CTA Buttons */}
        <div className="mt-8 flex flex-wrap items-center gap-4 pointer-events-auto">
          <button
            onClick={() => {
              setCameraMode('drone');
              const el = document.getElementById('digital-twin');
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            className="group px-6 h-12 rounded-lg bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs sm:text-sm font-semibold tracking-wide flex items-center gap-2 shadow-lg shadow-blue-600/30 transition-all hover:shadow-blue-500/50 hover:translate-y-[-1px]"
          >
            <span>EXPLORE THE DIGITAL TWIN</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>

          <button
            onClick={() => {
              const el = document.getElementById('optimization');
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            className="px-5 h-12 rounded-lg bg-[#0F172A]/80 hover:bg-[#1E293B] text-[#F1F5F9] border border-[#1E293B] hover:border-[#38BDF8]/40 text-xs sm:text-sm font-medium tracking-wide backdrop-blur-md transition-all"
          >
            SEE HOW IT WORKS
          </button>

          <button
            onClick={onRequestDemo}
            className="hidden lg:inline-flex items-center gap-1.5 px-4 h-12 rounded-lg bg-[#080D1A]/90 hover:bg-[#0F172A] text-sky-300 border border-sky-500/30 hover:border-sky-400 text-xs font-mono tracking-wider backdrop-blur-md transition-all cursor-pointer"
          >
            <span>REQUEST BRIEFING</span>
          </button>
        </div>

        {/* Value Anchor Pills */}
        <div className="mt-8 hidden sm:flex items-center gap-3 text-[11px] font-mono text-[#64748B]">
          <span className="flex items-center gap-1.5 text-[#94A3B8]">
            <Cpu className="w-3.5 h-3.5 text-[#38BDF8]" />
            CP-SAT Optimization
          </span>
          <span>•</span>
          <span className="flex items-center gap-1.5 text-[#94A3B8]">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Independent 13-Check Validator
          </span>
          <span>•</span>
          <span className="flex items-center gap-1.5 text-[#94A3B8]">
            <Lock className="w-3.5 h-3.5 text-amber-400" />
            Four-Eyes Human Sign-off
          </span>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* BOTTOM KPI METRIC TICKER (NDLS–CNB Northern Trunk Corridor Model)    */}
      {/* ------------------------------------------------------------------ */}
      <div className="relative z-20 w-full border-t border-[#1E293B]/80 bg-[#04070D]/90 backdrop-blur-md px-6 sm:px-12 lg:px-20 py-4">
        <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-4 divide-y md:divide-y-0 md:divide-x divide-[#1E293B]">
          <div className="pt-2 md:pt-0 pr-4">
            <div className="text-[10px] font-mono uppercase tracking-wider text-[#64748B]">
              Corridor Digital Twin
            </div>
            <div className="mt-1 flex items-baseline gap-2 font-mono">
              <span className="text-xl sm:text-2xl font-bold text-[#F8FAFC]">440 km</span>
              <span className="text-[11px] text-[#38BDF8]">NDLS–CNB Trunk</span>
            </div>
          </div>

          <div className="pt-2 md:pt-0 pl-0 md:pl-4 pr-4">
            <div className="text-[10px] font-mono uppercase tracking-wider text-[#64748B]">
              Physical Track Identity
            </div>
            <div className="mt-1 flex items-baseline gap-2 font-mono">
              <span className="text-xl sm:text-2xl font-bold text-[#F8FAFC]">132 Tracks</span>
              <span className="text-[11px] text-emerald-400">264 Endpoints</span>
            </div>
          </div>

          <div className="pt-2 md:pt-0 pl-0 md:pl-4 pr-4">
            <div className="text-[10px] font-mono uppercase tracking-wider text-[#64748B]">
              Safety Validation Firewall
            </div>
            <div className="mt-1 flex items-baseline gap-2 font-mono">
              <span className="text-xl sm:text-2xl font-bold text-emerald-400">13 Categories</span>
              <span className="text-[11px] text-[#94A3B8]">Zero Solver Bypass</span>
            </div>
          </div>

          <div className="pt-2 md:pt-0 pl-0 md:pl-4">
            <div className="text-[10px] font-mono uppercase tracking-wider text-[#64748B]">
              Operational Governance
            </div>
            <div className="mt-1 flex items-baseline gap-2 font-mono">
              <span className="text-xl sm:text-2xl font-bold text-amber-400">Four-Eyes</span>
              <span className="text-[11px] text-[#94A3B8]">Creator ≠ Approver</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
