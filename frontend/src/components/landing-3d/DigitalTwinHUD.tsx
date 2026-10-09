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
}

/**
 * Enterprise Railway HUD Controls:
 * - Camera Perspective Switcher
 * - Industrial Lighting Presets (Dawn, Night, Overcast)
 * - Telemetry Toggle
 * - Train Kinematics & Velocity Scrubber
 * - Inspected Entity Detail Drawer
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
}) => {
  return (
    <>
      {/* ================================================================== */}
      {/* TOP-RIGHT CONTROLS DOCK                                            */}
      {/* ================================================================== */}
      <div className="absolute top-20 right-4 sm:right-8 z-30 flex flex-col gap-2 max-w-[280px] pointer-events-auto">
        {/* Main Dock Container */}
        <div className="backdrop-blur-md bg-[#070D18]/85 border border-[#1E293B] rounded-lg p-2.5 shadow-2xl space-y-2.5">
          {/* Header */}
          <div className="flex items-center justify-between text-[10px] font-mono text-[#64748B] border-b border-[#1E293B] pb-1.5">
            <span className="flex items-center gap-1.5 text-[#38BDF8] font-bold">
              <Radio className="w-3 h-3 text-[#38BDF8] animate-pulse" />
              DIGITAL TWIN HUD
            </span>
            <span className="text-[#94A3B8]">NDLS–GZB (km 14.2)</span>
          </div>

          {/* 1. Camera Switcher */}
          <div>
            <div className="text-[9px] font-mono text-[#94A3B8] uppercase tracking-wider mb-1 flex items-center justify-between">
              <span>Camera View</span>
              <span className="text-[#38BDF8] font-bold">{cameraMode.toUpperCase()}</span>
            </div>
            <div className="grid grid-cols-4 gap-1">
              {[
                { id: 'cinematic' as CameraMode, label: 'Cinema', icon: Video },
                { id: 'cab' as CameraMode, label: 'Cab', icon: Eye },
                { id: 'drone' as CameraMode, label: 'Drone', icon: Layers },
                { id: 'orbit' as CameraMode, label: 'Orbit', icon: Compass },
              ].map((btn) => {
                const Icon = btn.icon;
                const isActive = cameraMode === btn.id;
                return (
                  <button
                    key={btn.id}
                    onClick={() => onSetCameraMode(btn.id)}
                    className={`flex flex-col items-center justify-center p-1.5 rounded text-[8px] font-mono transition-all ${
                      isActive
                        ? 'bg-[#2563EB] text-white shadow-md shadow-blue-500/30'
                        : 'bg-[#0F172A] text-[#94A3B8] hover:bg-[#1E293B] hover:text-[#F1F5F9]'
                    }`}
                  >
                    <Icon className="w-3 h-3 mb-0.5" />
                    <span>{btn.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 2. Lighting Preset Switcher */}
          <div>
            <div className="text-[9px] font-mono text-[#94A3B8] uppercase tracking-wider mb-1 flex items-center justify-between">
              <span>Atmosphere</span>
              <span className="text-[#38BDF8]">{lighting.toUpperCase()}</span>
            </div>
            <div className="grid grid-cols-3 gap-1">
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
                    className={`flex items-center justify-center gap-1 py-1 px-1.5 rounded text-[9px] font-mono transition-all ${
                      isActive
                        ? 'bg-[#1E293B] text-[#38BDF8] border border-[#38BDF8]/40'
                        : 'bg-[#0F172A] text-[#64748B] hover:text-[#94A3B8]'
                    }`}
                  >
                    <Icon className="w-2.5 h-2.5" />
                    <span>{btn.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 3. Telemetry Overlays Toggle */}
          <div className="flex items-center justify-between pt-1 border-t border-[#1E293B] text-[9px] font-mono">
            <span className="text-[#94A3B8]">Telemetry Anchors</span>
            <button
              onClick={onToggleTelemetry}
              className={`px-2 py-0.5 rounded transition-colors ${
                showTelemetry
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-[#0F172A] text-[#64748B]'
              }`}
            >
              {showTelemetry ? 'ENABLED' : 'MUTED'}
            </button>
          </div>

          {/* 4. Train Velocity Control */}
          <div className="pt-1.5 border-t border-[#1E293B] space-y-1">
            <div className="flex items-center justify-between text-[9px] font-mono text-[#94A3B8]">
              <span className="flex items-center gap-1">
                <Gauge className="w-2.5 h-2.5 text-[#38BDF8]" />
                Train Velocity
              </span>
              <span className="text-[#F1F5F9] font-bold">{isPlaying ? `${trainSpeedKmh} km/h` : 'PAUSED'}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={onTogglePlay}
                className="w-6 h-6 rounded bg-[#1E293B] text-[#F1F5F9] hover:bg-[#2563EB] transition-colors flex items-center justify-center"
              >
                {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3 fill-current" />}
              </button>
              <input
                type="range"
                min="0"
                max="160"
                step="5"
                value={trainSpeedKmh}
                onChange={(e) => onSetTrainSpeedKmh(Number(e.target.value))}
                className="w-full accent-[#2563EB] h-1.5 bg-[#0F172A] rounded cursor-pointer"
              />
            </div>
          </div>
        </div>
      </div>

      {/* ================================================================== */}
      {/* INSPECTED ENTITY DETAIL DRAWER (When a marker is clicked)          */}
      {/* ================================================================== */}
      {selectedMarker && (
        <div className="absolute bottom-16 right-4 sm:right-8 z-30 backdrop-blur-md bg-[#070D18]/95 border border-[#2563EB]/40 rounded-lg p-3.5 shadow-2xl max-w-[320px] pointer-events-auto animate-in fade-in slide-in-from-bottom-2 duration-200">
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
              className="p-1 rounded hover:bg-[#1E293B] text-[#94A3B8] hover:text-white transition-colors"
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
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              LIVE DIGITAL TWIN
            </span>
            <span>DATA PROVENANCE: 16I-C</span>
          </div>
        </div>
      )}
    </>
  );
};
