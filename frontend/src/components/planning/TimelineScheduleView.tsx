'use client';

import React, { useState } from 'react';
import { Corridor, TrainMovement, MaintenanceTask } from '@/types/railway';
import { ScheduleResult } from '@/types/planning';
import { Clock, ZoomIn, ZoomOut } from 'lucide-react';

interface TimelineScheduleViewProps {
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

export const TimelineScheduleView: React.FC<TimelineScheduleViewProps> = ({
  trains,
  tasks,
  scheduleResult,
  selectedTaskId,
  selectedTrainId,
  selectedSectionCode,
  onSelectTask,
  onSelectTrain,
}) => {
  const [activeDay, setActiveDay] = useState<'DAY1' | 'DAY2' | 'DAY3'>('DAY1');
  const [zoom, setZoom] = useState(1);
  const [hovered, setHovered] = useState<string | null>(null);

  // 24 hour markers
  const hours = [0, 4, 8, 12, 16, 20, 24];

  // Convert time string to percentage of 24h day
  const getPercentForTime = (iso?: string | null, fallbackH: number = 8): number => {
    if (!iso) return (fallbackH / 24) * 100;
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) {
        const parts = iso.split(':');
        if (parts.length >= 2) {
          const h = parseInt(parts[0], 10);
          const m = parseInt(parts[1], 10);
          return ((h + m / 60) / 24) * 100;
        }
        return (fallbackH / 24) * 100;
      }
      const h = d.getUTCHours();
      const m = d.getUTCMinutes();
      return ((h + m / 60) / 24) * 100;
    } catch {
      return (fallbackH / 24) * 100;
    }
  };

  const scheduledMap = new Map();
  scheduleResult?.scheduled_tasks.forEach((st) => scheduledMap.set(st.task_id, st));

  return (
    <div className="flex flex-col h-full bg-[#0F172A] border border-[#1E2D4A] rounded-lg overflow-hidden select-none font-sans text-xs">
      {/* Header Bar */}
      <div className="h-10 bg-[#141F36] border-b border-[#1E2D4A] px-3.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Clock className="w-3.5 h-3.5 text-[#2563EB]" />
          <span className="font-semibold text-[#F8FAFC]">Timeline / Time-Space Schedule</span>
          <span className="text-[10px] text-[#64748B] bg-[#0A0E17] border border-[#1E2D4A] px-2 py-0.5 rounded font-mono">
            24h Synchronized Axis
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Day Selector */}
          <div className="flex items-center bg-[#0A0E17] border border-[#1E2D4A] rounded p-0.5 text-[11px] font-medium">
            <button
              onClick={() => setActiveDay('DAY1')}
              className={`px-2 py-0.5 rounded transition-colors ${
                activeDay === 'DAY1' ? 'bg-[#2563EB] text-white' : 'text-[#94A3B8] hover:text-[#F8FAFC]'
              }`}
            >
              10 Oct
            </button>
            <button
              onClick={() => setActiveDay('DAY2')}
              className={`px-2 py-0.5 rounded transition-colors ${
                activeDay === 'DAY2' ? 'bg-[#2563EB] text-white' : 'text-[#94A3B8] hover:text-[#F8FAFC]'
              }`}
            >
              11 Oct
            </button>
            <button
              onClick={() => setActiveDay('DAY3')}
              className={`px-2 py-0.5 rounded transition-colors ${
                activeDay === 'DAY3' ? 'bg-[#2563EB] text-white' : 'text-[#94A3B8] hover:text-[#F8FAFC]'
              }`}
            >
              12 Oct
            </button>
          </div>

          {/* Zoom */}
          <div className="flex items-center gap-1 border-l border-[#1E2D4A] pl-2">
            <button
              onClick={() => setZoom((z) => Math.max(1, z - 0.25))}
              disabled={zoom <= 1}
              className="p-1 text-[#94A3B8] hover:text-white disabled:opacity-30 rounded hover:bg-[#1E2D4A]"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="text-[10px] font-mono text-[#94A3B8] w-7 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={() => setZoom((z) => Math.min(2, z + 0.25))}
              disabled={zoom >= 2}
              className="p-1 text-[#94A3B8] hover:text-white disabled:opacity-30 rounded hover:bg-[#1E2D4A]"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Diagram Area */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden p-3 relative flex flex-col justify-between">
        <div style={{ width: `${100 * zoom}%`, minWidth: '100%' }} className="h-full flex flex-col justify-between">
          {/* Time Axis Bar */}
          <div className="relative h-6 border-b border-[#1E2D4A] flex items-center shrink-0">
            {hours.map((hour) => {
              const leftPct = (hour / 24) * 100;
              return (
                <div
                  key={hour}
                  className="absolute -translate-x-1/2 flex flex-col items-center"
                  style={{ left: `${leftPct}%` }}
                >
                  <span className="text-[10px] font-mono text-[#64748B]">
                    {String(hour).padStart(2, '0')}:00
                  </span>
                  <div className="w-[1px] h-1.5 bg-[#334155] mt-0.5" />
                </div>
              );
            })}
          </div>

          {/* Timeline Grid Rows */}
          <div className="flex-1 flex flex-col justify-around py-2 relative">
            {/* Vertical grid lines */}
            {hours.map((hour) => {
              const leftPct = (hour / 24) * 100;
              return (
                <div
                  key={`grid-${hour}`}
                  className="absolute top-0 bottom-0 w-[1px] bg-[#1E2D4A]/50 pointer-events-none -translate-x-1/2"
                  style={{ left: `${leftPct}%` }}
                />
              );
            })}

            {/* Row 1: TRAINS */}
            <div className="relative h-9 bg-[#0A0E17]/60 border border-[#1E2D4A] rounded flex items-center px-2">
              <span className="w-14 text-[10px] font-semibold uppercase tracking-wider text-[#94A3B8] shrink-0">
                Trains
              </span>
              <div className="relative flex-1 h-6">
                {trains.map((train, idx) => {
                  const startPct = getPercentForTime(train.entry_time, 4 + idx * 3.5);
                  const endPct = Math.min(100, getPercentForTime(train.exit_time, 8 + idx * 3.5));
                  const widthPct = Math.max(4, endPct - startPct);
                  const trainId = train.train_id || `TR-${idx}`;
                  const isSelected = selectedTrainId === trainId;
                  const isExpress = train.priority_tier === 1;

                  return (
                    <div
                      key={trainId}
                      onClick={() => onSelectTrain?.(trainId)}
                      onMouseEnter={() => setHovered(`Train ${train.train_number} (${train.train_name})`)}
                      onMouseLeave={() => setHovered(null)}
                      style={{ left: `${startPct}%`, width: `${widthPct}%` }}
                      className={`absolute top-0.5 h-5 rounded cursor-pointer transition-all flex items-center px-1.5 truncate text-[9px] font-mono font-medium ${
                        isSelected
                          ? 'bg-[#2563EB] text-white ring-2 ring-[#60A5FA] z-20'
                          : isExpress
                          ? 'bg-[#1E3A8A]/90 text-[#93C5FD] border border-[#2563EB]/60 hover:bg-[#2563EB]/40'
                          : 'bg-[#1E293B] text-[#94A3B8] border border-[#334155] hover:bg-[#334155]'
                      }`}
                    >
                      <span className="truncate">{train.train_number}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Row 2: TASKS */}
            <div className="relative h-9 bg-[#0A0E17]/60 border border-[#1E2D4A] rounded flex items-center px-2">
              <span className="w-14 text-[10px] font-semibold uppercase tracking-wider text-[#94A3B8] shrink-0">
                Tasks
              </span>
              <div className="relative flex-1 h-6">
                {tasks.map((task, idx) => {
                  const scheduled = scheduledMap.get(task.task_id);
                  const isScheduled = !!scheduled;
                  const isSelected = selectedTaskId === task.task_id;
                  const startPct = isScheduled
                    ? getPercentForTime(scheduled.interval?.start || scheduled.start_time, 6 + idx * 2)
                    : getPercentForTime(task.earliest_start || task.window_start, 10 + idx * 1.5);
                  const endPct = isScheduled
                    ? getPercentForTime(scheduled.interval?.end || scheduled.end_time, 9 + idx * 2)
                    : getPercentForTime(task.latest_finish || task.window_end, 14 + idx * 1.5);
                  const widthPct = Math.max(5, endPct - startPct);

                  return (
                    <div
                      key={task.task_id}
                      onClick={() => onSelectTask?.(task.task_id)}
                      onMouseEnter={() =>
                        setHovered(`Task ${task.task_code || task.task_id}: ${task.title}`)
                      }
                      onMouseLeave={() => setHovered(null)}
                      style={{ left: `${startPct}%`, width: `${widthPct}%` }}
                      className={`absolute top-0.5 h-5 rounded cursor-pointer transition-all flex items-center px-1.5 truncate text-[9px] font-mono font-medium ${
                        isSelected
                          ? 'bg-[#2563EB] text-white ring-2 ring-white z-20'
                          : isScheduled
                          ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/60 hover:bg-emerald-900/80'
                          : 'bg-amber-950/70 text-amber-300 border border-amber-500/60 border-dashed hover:bg-amber-900/60'
                      }`}
                    >
                      <span className="truncate">{task.task_code || task.task_id}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Row 3: BLOCKS */}
            <div className="relative h-9 bg-[#0A0E17]/60 border border-[#1E2D4A] rounded flex items-center px-2">
              <span className="w-14 text-[10px] font-semibold uppercase tracking-wider text-[#94A3B8] shrink-0">
                Blocks
              </span>
              <div className="relative flex-1 h-6">
                {/* Block possession windows */}
                <div
                  style={{ left: '29.1%', width: '12.5%' }}
                  className="absolute top-0.5 h-5 bg-[#3B82F6]/25 border border-[#3B82F6] rounded flex items-center px-1.5 text-[9px] font-mono text-[#93C5FD] truncate cursor-pointer hover:bg-[#3B82F6]/35"
                  onMouseEnter={() => setHovered('Block SEC-12: Occupied 07:00 - 10:00 (TSK-0001)')}
                  onMouseLeave={() => setHovered(null)}
                >
                  SEC-12 (UP)
                </div>
                <div
                  style={{ left: '58.3%', width: '10.4%' }}
                  className={`absolute top-0.5 h-5 rounded flex items-center px-1.5 text-[9px] font-mono truncate cursor-pointer ${
                    selectedSectionCode?.includes('ALJN')
                      ? 'bg-rose-950/80 text-rose-300 border border-rose-500 ring-1 ring-rose-400'
                      : 'bg-rose-950/40 border border-rose-500/60 border-dashed text-rose-300 hover:bg-rose-950/60'
                  }`}
                  onMouseEnter={() => setHovered('Block SEC-ALJN-TDL: Window Request 14:00 - 16:30 (TSK-0007 Contention)')}
                  onMouseLeave={() => setHovered(null)}
                >
                  SEC-ALJN-TDL
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Hover info tooltip */}
        {hovered && (
          <div className="absolute bottom-2 left-16 bg-[#0A0E17]/95 border border-[#1E2D4A] px-2.5 py-1 rounded text-[10px] text-[#F8FAFC] shadow-lg pointer-events-none z-30">
            {hovered}
          </div>
        )}
      </div>

      {/* Legend Footer */}
      <div className="h-7 bg-[#141F36] border-t border-[#1E2D4A] px-3.5 flex items-center justify-between text-[10px] text-[#94A3B8]">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2 bg-emerald-500/40 border border-emerald-500 rounded-xs inline-block" />
            <span>Scheduled Possession</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2 bg-amber-500/40 border border-amber-500 border-dashed rounded-xs inline-block" />
            <span>Unplaced Requisition</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2 bg-[#2563EB]/40 border border-[#2563EB] rounded-xs inline-block" />
            <span>Express Train Path</span>
          </span>
        </div>
        <span className="font-mono text-[#64748B]">Hover to inspect entity window</span>
      </div>
    </div>
  );
};
