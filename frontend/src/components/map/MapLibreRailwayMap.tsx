'use client';

import React, { useEffect, useRef, useState } from 'react';
import {
  CORRIDOR_STATIONS_GIS,
  CORRIDOR_SECTIONS_GIS,
  ACTIVE_TRAINS_GIS,
  CORRIDOR_SIGNALS_GIS,
} from '@/lib/railway/corridorGisData';
import { RailwayMapFallback } from './RailwayMapFallback';
import {
  Radio,
  Eye,
  Layers,
  Zap,
  MapPin,
  Train,
  AlertTriangle,
  ZoomIn,
  ZoomOut,
  Crosshair,
} from 'lucide-react';

interface MapLibreRailwayMapProps {
  selectedSectionCode?: string | null;
  selectedTaskId?: string | null;
  selectedTrainId?: string | null;
  onSelectSection?: (sectionCode: string) => void;
  onSelectTask?: (taskId: string) => void;
  onSelectTrain?: (trainId: string) => void;
  onSelectStation?: (stationCode: string) => void;
  onOpenDigitalTwin?: (sectionCode: string) => void;
}

export const MapLibreRailwayMap: React.FC<MapLibreRailwayMapProps> = ({
  selectedSectionCode = 'SEC-12',
  selectedTaskId = 'TSK-0007',
  selectedTrainId,
  onSelectSection,
  onSelectTask,
  onSelectTrain,
  onSelectStation,
  onOpenDigitalTwin,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<unknown>(null);
  const [mapError, setMapError] = useState<boolean>(false);
  const [useFallbackOverride, setUseFallbackOverride] = useState<boolean>(false);
  const [mapLoaded, setMapLoaded] = useState<boolean>(false);

  // Check if MapTiler Key is available
  const mapTilerKey = process.env.NEXT_PUBLIC_MAPTILER_KEY;

  useEffect(() => {
    // If user explicitly chose fallback or we had an error, skip MapLibre init
    if (useFallbackOverride || mapError) return;

    let isMounted = true;
    let resizeObserver: ResizeObserver | null = null;

    async function initMap() {
      try {
        const maplibre = await import('maplibre-gl');
        if (!isMounted || !mapContainerRef.current) return;

        // Custom Dark Railway Style Schema
        const darkRailwayStyle = {
          version: 8,
          sources: {
            'osm-tiles': {
              type: 'raster',
              tiles: [
                mapTilerKey
                  ? `https://api.maptiler.com/maps/dataviz-dark/{z}/{x}/{y}.png?key=${mapTilerKey}`
                  : 'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
              ],
              tileSize: 256,
              attribution: '© OpenStreetMap contributors, CartoDB / MapTiler',
            },
            'railway-corridor': {
              type: 'geojson',
              data: {
                type: 'FeatureCollection',
                features: CORRIDOR_SECTIONS_GIS.map((sec) => ({
                  type: 'Feature',
                  properties: {
                    id: sec.section_id,
                    code: sec.code,
                    name: sec.name,
                    status: sec.up_line_status,
                    speed_limit: sec.speed_limit_kmh,
                  },
                  geometry: {
                    type: 'LineString',
                    coordinates: sec.coordinates,
                  },
                })),
              },
            },
            'railway-stations': {
              type: 'geojson',
              data: {
                type: 'FeatureCollection',
                features: CORRIDOR_STATIONS_GIS.map((st) => ({
                  type: 'Feature',
                  properties: {
                    code: st.code,
                    name: st.name,
                    distance_km: st.distance_km,
                    tracks: st.track_count,
                  },
                  geometry: {
                    type: 'Point',
                    coordinates: st.coordinates,
                  },
                })),
              },
            },
            'railway-trains': {
              type: 'geojson',
              data: {
                type: 'FeatureCollection',
                features: ACTIVE_TRAINS_GIS.map((tr) => ({
                  type: 'Feature',
                  properties: {
                    train_id: tr.train_id,
                    train_number: tr.train_number,
                    name: tr.name,
                    speed: tr.speed_kmh,
                    status: tr.status,
                  },
                  geometry: {
                    type: 'Point',
                    coordinates: tr.coordinates,
                  },
                })),
              },
            },
          },
          layers: [
            {
              id: 'background',
              type: 'background',
              paint: { 'background-color': '#04070D' },
            },
            {
              id: 'base-tiles',
              type: 'raster',
              source: 'osm-tiles',
              minzoom: 0,
              maxzoom: 19,
              paint: {
                'raster-opacity': 0.45,
                'raster-contrast': 0.2,
                'raster-brightness-min': 0.05,
              },
            },
            // Track alignment glow
            {
              id: 'railway-track-glow',
              type: 'line',
              source: 'railway-corridor',
              paint: {
                'line-color': '#2563EB',
                'line-width': 6,
                'line-opacity': 0.35,
                'line-blur': 4,
              },
            },
            // UP Mainline
            {
              id: 'railway-track-line',
              type: 'line',
              source: 'railway-corridor',
              paint: {
                'line-color': [
                  'case',
                  ['==', ['get', 'status'], 'POSSESSION'],
                  '#F59E0B',
                  ['==', ['get', 'status'], 'CAUTION'],
                  '#FBBF24',
                  '#38BDF8',
                ],
                'line-width': 2.5,
              },
            },
            // Station Points
            {
              id: 'stations-circle',
              type: 'circle',
              source: 'railway-stations',
              paint: {
                'circle-radius': 6,
                'circle-color': '#0B101C',
                'circle-stroke-width': 2,
                'circle-stroke-color': '#38BDF8',
              },
            },
            // Train Points
            {
              id: 'trains-circle',
              type: 'circle',
              source: 'railway-trains',
              paint: {
                'circle-radius': 7,
                'circle-color': [
                  'case',
                  ['==', ['get', 'status'], 'HELD_AT_SIGNAL'],
                  '#EF4444',
                  '#2563EB',
                ],
                'circle-stroke-width': 1.5,
                'circle-stroke-color': '#FFFFFF',
              },
            },
          ],
        };

        const map = new maplibre.Map({
          container: mapContainerRef.current,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          style: darkRailwayStyle as any,
          center: [78.78, 27.5], // Center between Delhi & Kanpur
          zoom: 7.2,
          minZoom: 6,
          maxZoom: 16,
        });

        map.on('load', () => {
          if (!isMounted) return;
          setMapLoaded(true);
        });

        // Click listeners on map
        map.on('click', 'railway-track-line', (e) => {
          if (e.features && e.features[0]) {
            const code = e.features[0].properties?.code;
            if (code) onSelectSection?.(code);
          }
        });

        map.on('click', 'trains-circle', (e) => {
          if (e.features && e.features[0]) {
            const trId = e.features[0].properties?.train_id;
            if (trId) onSelectTrain?.(trId);
          }
        });

        map.on('click', 'stations-circle', (e) => {
          if (e.features && e.features[0]) {
            const stCode = e.features[0].properties?.code;
            if (stCode) onSelectStation?.(stCode);
          }
        });

        mapInstanceRef.current = map;

        // Automatically resize map when sidebar collapses or expands
        if (typeof ResizeObserver !== 'undefined' && mapContainerRef.current) {
          resizeObserver = new ResizeObserver(() => {
            map.resize();
          });
          resizeObserver.observe(mapContainerRef.current);
        }
      } catch (err) {
        console.warn('MapLibre WebGL unavailable or failed to initialize, switching to synthetic fallback:', err);
        if (isMounted) setMapError(true);
      }
    }

    initMap();

    return () => {
      isMounted = false;
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      if (mapInstanceRef.current) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (mapInstanceRef.current as any).remove?.();
        mapInstanceRef.current = null;
      }
    };
  }, [useFallbackOverride, mapError, mapTilerKey, onSelectSection, onSelectStation, onSelectTrain]);

  // If map error occurred or user toggled fallback, show the reliable Synthetic vector fallback
  if (mapError || useFallbackOverride) {
    return (
      <div className="relative w-full h-full">
        <RailwayMapFallback
          selectedSectionCode={selectedSectionCode}
          selectedTaskId={selectedTaskId}
          selectedTrainId={selectedTrainId}
          onSelectSection={onSelectSection}
          onSelectTask={onSelectTask}
          onSelectTrain={onSelectTrain}
          onSelectStation={onSelectStation}
          onOpenDigitalTwin={onOpenDigitalTwin}
        />
        {/* Toggle back to MapLibre button */}
        {!mapError && (
          <button
            onClick={() => setUseFallbackOverride(false)}
            className="absolute top-2.5 right-36 z-30 text-[10px] font-mono bg-[#0B101C]/90 text-[#93C5FD] border border-[#2D436D] px-2 py-0.5 rounded hover:bg-[#141F36]"
          >
            Switch to MapLibre
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="relative w-full h-full bg-[#050912] overflow-hidden select-none font-sans flex flex-col border border-[#1E2D4A] rounded-lg">
      {/* Top Map HUD Bar */}
      <div className="h-10 bg-[#0B101C]/90 backdrop-blur-md border-b border-[#1E2D4A] px-3 flex items-center justify-between z-20 shrink-0">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs font-bold text-[#F8FAFC]">
            <Radio className="w-3.5 h-3.5 text-[#3B82F6] animate-pulse" />
            <span>MapLibre Geospatial Engine</span>
          </span>
          <span className="text-[10px] font-mono bg-[#141F36] text-[#93C5FD] px-2 py-0.5 rounded border border-[#2D436D]">
            NDLS → CNB (440 km Trunk)
          </span>
          <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            LIVE MAPLIBRE GL
          </span>
        </div>

        {/* View Switcher: MapLibre vs Synthetic Fallback */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setUseFallbackOverride(true)}
            className="text-[10px] font-mono bg-[#141F36] hover:bg-[#1A2846] text-[#94A3B8] hover:text-white px-2 py-0.5 rounded border border-[#1E2D4A] transition-colors"
          >
            Switch to Schematic
          </button>
        </div>
      </div>

      {/* MapLibre DOM Container */}
      <div className="relative flex-1 w-full h-full overflow-hidden">
        <div ref={mapContainerRef} className="w-full h-full" />

        {/* 3D Digital Twin Quick-Launch Float on Selected Section */}
        {selectedSectionCode && (
          <div className="absolute top-3 right-3 z-30 bg-[#0B101C]/95 backdrop-blur-md border border-[#2563EB] rounded-lg p-2.5 shadow-2xl flex items-center gap-3">
            <div>
              <div className="text-[10px] uppercase font-bold text-[#64748B] tracking-wider">
                Selected Section
              </div>
              <div className="text-xs font-bold text-white font-mono flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#2563EB] animate-pulse" />
                {selectedSectionCode}
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

        {/* Map Legend Overlay */}
        <div className="absolute bottom-3 left-3 z-20 bg-[#0B101C]/90 backdrop-blur-md border border-[#1E2D4A] rounded-md px-3 py-1.5 shadow-lg text-[10px] flex items-center gap-4 text-[#CBD5E1]">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-1 bg-[#38BDF8] rounded" />
            <span>Clear UP Track</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-1 bg-[#F59E0B] rounded" />
            <span>Possession Block</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#38BDF8]" />
            <span>Station</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#2563EB]" />
            <span>Active Train</span>
          </span>
        </div>
      </div>
    </div>
  );
};
