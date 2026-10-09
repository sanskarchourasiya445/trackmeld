'use client';

import React, { useState, useMemo } from 'react';
import { Corridor, TrainMovement, MaintenanceTask } from '@/types/railway';
import { ScheduleResult, ScheduledTaskInterval } from '@/types/planning';
import { Clock, ZoomIn, ZoomOut, Layers, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getTrainOccurrenceKey } from '@/lib/railway/identity';

interface TimeSpaceChartProps {
  corridor: Corridor;
  trains: TrainMovement[];
  tasks: MaintenanceTask[];
  scheduleResult?: ScheduleResult | null;
  selectedTaskId?: string | null;
  selectedTrainId?: string | null;
  selectedSectionCode?: string | null;
  onSelectTask?: (taskId: string) => void;
  onSelectTrain?: (trainId: string) => void;
  onSelectSection?: (sectionCode: string) => void;
}

export const TimeSpaceChart: React.FC<TimeSpaceChartProps> = ({
  corridor,
  trains,
  tasks,
  scheduleResult,
  selectedTaskId,
  selectedTrainId,
  selectedSectionCode,
  onSelectTask,
  onSelectTrain,
  onSelectSection,
}) => {
  const [timeFilter, setTimeFilter] = useState<'ALL' | 'DAY1' | 'DAY2' | 'DAY3'>('ALL');
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [hoveredEntity, setHoveredEntity] = useState<string | null>(null);

  // Corridor station markers
  const maxDistance = corridor.total_length_km || 440;
  const stations =
    corridor.stations && corridor.stations.length > 0
      ? corridor.stations
      : [
          { code: 'NDLS', name: 'New Delhi', distance_km: 0 },
          { code: 'GZB', name: 'Ghaziabad Jn', distance_km: 26 },
          { code: 'ALJN', name: 'Aligarh Jn', distance_km: 131 },
          { code: 'TDL', name: 'Tundla Jn', distance_km: 209 },
          { code: 'ETW', name: 'Etawah Jn', distance_km: 301 },
          { code: 'CNB', name: 'Kanpur Central', distance_km: 440 },
        ];

  // Chart dimensions
  const svgWidth = 1100 * zoomLevel;
  const svgHeight = 560;
  const paddingLeft = 95;
  const paddingRight = 40;
  const paddingTop = 40;
  const paddingBottom = 50;

  const chartAreaWidth = svgWidth - paddingLeft - paddingRight;
  const chartAreaHeight = svgHeight - paddingTop - paddingBottom;

  // Station km mapping to Y coordinate
  const getYForKm = (km: number) => {
    return paddingTop + (Math.min(maxDistance, Math.max(0, km)) / maxDistance) * chartAreaHeight;
  };

  const getYForStation = (stationCode: string) => {
    const st = stations.find((s) => s.code === stationCode || s.name === stationCode);
    if (!st) return paddingTop + chartAreaHeight / 2;
    return getYForKm(st.distance_km);
  };

  // Base planning horizon: 2026-10-10 00:00 UTC to 2026-10-12 23:59 UTC
  const horizonStartMs = useMemo(() => new Date('2026-10-10T00:00:00Z').getTime(), []);

  const [startHourOffset, endHourOffset] = useMemo(() => {
    switch (timeFilter) {
      case 'DAY1':
        return [0, 24];
      case 'DAY2':
        return [24, 48];
      case 'DAY3':
        return [48, 72];
      default:
        return [0, 72];
    }
  }, [timeFilter]);

  const totalFilteredHours = endHourOffset - startHourOffset;

  // Convert ISO string or timestamp to X coordinate
  const getXForTime = (timeIso?: string | null): number => {
    if (!timeIso) return paddingLeft;
    let tMs = new Date(timeIso).getTime();
    if (isNaN(tMs)) {
      const parts = timeIso.split(':');
      if (parts.length === 2) {
        const h = parseInt(parts[0], 10);
        const m = parseInt(parts[1], 10);
        tMs = horizonStartMs + (h * 3600 + m * 60) * 1000;
      } else {
        return paddingLeft;
      }
    }

    const hoursFromStart = (tMs - horizonStartMs) / (1000 * 3600);
    const clamped = Math.max(startHourOffset, Math.min(endHourOffset, hoursFromStart));
    return paddingLeft + ((clamped - startHourOffset) / totalFilteredHours) * chartAreaWidth;
  };

  const getXForHourOffset = (hourOffset: number) => {
    return paddingLeft + ((hourOffset - startHourOffset) / totalFilteredHours) * chartAreaWidth;
  };

  // Map scheduled tasks by ID
  const scheduledMap = useMemo(() => {
    const map = new Map<string, ScheduledTaskInterval>();
    scheduleResult?.scheduled_tasks.forEach((st) => {
      map.set(st.task_id, st);
    });
    return map;
  }, [scheduleResult]);

  // Selected task interval bounds for highlighting intersecting train paths
  const selectedTaskWindow = useMemo(() => {
    if (!selectedTaskId) return null;
    const scheduled = scheduledMap.get(selectedTaskId);
    if (scheduled) {
      const s = scheduled.interval?.start || scheduled.start_time;
      const e = scheduled.interval?.end || scheduled.end_time;
      return { start: new Date(s || '').getTime(), end: new Date(e || '').getTime() };
    }
    const unplaced = tasks.find((t) => t.task_id === selectedTaskId);
    if (unplaced) {
      const s = unplaced.earliest_start || unplaced.window_start;
      const e = unplaced.latest_finish || unplaced.window_end;
      return { start: new Date(s || '').getTime(), end: new Date(e || '').getTime() };
    }
    return null;
  }, [selectedTaskId, scheduledMap, tasks]);

  return (
    <div className="flex flex-col h-full bg-[#0B101C] border border-[#1E2D4A] rounded-xl overflow-hidden select-none font-sans text-xs">
      {/* 1. Header Controls */}
      <div className="h-12 bg-[#0F172A] border-b border-[#1E2D4A] px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <Clock className="w-4 h-4 text-[#38BDF8]" />
          <span className="text-xs font-bold text-[#F8FAFC]">
            Corridor Time-Space Diagram
          </span>
          <span className="text-[10px] font-mono text-[#94A3B8] bg-[#141F36] border border-[#1E2D4A] px-2 py-0.5 rounded">
            NDLS–CNB (440 km) • 72h Horizon
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Day range filters */}
          <div className="flex items-center rounded-md border border-[#1E2D4A] bg-[#0A0E17] p-0.5 text-xs font-mono">
            {(['ALL', 'DAY1', 'DAY2', 'DAY3'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setTimeFilter(filter)}
                className={`px-2.5 py-1 rounded transition-colors ${
                  timeFilter === filter
                    ? 'bg-[#2563EB] text-white font-semibold'
                    : 'text-[#94A3B8] hover:text-[#F8FAFC]'
                }`}
              >
                {filter === 'ALL' ? '72h All' : filter === 'DAY1' ? '10 Oct' : filter === 'DAY2' ? '11 Oct' : '12 Oct'}
              </button>
            ))}
          </div>

          {/* Zoom controls */}
          <div className="flex items-center gap-1.5 border-l border-[#1E2D4A] pl-3">
            <Button
              variant="outline"
              size="icon-xs"
              onClick={() => setZoomLevel((z) => Math.max(1, z - 0.25))}
              disabled={zoomLevel <= 1}
              className="border-[#1E2D4A] text-[#94A3B8] hover:text-white h-7 w-7"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </Button>
            <span className="text-[10px] font-mono text-[#94A3B8] w-9 text-center">
              {Math.round(zoomLevel * 100)}%
            </span>
            <Button
              variant="outline"
              size="icon-xs"
              onClick={() => setZoomLevel((z) => Math.min(2.5, z + 0.25))}
              disabled={zoomLevel >= 2.5}
              className="border-[#1E2D4A] text-[#94A3B8] hover:text-white h-7 w-7"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </div>

      {/* 2. SVG Canvas Area */}
      <div className="flex-1 overflow-auto bg-[#04070D] relative">
        <svg width={svgWidth} height={svgHeight} className="min-w-full text-[10px] font-mono">
          <defs>
            <pattern
              id="possessionHatch"
              width="6"
              height="6"
              patternTransform="rotate(45 0 0)"
              patternUnits="userSpaceOnUse"
            >
              <line x1="0" y1="0" x2="0" y2="6" stroke="#38BDF8" strokeWidth="1.5" strokeOpacity="0.45" />
            </pattern>
            <pattern
              id="conflictHatch"
              width="6"
              height="6"
              patternTransform="rotate(45 0 0)"
              patternUnits="userSpaceOnUse"
            >
              <line x1="0" y1="0" x2="0" y2="6" stroke="#EF4444" strokeWidth="1.5" strokeOpacity="0.5" />
            </pattern>
          </defs>

          {/* Grid: Station horizontal baseline rules */}
          {stations.map((st) => {
            const y = getYForKm(st.distance_km);
            const isSelected = selectedSectionCode?.includes(st.code);
            return (
              <g key={st.code}>
                <line
                  x1={paddingLeft}
                  y1={y}
                  x2={svgWidth - paddingRight}
                  y2={y}
                  stroke={isSelected ? '#38BDF8' : '#172338'}
                  strokeWidth={isSelected ? 1.5 : 0.8}
                  strokeDasharray={st.distance_km === 0 || st.distance_km === maxDistance ? 'none' : '3 3'}
                />
                <text
                  x={paddingLeft - 10}
                  y={y + 3.5}
                  textAnchor="end"
                  fill={isSelected ? '#38BDF8' : '#94A3B8'}
                  fontSize="9.5"
                  fontWeight={isSelected ? '700' : '500'}
                  className="select-none font-sans"
                >
                  {st.name}
                </text>
                <text
                  x={svgWidth - paddingRight + 8}
                  y={y + 3.5}
                  textAnchor="start"
                  fill="#64748B"
                  fontSize="8.5"
                  className="select-none"
                >
                  km {st.distance_km}
                </text>
              </g>
            );
          })}

          {/* Grid: Time vertical columns */}
          {Array.from({ length: totalFilteredHours + 1 }).map((_, i) => {
            const h = startHourOffset + i;
            if (h % 3 !== 0 && zoomLevel < 1.5) return null;
            if (h % 2 !== 0 && zoomLevel < 2) return null;
            const x = getXForHourOffset(h);
            const isDayBoundary = h % 24 === 0;

            return (
              <g key={`time-${h}`}>
                <line
                  x1={x}
                  y1={paddingTop}
                  x2={x}
                  y2={paddingTop + chartAreaHeight}
                  stroke={isDayBoundary ? '#2D436D' : '#121D30'}
                  strokeWidth={isDayBoundary ? 1.5 : 0.6}
                />
                <text
                  x={x}
                  y={paddingTop + chartAreaHeight + 18}
                  textAnchor="middle"
                  fill={isDayBoundary ? '#F8FAFC' : '#64748B'}
                  fontSize="9"
                  fontWeight={isDayBoundary ? '700' : '400'}
                  className="select-none"
                >
                  {String(h % 24).padStart(2, '0')}:00
                </text>
                {isDayBoundary && (
                  <text
                    x={x + 4}
                    y={paddingTop - 12}
                    fill="#38BDF8"
                    fontSize="9"
                    fontWeight="700"
                    className="select-none"
                  >
                    Day {Math.floor(h / 24) + 1}
                  </text>
                )}
              </g>
            );
          })}

          {/* Planned Possession Blocks */}
          {tasks.map((task) => {
            const scheduled = scheduledMap.get(task.task_id);
            const isScheduled = !!scheduled;
            const isSelected = selectedTaskId === task.task_id;

            const startIso = scheduled?.interval?.start || scheduled?.start_time || task.earliest_start || task.window_start;
            const endIso = scheduled?.interval?.end || scheduled?.end_time || task.latest_finish || task.window_end;

            const xStart = getXForTime(startIso);
            const xEnd = getXForTime(endIso);
            const blockWidth = Math.max(12, xEnd - xStart);

            const yTop = getYForKm(task.from_km || 140);
            const yBottom = getYForKm(task.to_km || 200);
            const blockHeight = Math.max(10, Math.abs(yBottom - yTop));
            const yPos = Math.min(yTop, yBottom);

            const isConflict = !isScheduled && task.task_id === 'TSK-0007';

            return (
              <g
                key={`task-block-${task.task_id}`}
                onClick={() => onSelectTask?.(task.task_id)}
                onMouseEnter={() => setHoveredEntity(`Possession: ${task.title} (${task.task_id})`)}
                onMouseLeave={() => setHoveredEntity(null)}
                className="cursor-pointer group"
              >
                <rect
                  x={xStart}
                  y={yPos}
                  width={blockWidth}
                  height={blockHeight}
                  fill={
                    isConflict
                      ? 'url(#conflictHatch)'
                      : isScheduled
                      ? 'url(#possessionHatch)'
                      : 'rgba(239, 68, 68, 0.15)'
                  }
                  stroke={
                    isSelected
                      ? '#F59E0B'
                      : isConflict
                      ? '#EF4444'
                      : isScheduled
                      ? '#38BDF8'
                      : '#94A3B8'
                  }
                  strokeWidth={isSelected ? 2 : 1}
                  rx="3"
                  className="transition-all"
                />
                <text
                  x={xStart + 4}
                  y={yPos + 12}
                  fill={isConflict ? '#FCA5A5' : '#F8FAFC'}
                  fontSize="8.5"
                  fontWeight="600"
                  className="select-none pointer-events-none"
                >
                  {task.task_code || task.task_id}
                </text>
              </g>
            );
          })}

          {/* Train Trajectory Stringlines */}
          {trains.map((train, idx) => {
            const occurrenceKey = getTrainOccurrenceKey(train, idx);
            const trainServiceId = train.train_id;
            const isSelected = selectedTrainId === train.movement_id || selectedTrainId === trainServiceId;
            const isHighPriority = train.priority_tier === 1;
            const isFreight = train.train_name?.toLowerCase().includes('freight');
            const entryIso = train.entry_time || train.scheduled_departure || (train as any).route_entry_time || (train as any).origin_departure;
            const exitIso = train.exit_time || train.scheduled_arrival || (train as any).route_exit_time || (train as any).destination_arrival;

            const isDown = train.direction === 'DOWN';
            const x1 = getXForTime(entryIso);
            const y1 = isDown ? getYForKm(0) : getYForKm(maxDistance);
            const x2 = getXForTime(exitIso);
            const y2 = isDown ? getYForKm(maxDistance) : getYForKm(0);

            const trainStartMs = new Date(entryIso || '').getTime();
            const trainEndMs = new Date(exitIso || '').getTime();
            const isIntersectsSelectedTask =
              selectedTaskWindow &&
              !isNaN(trainStartMs) &&
              !isNaN(trainEndMs) &&
              trainStartMs <= selectedTaskWindow.end &&
              trainEndMs >= selectedTaskWindow.start;

            const strokeColor = isSelected
              ? '#F59E0B'
              : isIntersectsSelectedTask
              ? '#38BDF8'
              : isHighPriority
              ? '#2563EB'
              : isFreight
              ? '#64748B'
              : '#94A3B8';

            const strokeWidth = isSelected ? 3.5 : isIntersectsSelectedTask ? 2.5 : isHighPriority ? 1.8 : 1.2;
            const strokeDash = isFreight ? '4 3' : 'none';

            return (
              <g
                key={occurrenceKey}
                onClick={() => onSelectTrain?.(train.movement_id || trainServiceId)}
                onMouseEnter={() => setHoveredEntity(`Train: ${train.train_number} (${train.train_name})`)}
                onMouseLeave={() => setHoveredEntity(null)}
                className="cursor-pointer group"
              >
                <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="transparent" strokeWidth="10" />
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                  strokeDasharray={strokeDash}
                  strokeOpacity={isSelected || isIntersectsSelectedTask ? 1 : 0.85}
                />
                <text
                  x={x1 + (x2 - x1) * 0.45}
                  y={y1 + (y2 - y1) * 0.45 - 4}
                  fill={strokeColor}
                  fontSize="8"
                  fontWeight="700"
                  className="select-none"
                >
                  {train.train_number}
                </text>
              </g>
            );
          })}
        </svg>

        {hoveredEntity && (
          <div className="absolute top-3 right-3 bg-[#0B101C]/95 border border-[#1E2D4A] px-3 py-1.5 rounded-md text-xs text-[#F8FAFC] backdrop-blur-md shadow-md pointer-events-none font-sans">
            Focus: <span className="font-bold text-[#38BDF8] ml-1">{hoveredEntity}</span>
          </div>
        )}
      </div>

      {/* 3. Legend Footer */}
      <div className="h-9 bg-[#0F172A] border-t border-[#1E2D4A] px-4 flex items-center justify-between text-[11px] text-[#94A3B8]">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-3.5 h-2 bg-[#38BDF8]/40 border border-[#38BDF8] rounded-xs inline-block"></span>
            <span>Scheduled Possession</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3.5 h-2 bg-emerald-500/40 border border-emerald-500 rounded-xs inline-block"></span>
            <span>Shadow Bundled</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3.5 h-2 bg-rose-500/30 border border-rose-500 border-dashed rounded-xs inline-block"></span>
            <span>Unscheduled / Conflict</span>
          </span>
        </div>

        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 bg-[#2563EB] inline-block"></span>
            <span>Tier-1 Express</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 border-b border-dashed border-[#64748B] inline-block"></span>
            <span>Freight Path</span>
          </span>
        </div>
      </div>
    </div>
  );
};
