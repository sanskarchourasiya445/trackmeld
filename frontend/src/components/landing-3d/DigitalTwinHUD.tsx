'use client';

import React from 'react';
import { CameraMode, LightingPreset, TelemetryMarker } from './types';
import {
  Video,
  Eye,
  Compass,
  Sun,
  Moon,
  Cloud,
  Play,
  Pause,
  Gauge,
  Layers,
  X,
  Radio,
  Sliders,
} from 'lucide-react';

interface DigitalTwinHUDProps {
  cameraMode: CameraMode;
  onSetCameraMode: (mode: CameraMode) => void;
  lighting: LightingPreset;
  onSetLighting: (preset: LightingPreset) => void;
  trainSpeedKmh: number;
  onSetTrainSpeedKmh: (speed: number) => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  showTelemetry: boolean;
  onToggleTelemetry: () => void;
  selectedMarker: TelemetryMarker | null;
  onCloseSelectedMarker: () => void;
  compact?: boolean;
}

/**
 * Digital Twin View Controls Toolbar:
 * Horizontal visualization toolbar positioned directly underneath the 3D railway scene.
 * Replaces the old floating top-right panel to give the railway visualization and operational annotations full focus.
 */
export const DigitalTwinHUD: React.FC<DigitalTwinHUDProps> = ({
  cameraMode,
  onSetCameraMode,
  lighting,
  onSetLighting,
  trainSpeedKmh,
  onSetTrainSpeedKmh,
  isPlaying,
  onTogglePlay,
  showTelemetry,
  onToggleTelemetry,
  selectedMarker,
  onCloseSelectedMarker,
  compact = false,
}) => {
  // View descriptions for active camera mode
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

  return (
    <div className="relative w-full">
      {/* ------------------------------------------------------------------ */}
      {/* INSPECTED ENTITY DETAIL DRAWER (Anchored above toolbar when clicked)*/}
      {/* ------------------------------------------------------------------ */}
      {selectedMarker && (
        <div className="absolute bottom-full mb-3 right-6 sm:right-12 z-30 backdrop-blur-md bg-[#070D18]/95 border border-[#2563EB]/40 rounded-xl p-4 shadow-2xl max-w-[340px] pointer-events-auto animate-in fade-in slide-in-from-bottom-2 duration-200">
          <div className="flex items-start justify-between gap-3 pb-2 border-b border-[#1E293B]">
            <div>
              <div className="text-[10px] font-mono uppercase text-[#38BDF8] font-bold">
                {selectedMarker.title}
              </div>
              <div className="text-xs font-bold text-[#F1F5F9] mt-0.5">
                {selectedMarker.subtitle}
              </div>
            </div>
            <button
              onClick={onCloseSelectedMarker}
              className="p-1 rounded hover:bg-[#1E293B] text-[#94A3B8] hover:text-white transition-colors cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="mt-2.5 space-y-1.5 text-[10px] font-mono">
            {selectedMarker.details.map((d, i) => (
              <div key={i} className="flex items-center justify-between text-[#94A3B8]">
                <span>{d.label}:</span>
                <span className="text-[#F1F5F9] font-medium">{d.value}</span>
              </div>
            ))}
          </div>

          <div className="mt-3 pt-2 border-t border-[#1E293B] flex items-center justify-between text-[9px] font-mono text-[#64748B]">
            <span className="flex items-center gap-1 text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              LIVE TELEMETRY
            </span>
            <span>PROVENANCE: 16I-C</span>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* HORIZONTAL DIGITAL TWIN VIEW CONTROLS TOOLBAR                      */}
      {/* ------------------------------------------------------------------ */}
      <div className={`w-full ${compact ? 'px-3 py-1.5' : 'px-6 sm:px-12 lg:px-20 py-3'} flex flex-wrap items-center justify-between gap-4`}>
        {/* ================================================================ */}
        {/* LEFT: VIEW IDENTITY & CONCISE CONTEXT                            */}
        {/* ================================================================ */}
        <div className="flex items-center gap-3 min-w-[220px]">
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-sky-950/60 border border-sky-500/30 text-[10px] font-mono font-bold text-[#38BDF8] uppercase tracking-wider">
                <Radio className="w-2.5 h-2.5 text-[#38BDF8] animate-pulse" />
                DIGITAL TWIN VIEW
              </span>
              <span className="text-[10px] font-mono text-[#64748B] hidden sm:inline">
                DIGITAL TWIN HUD
              </span>
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-xs sm:text-sm font-bold text-[#F8FAFC] tracking-tight">
                {activeMeta.title}
              </span>
              <span className="text-[11px] font-mono text-[#64748B] hidden md:inline">
                — {activeMeta.desc}
              </span>
            </div>
          </div>
        </div>

        {/* ================================================================ */}
        {/* CENTER: FOUR SELECTABLE CAMERA VIEW OPTIONS                      */}
        {/* ================================================================ */}
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-mono uppercase text-[#64748B] mr-1 hidden xl:inline">
            Camera View
          </span>
          <div className="inline-flex items-center p-1 rounded-lg bg-[#070D18] border border-[#1E293B] shadow-inner gap-1">
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
                  onClick={() => {
                    onSetCameraMode(btn.id);
                    onCloseSelectedMarker();
                  }}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-mono font-medium transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-[#38BDF8] focus-visible:outline-none ${
                    isActive
                      ? 'bg-[#2563EB] text-white shadow-md shadow-blue-600/30 ring-1 ring-blue-400/40'
                      : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#1E293B]/70'
                  }`}
                  aria-pressed={isActive}
                  aria-label={`Switch to ${btn.label} camera perspective`}
                  title={`Switch to ${btn.label} camera perspective`}
                >
                  <Icon className="w-3.5 h-3.5 shrink-0" />
                  <span>{btn.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* ================================================================ */}
        {/* RIGHT: ATMOSPHERE, TELEMETRY, & VELOCITY SCRUBBER                */}
        {/* ================================================================ */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Atmosphere Selector */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-mono uppercase text-[#64748B] hidden lg:inline">
              Atmosphere
            </span>
            <div className="inline-flex items-center p-0.5 rounded-lg bg-[#070D18] border border-[#1E293B]">
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
                    onClick={() => onSetLighting(btn.id)}
                    className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-mono transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-[#38BDF8] focus-visible:outline-none ${
                      isActive
                        ? 'bg-[#1E293B] text-[#38BDF8] border border-[#38BDF8]/40 shadow-sm'
                        : 'text-[#64748B] hover:text-[#94A3B8]'
                    }`}
                    aria-label={`Atmosphere Preset: ${btn.label}`}
                    title={`Lighting Preset: ${btn.label}`}
                  >
                    <Icon className="w-3 h-3" />
                    <span>{btn.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Telemetry Overlays Toggle */}
          <button
            onClick={onToggleTelemetry}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-mono transition-all border cursor-pointer focus-visible:ring-2 focus-visible:ring-[#38BDF8] focus-visible:outline-none ${
              showTelemetry
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-[#070D18] text-[#64748B] border-[#1E293B]'
            }`}
            aria-label={`Toggle telemetry overlays. Currently ${showTelemetry ? 'enabled' : 'muted'}`}
            title="Toggle digital twin telemetry anchors"
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                showTelemetry ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'
              }`}
            />
            <span>{showTelemetry ? 'Anchors: ON' : 'Anchors: MUTED'}</span>
          </button>

          {/* Train Velocity & Playback Scrubber */}
          <div className="flex items-center gap-2 pl-2 border-l border-[#1E293B]/80">
            <button
              onClick={onTogglePlay}
              className="w-7 h-7 rounded-lg bg-[#1E293B] text-[#F1F5F9] hover:bg-[#2563EB] transition-colors flex items-center justify-center cursor-pointer shadow-sm focus-visible:ring-2 focus-visible:ring-[#38BDF8] focus-visible:outline-none"
              aria-label={isPlaying ? 'Pause simulation motion' : 'Resume simulation motion'}
              title={isPlaying ? 'Pause simulation motion' : 'Resume simulation motion'}
            >
              {isPlaying ? (
                <Pause className="w-3.5 h-3.5" />
              ) : (
                <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
              )}
            </button>
            <div className="hidden sm:flex items-center gap-2">
              <input
                type="range"
                min="0"
                max="160"
                step="5"
                value={trainSpeedKmh}
                onChange={(e) => onSetTrainSpeedKmh(Number(e.target.value))}
                className="w-20 lg:w-24 accent-[#2563EB] h-1.5 bg-[#0F172A] rounded cursor-pointer focus-visible:ring-2 focus-visible:ring-[#38BDF8] focus-visible:outline-none"
                aria-label={`Train Velocity Slider: currently ${trainSpeedKmh} km/h`}
                title={`Train Velocity: ${trainSpeedKmh} km/h`}
              />
              <span className="text-[11px] font-mono font-bold text-[#F1F5F9] min-w-[55px] text-right">
                {isPlaying ? `${trainSpeedKmh} km/h` : 'PAUSED'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
