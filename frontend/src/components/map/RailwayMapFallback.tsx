'use client';

import React, { useState } from 'react';
import {
  CORRIDOR_STATIONS_GIS,
  CORRIDOR_SECTIONS_GIS,
  ACTIVE_TRAINS_GIS,
  CORRIDOR_SIGNALS_GIS,
  ActiveTrainGis,
  StationGisNode,
  TrackSectionGis,
} from '@/lib/railway/corridorGisData';
import {
  Layers,
  MapPin,
  Train,
  AlertTriangle,
  Zap,
  Radio,
  Eye,
  Crosshair,
  Maximize2,
  ZoomIn,
  ZoomOut,
  Info,
} from 'lucide-react';

interface RailwayMapFallbackProps {
  selectedSectionCode?: string | null;
  selectedTaskId?: string | null;
  selectedTrainId?: string | null;
  onSelectSection?: (sectionCode: string) => void;
  onSelectTask?: (taskId: string) => void;
  onSelectTrain?: (trainId: string) => void;
  onSelectStation?: (stationCode: string) => void;
  onOpenDigitalTwin?: (sectionCode: string) => void;
}

export const RailwayMapFallback: React.FC<RailwayMapFallbackProps> = ({
  selectedSectionCode = 'SEC-12',
  selectedTaskId = 'TSK-0007',
  selectedTrainId,
  onSelectSection,
  onSelectTask,
  onSelectTrain,
  onSelectStation,
  onOpenDigitalTwin,
}) => {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [activeLayers, setActiveLayers] = useState({
    tracks: true,
    stations: true,
    trains: true,
    workZones: true,
    signals: true,
    ohe: true,
  });

  const toggleLayer = (layerKey: keyof typeof activeLayers) => {
    setActiveLayers((prev) => ({ ...prev, [layerKey]: !prev[layerKey] }));
  };

  // Convert longitude (77.0 - 80.6) to SVG X (60 - 940)
  const lngToX = (lng: number) => {
    const minLng = 77.1;
    const maxLng = 80.5;
    return 60 + ((lng - minLng) / (maxLng - minLng)) * 880;
  };

  // Convert latitude (28.8 - 26.3) to SVG Y (60 - 440)
  const latToY = (lat: number) => {
    const minLat = 26.3;
    const maxLat = 28.8;
    return 60 + ((maxLat - lat) / (maxLat - minLat)) * 380;
  };

  return (
    <div className="relative w-full h-full bg-[#050912] overflow-hidden select-none font-sans flex flex-col border border-[#1E2D4A] rounded-lg">
      {/* Top Map HUD Bar */}
      <div className="h-10 bg-[#0B101C]/90 backdrop-blur-md border-b border-[#1E2D4A] px-3 flex items-center justify-between z-20 shrink-0">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs font-bold text-[#F8FAFC]">
            <Radio className="w-3.5 h-3.5 text-[#3B82F6] animate-pulse" />
            <span>Northern Trunk Corridor Spatial Map</span>
          </span>
          <span className="text-[10px] font-mono bg-[#141F36] text-[#93C5FD] px-2 py-0.5 rounded border border-[#2D436D]">
            NDLS → CNB (440 km)
          </span>
          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-amber-400 bg-amber-950/60 px-1.5 py-0.5 rounded border border-amber-500/30 font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            SYNTHETIC DEMO
          </span>
          <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            SCHEMATIC GIS
          </span>
        </div>

        {/* Right Layer Filters */}
        <div className="flex items-center gap-1.5 text-[11px]">
          <button
            onClick={() => toggleLayer('tracks')}
            className={`px-2 py-0.5 rounded border transition-colors ${
              activeLayers.tracks
                ? 'bg-[#141F36] text-white border-[#3B82F6]'
                : 'text-[#64748B] border-[#1E2D4A] hover:text-[#94A3B8]'
            }`}
          >
            Tracks
          </button>
          <button
            onClick={() => toggleLayer('trains')}
            className={`px-2 py-0.5 rounded border transition-colors ${
              activeLayers.trains
                ? 'bg-[#141F36] text-white border-[#3B82F6]'
                : 'text-[#64748B] border-[#1E2D4A] hover:text-[#94A3B8]'
            }`}
          >
            Trains
          </button>
          <button
            onClick={() => toggleLayer('workZones')}
            className={`px-2 py-0.5 rounded border transition-colors ${
              activeLayers.workZones
                ? 'bg-[#141F36] text-white border-[#F59E0B]'
                : 'text-[#64748B] border-[#1E2D4A] hover:text-[#94A3B8]'
            }`}
          >
            Possessions
          </button>
          <button
            onClick={() => toggleLayer('signals')}
            aria-label="Toggle signalling infrastructure layer"
            className={`px-2 py-0.5 rounded border transition-colors hidden md:block ${
              activeLayers.signals
                ? 'bg-[#141F36] text-white border-[#10B981]'
                : 'text-[#64748B] border-[#1E2D4A] hover:text-[#94A3B8]'
            }`}
          >
            Signalling
          </button>
        </div>
      </div>

      {/* Main Interactive Vector Map Surface */}
      <div className="relative flex-1 w-full h-full overflow-hidden bg-[#04070D]">
        {/* Navigation Toolbar (Zoom / Reset) */}
        <div className="absolute top-3 left-3 z-30 flex flex-col gap-1 bg-[#0B101C]/90 backdrop-blur-md border border-[#1E2D4A] rounded-md p-1 shadow-lg">
          <button
            onClick={() => setZoomLevel((z) => Math.min(z + 0.2, 2.4))}
            className="p-1.5 text-[#94A3B8] hover:text-white hover:bg-[#141F36] rounded transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setZoomLevel((z) => Math.max(z - 0.2, 0.8))}
            className="p-1.5 text-[#94A3B8] hover:text-white hover:bg-[#141F36] rounded transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <div className="h-[1px] bg-[#1E2D4A] my-0.5" />
          <button
            onClick={() => {
              setZoomLevel(1);
              setPanOffset({ x: 0, y: 0 });
            }}
            className="p-1.5 text-[#94A3B8] hover:text-white hover:bg-[#141F36] rounded transition-colors"
            title="Recenter Map"
          >
            <Crosshair className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* 3D Digital Twin Quick-Launch Float on Selected Section */}
        {selectedSectionCode && (
          <div className="absolute top-3 right-3 z-30 bg-[#0B101C]/95 backdrop-blur-md border border-[#2563EB] rounded-lg p-2.5 shadow-2xl flex items-center gap-3">
            <div>
              <div className="text-[10px] uppercase font-bold text-[#64748B] tracking-wider">
                Active Selection
              </div>
              <div className="text-xs font-bold text-white font-mono flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#2563EB] animate-pulse" />
                {selectedSectionCode} (km 209–301)
              </div>
            </div>
            <button
              onClick={() => onOpenDigitalTwin?.(selectedSectionCode)}
              className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[11px] font-semibold px-2.5 py-1.5 rounded flex items-center gap-1.5 shadow-xs transition-colors cursor-pointer"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Open 3D Twin</span>
            </button>
          </div>
        )}

        {/* Scalable SVG Map Canvas */}
        <div
          className="w-full h-full cursor-grab active:cursor-grabbing transition-transform duration-100"
          style={{
            transform: `scale(${zoomLevel}) translate(${panOffset.x}px, ${panOffset.y}px)`,
            transformOrigin: 'center center',
          }}
        >
          <svg
            viewBox="0 0 1000 500"
            className="w-full h-full"
            style={{ shapeRendering: 'geometricPrecision' }}
          >
            <defs>
              {/* Subtle grid pattern */}
              <pattern id="rail-grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#121824" strokeWidth="0.8" />
              </pattern>
              {/* Gradient for Trunk alignment */}
              <linearGradient id="trunk-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#2563EB" />
                <stop offset="50%" stopColor="#38BDF8" />
                <stop offset="100%" stopColor="#1D4ED8" />
              </linearGradient>
              {/* Glow filter for selected route */}
              <filter id="glow-route" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Background Grid */}
            <rect width="1000" height="500" fill="url(#rail-grid)" />

            {/* Geographic Terrain & Waterways (Subtle Yamuna / Ganga river curve) */}
            <path
              d="M 120 40 Q 280 160 480 230 T 820 410 T 960 480"
              fill="none"
              stroke="#0E1726"
              strokeWidth="24"
              strokeLinecap="round"
              opacity="0.6"
            />
            <text x="320" y="195" fill="#1E293B" fontSize="10" fontFamily="sans-serif" letterSpacing="2">
              YAMUNA RIVER BASIN
            </text>

            {/* Track Sections Alignment Lines */}
            {activeLayers.tracks &&
              CORRIDOR_SECTIONS_GIS.map((sec, sIdx) => {
                const points = sec.coordinates
                  .map((coord) => `${lngToX(coord[0])},${latToY(coord[1])}`)
                  .join(' ');
                const isSelected = selectedSectionCode === sec.code || selectedSectionCode === sec.section_id;
                const isPossession = sec.up_line_status === 'POSSESSION';

                // True midpoint calculation along the section coordinates
                const coords = sec.coordinates;
                const midIdx = Math.max(1, Math.floor(coords.length / 2));
                const c1 = coords[midIdx - 1] || coords[0];
                const c2 = coords[midIdx];
                const midLng = (c1[0] + c2[0]) / 2;
                const midLat = (c1[1] + c2[1]) / 2;
                const midX = lngToX(midLng);
                const midY = latToY(midLat) + (sIdx % 2 === 0 ? -16 : 14);

                return (
                  <g key={sec.section_id} onClick={() => onSelectSection?.(sec.code)} className="cursor-pointer group">
                    {/* Outer Click Boundary */}
                    <polyline
                      points={points}
                      fill="none"
                      stroke="transparent"
                      strokeWidth="24"
                    />

                    {/* DOWN Mainline (Parallel offset line) */}
                    <polyline
                      points={points}
                      fill="none"
                      stroke="#1E293B"
                      strokeWidth="2"
                      strokeDasharray="4 2"
                    />

                    {/* UP Mainline Track Base */}
                    <polyline
                      points={points}
                      fill="none"
                      stroke={
                        isSelected
                          ? '#38BDF8'
                          : isPossession
                          ? '#F59E0B'
                          : '#2563EB'
                      }
                      strokeWidth={isSelected ? '4' : '2.5'}
                      filter={isSelected ? 'url(#glow-route)' : undefined}
                      opacity={isSelected ? 1 : 0.85}
                    />

                    {/* Deconflicted Track Section Label Midpoint */}
                    <g transform={`translate(${midX}, ${midY})`}>
                      <rect
                        x="-24"
                        y="-8"
                        width="48"
                        height="16"
                        rx="3"
                        fill="#0B101C"
                        stroke={isSelected ? '#38BDF8' : '#1E2D4A'}
                        strokeWidth="1"
                      />
                      <text
                        x="0"
                        y="0"
                        textAnchor="middle"
                        fill={isSelected ? '#38BDF8' : '#94A3B8'}
                        fontSize="7.5"
                        fontFamily="monospace"
                        fontWeight="bold"
                        dy=".3em"
                      >
                        {sec.code}
                      </text>
                    </g>
                  </g>
                );
              })}

            {/* Active Work Zone Possessions */}
            {activeLayers.workZones && (
              <g
                onClick={() => onSelectTask?.('TSK-0007')}
                className="cursor-pointer group"
                transform={`translate(${lngToX(78.64)}, ${latToY(27.01)})`}
              >
                {/* Pulsing Possession Halo */}
                <circle r="18" fill="#F59E0B" fillOpacity="0.15" className="animate-ping" />
                <rect
                  x="-52"
                  y="-12"
                  width="104"
                  height="24"
                  rx="4"
                  fill="#0F172A"
                  stroke="#F59E0B"
                  strokeWidth="1.5"
                />
                <text
                  x="0"
                  y="2"
                  textAnchor="middle"
                  fill="#F59E0B"
                  fontSize="8.5"
                  fontFamily="monospace"
                  fontWeight="bold"
                >
                  ⚡ WO-1847 (S-04)
                </text>
              </g>
            )}

            {/* Signals Layer */}
            {activeLayers.signals &&
              CORRIDOR_SIGNALS_GIS.map((sig) => {
                const x = lngToX(sig.coordinates[0]);
                const y = latToY(sig.coordinates[1]);
                const color =
                  sig.aspect === 'PROCEED'
                    ? '#10B981'
                    : sig.aspect === 'CAUTION'
                    ? '#F59E0B'
                    : sig.aspect === 'STOP'
                    ? '#EF4444'
                    : '#38BDF8';

                return (
                  <g key={sig.signal_id} transform={`translate(${x}, ${y})`} className="group cursor-pointer">
                    <circle r="3.5" fill={color} stroke="#0B101C" strokeWidth="1" />
                    {/* Signal label shown on hover or when zoomed in */}
                    <g className={`${zoomLevel >= 1.25 ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} transition-opacity pointer-events-none`}>
                      <rect
                        x="5"
                        y="-7"
                        width="36"
                        height="13"
                        rx="2"
                        fill="#0B101C"
                        stroke="#1E2D4A"
                        strokeWidth="0.8"
                      />
                      <text
                        x="23"
                        y="0"
                        textAnchor="middle"
                        fill="#94A3B8"
                        fontSize="6.5"
                        fontFamily="monospace"
                        dy=".3em"
                      >
                        {sig.code}
                      </text>
                    </g>
                  </g>
                );
              })}

            {/* Moving Trains Layer */}
            {activeLayers.trains &&
              ACTIVE_TRAINS_GIS.map((train) => {
                const x = lngToX(train.coordinates[0]);
                const y = latToY(train.coordinates[1]);
                const isSelected = selectedTrainId === train.train_id;

                // Deconflict train tag offsets based on train ID and surrounding assets
                let badgeOffsetX = 12;
                let badgeOffsetY = -14;
                if (train.train_id === 'TR-FRG-UP1') {
                  badgeOffsetX = -88;
                  badgeOffsetY = 6;
                } else if (train.train_id === 'TR-22436') {
                  badgeOffsetX = 12;
                  badgeOffsetY = -18;
                } else if (train.train_id === 'TR-12004') {
                  badgeOffsetX = 12;
                  badgeOffsetY = -12;
                } else if (train.train_id === 'TR-12424') {
                  badgeOffsetX = 12;
                  badgeOffsetY = -16;
                }

                return (
                  <g
                    key={train.train_id}
                    onClick={() => onSelectTrain?.(train.train_id)}
                    transform={`translate(${x}, ${y})`}
                    className="cursor-pointer group"
                  >
                    {/* Selection ring */}
                    {isSelected && (
                      <circle r="12" fill="none" stroke="#38BDF8" strokeWidth="1.5" strokeDasharray="3 2" className="animate-spin" />
                    )}

                    {/* Train Icon Bubble */}
                    <circle
                      r="6.5"
                      fill={train.status === 'HELD_AT_SIGNAL' ? '#EF4444' : '#2563EB'}
                      stroke="#F8FAFC"
                      strokeWidth="1.5"
                      filter="drop-shadow(0 2px 4px rgba(0,0,0,0.8))"
                    />

                    {/* Heading Chevron indicator */}
                    <path
                      d="M -3 -1 L 0 -5 L 3 -1"
                      fill="none"
                      stroke="#FFFFFF"
                      strokeWidth="1.2"
                    />

                    {/* Deconflicted Train Label Badge */}
                    <g transform={`translate(${badgeOffsetX}, ${badgeOffsetY})`}>
                      <rect
                        x="-2"
                        y="-8"
                        width="82"
                        height="18"
                        rx="3"
                        fill="#0B101C"
                        stroke={train.status === 'HELD_AT_SIGNAL' ? '#EF4444' : '#2D436D'}
                        strokeWidth="1"
                      />
                      <text
                        x="4"
                        y="0"
                        fill="#F8FAFC"
                        fontSize="7.5"
                        fontFamily="monospace"
                        fontWeight="bold"
                      >
                        {train.train_number} • {train.speed_kmh}k
                      </text>
                      <text
                        x="4"
                        y="7"
                        fill={train.status === 'HELD_AT_SIGNAL' ? '#EF4444' : '#93C5FD'}
                        fontSize="6.5"
                        fontFamily="sans-serif"
                      >
                        {train.status === 'HELD_AT_SIGNAL' ? 'HELD @ S-04' : train.name.slice(0, 14)}
                      </text>
                    </g>
                  </g>
                );
              })}

            {/* Stations Layer (Prominent Hub Markers with Staggered Anchors) */}
            {activeLayers.stations &&
              CORRIDOR_STATIONS_GIS.map((st) => {
                const x = lngToX(st.coordinates[0]);
                const y = latToY(st.coordinates[1]);

                // Dedicated anchor offset per station to avoid colliding with other stations or tracks
                let tagOffsetX = 0;
                let tagOffsetY = 16;
                if (st.code === 'NDLS') {
                  tagOffsetX = -46;
                  tagOffsetY = -6;
                } else if (st.code === 'GZB') {
                  tagOffsetX = 0;
                  tagOffsetY = -22;
                } else if (st.code === 'ALJN') {
                  tagOffsetX = -46;
                  tagOffsetY = -4;
                } else if (st.code === 'TDL') {
                  tagOffsetX = -48;
                  tagOffsetY = -4;
                } else if (st.code === 'ETW') {
                  tagOffsetX = 12;
                  tagOffsetY = 18;
                } else if (st.code === 'CNB') {
                  tagOffsetX = 0;
                  tagOffsetY = 20;
                }

                return (
                  <g
                    key={st.code}
                    onClick={() => onSelectStation?.(st.code)}
                    transform={`translate(${x}, ${y})`}
                    className="cursor-pointer group"
                  >
                    {/* Station Halo */}
                    <circle
                      r="8"
                      fill="#0B101C"
                      stroke="#38BDF8"
                      strokeWidth="2"
                      className="group-hover:scale-125 transition-transform"
                    />
                    <circle r="3.5" fill="#38BDF8" />

                    {/* Staggered Station Name & Distance Tag */}
                    <g transform={`translate(${tagOffsetX}, ${tagOffsetY})`}>
                      <rect
                        x="-30"
                        y="-8"
                        width="60"
                        height="16"
                        rx="2"
                        fill="#0F172A"
                        stroke="#1E2D4A"
                        strokeWidth="0.8"
                      />
                      <text
                        x="0"
                        y="0"
                        textAnchor="middle"
                        fill="#F8FAFC"
                        fontSize="8"
                        fontFamily="sans-serif"
                        fontWeight="bold"
                        dy=".3em"
                      >
                        {st.name}
                      </text>
                      <text
                        x="0"
                        y="14"
                        textAnchor="middle"
                        fill="#64748B"
                        fontSize="7"
                        fontFamily="monospace"
                      >
                        km {st.distance_km}
                      </text>
                    </g>
                  </g>
                );
              })}
          </svg>
        </div>

        {/* Bottom Legend */}
        <div className="absolute bottom-3 left-3 z-30 bg-[#0B101C]/90 backdrop-blur-md border border-[#1E2D4A] rounded-md px-3 py-1.5 shadow-lg text-[10px] flex items-center gap-4 text-[#CBD5E1]">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-1 bg-[#2563EB] rounded" />
            <span>Clear UP Main</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-1 bg-[#F59E0B] rounded" />
            <span>Possession Block</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#10B981]" />
            <span>Signal Clear</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#2563EB]" />
            <span>Active Train</span>
          </span>
        </div>

        {/* Scale Bar */}
        <div className="absolute bottom-3 right-3 z-30 flex items-center gap-2 bg-[#0B101C]/90 backdrop-blur-md border border-[#1E2D4A] rounded px-2.5 py-1 text-[9.5px] font-mono text-[#64748B]">
          <span>0</span>
          <div className="w-10 h-[2px] bg-[#3B82F6]" />
          <span>50</span>
          <div className="w-10 h-[2px] bg-[#3B82F6]" />
          <span>100 km</span>
        </div>
      </div>
    </div>
  );
};
