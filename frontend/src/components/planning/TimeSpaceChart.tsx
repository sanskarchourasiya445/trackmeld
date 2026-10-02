'use client';

import React, { useState, useMemo } from 'react';
import { Corridor, TrainMovement, MaintenanceTask } from '@/types/railway';
import { ScheduleResult, ScheduledTaskInterval } from '@/types/planning';
import { Clock, ZoomIn, ZoomOut } from 'lucide-react';
import { Button } from '@/components/ui/button';

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
  const stations = corridor.stations && corridor.stations.length > 0 ? corridor.stations : [
    { code: 'NDLS', name: 'New Delhi', distance_km: 0 },
    { code: 'GZB', name: 'Ghaziabad Jn', distance_km: 26 },
    { code: 'ALJN', name: 'Aligarh Jn', distance_km: 131 },
    { code: 'TDL', name: 'Tundla Jn', distance_km: 209 },
    { code: 'ETW', name: 'Etawah Jn', distance_km: 301 },
    { code: 'CNB', name: 'Kanpur Central', distance_km: 440 },
  ];

  // Chart dimensions
  const svgWidth = 980 * zoomLevel;
  const svgHeight = 490;
  const paddingLeft = 85;
  const paddingRight = 35;
  const paddingTop = 35;
  const paddingBottom = 45;

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
    <div className="flex flex-col h-full bg-[#141418] border border-[#202024] rounded-md overflow-hidden select-none font-mono">
      {/* Header Controls */}
      <div className="h-10 bg-[#18181C] border-b border-[#202024] px-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="w-3.5 h-3.5 text-[#4C87E7]" />
          <span className="text-xs font-semibold text-[#F5F5F5]">
            Corridor Time-Space Diagram
          </span>
          <span className="text-[10px] text-[#71717A] bg-[#202024] px-1.5 py-0.5 rounded">
            NDLS–CNB (440 km) • 72h Horizon
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Day range filters */}
          <div className="flex items-center rounded border border-[#29292F] bg-[#0E0E12] p-0.5 text-[11px]">
            {(['ALL', 'DAY1', 'DAY2', 'DAY3'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setTimeFilter(filter)}
                className={`px-2 py-0.5 rounded ${
                  timeFilter === filter
                    ? 'bg-[#4C87E7] text-white font-semibold'
                    : 'text-[#A1A1AA] hover:text-white'
                }`}
              >
                {filter === 'ALL' ? '72h All' : filter === 'DAY1' ? '10 Oct' : filter === 'DAY2' ? '11 Oct' : '12 Oct'}
              </button>
            ))}
          </div>

          {/* Zoom controls */}
          <div className="flex items-center gap-1 border-l border-[#29292F] pl-2">
            <Button
              variant="outline"
              size="icon-xs"
              onClick={() => setZoomLevel((z) => Math.max(1, z - 0.25))}
              disabled={zoomLevel <= 1}
              className="border-[#29292F] text-[#A1A1AA] hover:text-white"
            >
              <ZoomOut className="w-3 h-3" />
            </Button>
            <span className="text-[10px] text-[#A1A1AA] w-8 text-center">
              {Math.round(zoomLevel * 100)}%
            </span>
            <Button
              variant="outline"
              size="icon-xs"
              onClick={() => setZoomLevel((z) => Math.min(2.5, z + 0.25))}
              disabled={zoomLevel >= 2.5}
              className="border-[#29292F] text-[#A1A1AA] hover:text-white"
            >
              <ZoomIn className="w-3 h-3" />
            </Button>
          </div>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div className="flex-1 overflow-auto bg-[#0A0A0A] relative">
        <svg
          width={svgWidth}
          height={svgHeight}
          className="min-w-full text-[10px]"
        >
          <defs>
            <pattern
              id="possessionHatch"
              width="6"
              height="6"
              patternTransform="rotate(45 0 0)"
              patternUnits="userSpaceOnUse"
            >
              <line x1="0" y1="0" x2="0" y2="6" stroke="#4C87E7" strokeWidth="1.5" strokeOpacity="0.45" />
            </pattern>
            <pattern
              id="conflictHatch"
              width="6"
              height="6"
              patternTransform="rotate(45 0 0)"
              patternUnits="userSpaceOnUse"
            >
              <line x1="0" y1="0" x2="0" y2="6" stroke="#F06464" strokeWidth="1.5" strokeOpacity="0.5" />
            </pattern>
          </defs>

          {/* Grid: Station Distance Lines & Clickable Stations */}
          {stations.map((st) => {
            const y = getYForKm(st.distance_km);
            return (
              <g key={st.code} className="cursor-pointer" onClick={() => onSelectSection?.(st.code)}>
                <line
                  x1={paddingLeft}
                  y1={y}
                  x2={svgWidth - paddingRight}
                  y2={y}
                  stroke="#202024"
                  strokeWidth="1"
                  strokeDasharray="2 3"
                />
                <text
                  x={paddingLeft - 8}
                  y={y + 3}
                  textAnchor="end"
                  fill="#A1A1AA"
                  fontSize="10"
                  fontWeight="600"
                >
                  {st.code}
                </text>
                <text
                  x={paddingLeft - 44}
                  y={y + 3}
                  textAnchor="end"
                  fill="#71717A"
                  fontSize="8"
                >
                  {st.distance_km}km
                </text>
              </g>
            );
          })}

          {/* Grid: Vertical Time Grid Lines */}
          {Array.from({ length: Math.floor(totalFilteredHours / (totalFilteredHours > 24 ? 6 : 2)) + 1 }).map((_, i) => {
            const step = totalFilteredHours > 24 ? 6 : 2;
            const hourOffset = startHourOffset + i * step;
            if (hourOffset > endHourOffset) return null;
            const x = getXForHourOffset(hourOffset);
            const dayNum = Math.floor(hourOffset / 24) + 10;
            const hourInDay = hourOffset % 24;

            return (
              <g key={hourOffset}>
                <line
                  x1={x}
                  y1={paddingTop}
                  x2={x}
                  y2={svgHeight - paddingBottom}
                  stroke="#18181C"
                  strokeWidth="1"
                />
                <text
                  x={x}
                  y={svgHeight - paddingBottom + 16}
                  textAnchor="middle"
                  fill="#71717A"
                  fontSize="9"
                >
                  {String(hourInDay).padStart(2, '0')}:00
                </text>
                {hourInDay === 0 && (
                  <text
                    x={x + 16}
                    y={svgHeight - paddingBottom + 28}
                    textAnchor="middle"
                    fill="#4C87E7"
                    fontSize="8"
                    fontWeight="700"
                  >
                    {dayNum} Oct
                  </text>
                )}
              </g>
            );
          })}

          {/* 1. Maintenance Possession Intervals */}
          {tasks.map((task) => {
            const scheduled = scheduledMap.get(task.task_id);
            const isSelected = selectedTaskId === task.task_id;
            const secCode = task.section_code || task.section_id || '';
            const isSectionActive = selectedSectionCode && secCode.includes(selectedSectionCode);

            // Derive Y bounds based on section
            let yTop = paddingTop + 10;
            let yBottom = yTop + 45;

            if (secCode.includes('NDLS') || secCode.includes('GZB')) {
              yTop = getYForStation('NDLS');
              yBottom = getYForStation('GZB');
            } else if (secCode.includes('GZB') || secCode.includes('ALJN')) {
              yTop = getYForStation('GZB');
              yBottom = getYForStation('ALJN');
            } else if (secCode.includes('ALJN') || secCode.includes('TDL')) {
              yTop = getYForStation('ALJN');
              yBottom = getYForStation('TDL');
            } else if (secCode.includes('TDL') || secCode.includes('ETW')) {
              yTop = getYForStation('TDL');
              yBottom = getYForStation('ETW');
            } else if (secCode.includes('ETW') || secCode.includes('CNB')) {
              yTop = getYForStation('ETW');
              yBottom = getYForStation('CNB');
            }

            const blockHeight = Math.max(16, yBottom - yTop);

            if (scheduled) {
              const startIso = scheduled.interval?.start || scheduled.start_time;
              const endIso = scheduled.interval?.end || scheduled.end_time;
              const xStart = getXForTime(startIso);
              const xEnd = getXForTime(endIso);
              const blockWidth = Math.max(22, xEnd - xStart);
              const isShadow = (scheduled.shadow_possession_with?.length ?? 0) > 0;

              return (
                <g
                  key={task.task_id}
                  onClick={() => onSelectTask?.(task.task_id)}
                  onMouseEnter={() => setHoveredEntity(`Possession: ${task.task_code || task.task_id}`)}
                  onMouseLeave={() => setHoveredEntity(null)}
                  className="cursor-pointer transition-all"
                >
                  <rect
                    x={xStart}
                    y={yTop}
                    width={blockWidth}
                    height={blockHeight}
                    fill={isSelected ? '#4C87E7' : isSectionActive ? '#3B82F6' : isShadow ? '#35B779' : '#1E1E24'}
                    fillOpacity={isSelected ? 0.45 : isSectionActive ? 0.35 : isShadow ? 0.3 : 0.65}
                    stroke={isSelected ? '#3B82F6' : isSectionActive ? '#60A5FA' : isShadow ? '#35B779' : '#4C87E7'}
                    strokeWidth={isSelected ? 2.5 : isSectionActive ? 2 : 1.2}
                    rx="3"
                  />
                  <rect
                    x={xStart}
                    y={yTop}
                    width={blockWidth}
                    height={blockHeight}
                    fill="url(#possessionHatch)"
                    rx="3"
                  />
                  <text
                    x={xStart + 3}
                    y={yTop + 12}
                    fill={isSelected ? '#FFFFFF' : '#F5F5F5'}
                    fontSize="8.5"
                    fontWeight="700"
                  >
                    {task.task_code || task.task_id}
                  </text>
                  {isShadow && (
                    <text
                      x={xStart + 3}
                      y={yTop + 22}
                      fill="#35B779"
                      fontSize="7.5"
                      fontWeight="600"
                    >
                      [BUNDLED]
                    </text>
                  )}
                </g>
              );
            } else {
              // Unscheduled Task
              const startIso = task.earliest_start || task.window_start;
              const endIso = task.latest_finish || task.window_end;
              const xStart = getXForTime(startIso);
              const xEnd = getXForTime(endIso);
              const blockWidth = Math.max(22, xEnd - xStart);

              return (
                <g
                  key={task.task_id}
                  onClick={() => onSelectTask?.(task.task_id)}
                  onMouseEnter={() => setHoveredEntity(`Unscheduled: ${task.task_code || task.task_id}`)}
                  onMouseLeave={() => setHoveredEntity(null)}
                  className="cursor-pointer"
                >
                  <rect
                    x={xStart}
                    y={yTop}
                    width={blockWidth}
                    height={blockHeight}
                    fill="#F06464"
                    fillOpacity={isSelected ? 0.35 : 0.15}
                    stroke="#F06464"
                    strokeWidth={isSelected ? 2.5 : 1.2}
                    strokeDasharray="4 3"
                    rx="3"
                  />
                  <rect
                    x={xStart}
                    y={yTop}
                    width={blockWidth}
                    height={blockHeight}
                    fill="url(#conflictHatch)"
                    rx="3"
                  />
                  <text
                    x={xStart + 3}
                    y={yTop + 12}
                    fill="#F06464"
                    fontSize="8.5"
                    fontWeight="700"
                  >
                    {task.task_code || task.task_id} (UNPLACED)
                  </text>
                </g>
              );
            }
          })}

          {/* 2. Train Trajectory Slopes */}
          {trains.map((train, idx) => {
            const trainId = train.train_id || train.movement_id || `TRN-${idx}`;
            const isSelected = selectedTrainId === trainId;

            // Parse entry and exit points
            let entryIso = train.entry_time;
            let exitIso = train.exit_time;
            const entryStation = train.entry_station || (train.direction === 'DOWN' ? 'CNB' : 'NDLS');
            const exitStation = train.exit_station || (train.direction === 'DOWN' ? 'NDLS' : 'CNB');

            if (!entryIso && train.scheduled_arrival) {
              const day = 10 + (train.day_offset || 0);
              entryIso = `2026-10-${day}T${train.scheduled_arrival}:00Z`;
            }
            if (!exitIso && train.scheduled_departure) {
              const day = 10 + (train.day_offset || 0);
              exitIso = `2026-10-${day}T${train.scheduled_departure}:00Z`;
            }

            const x1 = getXForTime(entryIso);
            const y1 = getYForStation(entryStation);
            const x2 = exitIso ? getXForTime(exitIso) : x1 + 80;
            const y2 = getYForStation(exitStation);

            const isHighPriority = train.priority_tier === 1;
            const isFreight = (train.priority_tier ?? 4) >= 4;

            // Check if train trajectory intersects selected task window
            const trainStartMs = new Date(entryIso || '').getTime();
            const trainEndMs = new Date(exitIso || '').getTime();
            const isIntersectsSelectedTask =
              selectedTaskWindow &&
              !isNaN(trainStartMs) &&
              !isNaN(trainEndMs) &&
              trainStartMs <= selectedTaskWindow.end &&
              trainEndMs >= selectedTaskWindow.start;

            const strokeColor = isSelected
              ? '#F4B740'
              : isIntersectsSelectedTask
              ? '#60A5FA'
              : isHighPriority
              ? '#4C87E7'
              : isFreight
              ? '#71717A'
              : '#A1A1AA';

            const strokeWidth = isSelected ? 3.5 : isIntersectsSelectedTask ? 2.5 : isHighPriority ? 1.8 : 1.2;
            const strokeDash = isFreight ? '4 3' : 'none';

            return (
              <g
                key={trainId}
                onClick={() => onSelectTrain?.(trainId)}
                onMouseEnter={() => setHoveredEntity(`Train: ${train.train_number} (${train.train_name})`)}
                onMouseLeave={() => setHoveredEntity(null)}
                className="cursor-pointer group"
              >
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke="transparent"
                  strokeWidth="10"
                />
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={strokeColor}
                  strokeWidth={strokeWidth}
                  strokeDasharray={strokeDash}
                  strokeOpacity={isSelected || isIntersectsSelectedTask ? 1 : 0.8}
                />
                <text
                  x={x1 + (x2 - x1) * 0.45}
                  y={y1 + (y2 - y1) * 0.45 - 3}
                  fill={strokeColor}
                  fontSize="7.5"
                  fontWeight="600"
                  className="select-none"
                >
                  {train.train_number}
                </text>
              </g>
            );
          })}
        </svg>

        {hoveredEntity && (
          <div className="absolute top-2 right-2 bg-[#18181C]/90 border border-[#29292F] px-2 py-1 rounded text-[10px] text-[#F5F5F5] backdrop-blur-xs pointer-events-none">
            Focus: <span className="font-bold text-[#4C87E7]">{hoveredEntity}</span>
          </div>
        )}
      </div>

      {/* Legend Footer */}
      <div className="h-8 bg-[#141418] border-t border-[#202024] px-3 flex items-center justify-between text-[10px] text-[#A1A1AA]">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="w-3 h-2 bg-[#4C87E7]/40 border border-[#4C87E7] rounded-xs inline-block"></span>
            <span>Scheduled Possession</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-2 bg-[#35B779]/40 border border-[#35B779] rounded-xs inline-block"></span>
            <span>Shadow Bundled</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-2 bg-[#F06464]/30 border border-[#F06464] border-dashed rounded-xs inline-block"></span>
            <span>Unscheduled</span>
          </span>
        </div>

        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="w-4 h-0.5 bg-[#4C87E7] inline-block"></span>
            <span>Tier-1 Express</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-4 h-0.5 bg-[#71717A] border-b border-dashed border-[#71717A] inline-block"></span>
            <span>Freight Path</span>
          </span>
        </div>
      </div>
    </div>
  );
};
