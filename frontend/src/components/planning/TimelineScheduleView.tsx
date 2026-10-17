'use client';

import React, { useState } from 'react';
import { TrainMovement, MaintenanceTask } from '@/types/railway';
import { ScheduleResult } from '@/types/planning';

interface TimelineScheduleViewProps {
  trains: TrainMovement[];
  tasks: MaintenanceTask[];
  scheduleResult?: ScheduleResult | null;
  selectedTaskId?: string | null;
  selectedTrainId?: string | null;
  selectedSectionCode?: string | null;
  onSelectTask?: (taskId: string) => void;
  onSelectTrain?: (trainId: string) => void;
  onSwitchToTimeSpace?: () => void;
  isEmbedded?: boolean;
  className?: string;
}

export const TimelineScheduleView: React.FC<TimelineScheduleViewProps> = ({
  selectedTaskId,
  selectedTrainId,
  selectedSectionCode,
  onSelectTask,
  onSelectTrain,
  onSwitchToTimeSpace,
  isEmbedded = false,
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState<'TIMELINE' | 'TIMESPACE'>('TIMELINE');
  const [horizonRange, setHorizonRange] = useState<'24h' | '48h' | '72h'>('48h');
  const [hovered, setHovered] = useState<string | null>(null);

  // Time markers based on horizon
  const timeMarkers = ['00:00', '06:00', '12:00', '18:00', '24:00'];

  return (
    <div
      className={`flex flex-col h-full bg-[#0B1120] font-sans text-xs ${
        isEmbedded ? '' : 'border border-[#1A263D] rounded-lg overflow-hidden'
      } ${className}`}
    >
      {/* 1. Header Toolbar (Hidden when embedded inside integrated container with parent header) */}
      {!isEmbedded && (
        <div className="h-10 bg-[#0F172A] border-b border-[#1A263D] px-3.5 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 font-semibold text-xs">
              <button
                onClick={() => setActiveTab('TIMELINE')}
                className={`pb-0.5 transition-colors ${
                  activeTab === 'TIMELINE' ? 'text-[#F8FAFC] border-b-2 border-[#2563EB]' : 'text-[#64748B] hover:text-[#94A3B8]'
                }`}
              >
                Timeline
              </button>
              <span className="text-[#334155] mx-1">|</span>
              <button
                onClick={() => {
                  if (onSwitchToTimeSpace) {
                    onSwitchToTimeSpace();
                  } else {
                    setActiveTab('TIMESPACE');
                  }
                }}
                title="Switch to Diagram view"
                aria-label="Switch to Diagram view"
                className="text-[#64748B] hover:text-[#94A3B8] transition-colors"
              >
                Diagram View
              </button>
            </div>

            <span className="text-[11px] font-mono text-[#94A3B8] hidden sm:inline">
              Oct 10, 2026
            </span>
          </div>

          {/* Horizon Range Selector (24h | 48h | 72h) */}
          <div className="flex items-center bg-[#070B14] border border-[#1A263D] rounded p-0.5 text-[10px] font-mono">
            <button
              onClick={() => setHorizonRange('24h')}
              className={`px-2 py-0.5 rounded transition-colors ${
                horizonRange === '24h' ? 'bg-[#2563EB] text-white font-bold' : 'text-[#64748B] hover:text-white'
              }`}
            >
              24h
            </button>
            <button
              onClick={() => setHorizonRange('48h')}
              className={`px-2 py-0.5 rounded transition-colors ${
                horizonRange === '48h' ? 'bg-[#2563EB] text-white font-bold' : 'text-[#64748B] hover:text-white'
              }`}
            >
              48h
            </button>
            <button
              onClick={() => setHorizonRange('72h')}
              className={`px-2 py-0.5 rounded transition-colors ${
                horizonRange === '72h' ? 'bg-[#2563EB] text-white font-bold' : 'text-[#64748B] hover:text-white'
              }`}
            >
              72h
            </button>
          </div>
        </div>
      )}

      {/* 2. Diagram Canvas */}
      <div className="flex-1 p-2 sm:p-2.5 relative flex flex-col justify-between overflow-hidden">
        {/* Time Axis Bar */}
        <div className="relative h-5 border-b border-[#1A263D] flex items-center shrink-0">
          {timeMarkers.map((mark, idx) => {
            const leftPct = (idx / (timeMarkers.length - 1)) * 100;
            return (
              <div
                key={mark}
                className="absolute -translate-x-1/2 flex flex-col items-center"
                style={{ left: `${leftPct}%` }}
              >
                <span className="text-[10px] font-mono text-[#64748B]">{mark}</span>
                <div className="w-[1px] h-1 bg-[#233554] mt-0.5" />
              </div>
            );
          })}
        </div>

        {/* Timeline Grid Rows */}
        <div className="flex-1 flex flex-col justify-around py-1 relative">
          {/* Vertical grid lines */}
          {timeMarkers.map((mark, idx) => {
            const leftPct = (idx / (timeMarkers.length - 1)) * 100;
            return (
              <div
                key={`grid-${mark}`}
                className="absolute top-0 bottom-0 w-[1px] bg-[#1A263D]/40 pointer-events-none -translate-x-1/2"
                style={{ left: `${leftPct}%` }}
              />
            );
          })}

          {/* Row 1: TRAINS */}
          <div className="relative h-8.5 bg-[#070D18]/70 border border-[#1A263D] rounded-md flex items-center px-2 min-w-0">
            <span className="w-11 sm:w-13 text-[9.5px] font-bold uppercase text-[#64748B] shrink-0 font-mono tracking-wider truncate">
              Trains
            </span>
            <div className="relative flex-1 h-5.5 min-w-0">
              {/* Train trajectory bars */}
              <div
                onClick={() => onSelectTrain?.('12400')}
                onMouseEnter={() => setHovered('Train 12400 Express: 04:30 – 08:30 UTC')}
                onMouseLeave={() => setHovered(null)}
                style={{ left: '18%', width: '22%' }}
                className={`absolute top-0.5 h-4.5 rounded cursor-pointer transition-all flex items-center px-1.5 text-[9px] font-mono font-medium ${
                  selectedTrainId === '12400'
                    ? 'bg-[#2563EB] text-white ring-2 ring-[#60A5FA] z-20 shadow-xs'
                    : 'bg-[#1D4ED8]/70 text-[#BFDBFE] border border-[#2563EB]/50 hover:bg-[#2563EB]'
                }`}
              >
                <span className="truncate">12400</span>
              </div>

              <div
                onClick={() => onSelectTrain?.('02073')}
                onMouseEnter={() => setHovered('Train 02073 (Shatabdi Exp): 14:00 – 17:30 UTC')}
                onMouseLeave={() => setHovered(null)}
                style={{ left: '58%', width: '18%' }}
                className={`absolute top-0.5 h-4.5 rounded cursor-pointer transition-all flex items-center px-1.5 text-[9px] font-mono font-medium ${
                  selectedTrainId === '02073'
                    ? 'bg-[#2563EB] text-white ring-2 ring-white z-20 shadow-xs'
                    : 'bg-[#1E3A8A]/90 text-[#93C5FD] border border-[#2563EB]/40 hover:bg-[#2563EB]'
                }`}
              >
                <span className="truncate">02073</span>
              </div>

              <div
                style={{ left: '80%', width: '15%' }}
                className="absolute top-0.5 h-4.5 rounded bg-[#131E35] border border-[#223554] text-[#94A3B8] flex items-center px-1.5 text-[9px] font-mono truncate"
              >
                FRG-401
              </div>
            </div>
          </div>

          {/* Row 2: TASKS */}
          <div className="relative h-8.5 bg-[#070D18]/70 border border-[#1A263D] rounded-md flex items-center px-2">
            <span className="w-11 sm:w-13 text-[9.5px] font-bold uppercase text-[#64748B] shrink-0 font-mono tracking-wider">
              Tasks
            </span>
            <div className="relative flex-1 h-5.5">
              {/* Task possession bars */}
              <div
                onClick={() => onSelectTask?.('TSK-0001')}
                onMouseEnter={() => setHovered('Task TSK-0001: 02:00 – 05:00 UTC (Scheduled)')}
                onMouseLeave={() => setHovered(null)}
                style={{ left: '8%', width: '15%' }}
                className={`absolute top-0.5 h-4.5 rounded cursor-pointer transition-all flex items-center px-1.5 text-[9px] font-mono font-medium ${
                  selectedTaskId === 'TSK-0001'
                    ? 'bg-[#2563EB] text-white ring-2 ring-white z-20 shadow-xs'
                    : 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/60 hover:bg-emerald-900'
                }`}
              >
                <span className="truncate">TSK-0001</span>
              </div>

              {/* TSK-0007 Highlighted Amber/Red */}
              <div
                onClick={() => onSelectTask?.('TSK-0007')}
                onMouseEnter={() => setHovered('Task TSK-0007: 07:00 – 10:00 UTC (Unscheduled / Conflict)')}
                onMouseLeave={() => setHovered(null)}
                style={{ left: '29%', width: '16%' }}
                className={`absolute top-0.5 h-4.5 rounded cursor-pointer transition-all flex items-center px-1.5 text-[9px] font-mono font-medium ${
                  selectedTaskId === 'TSK-0007'
                    ? 'bg-amber-500 text-black font-bold ring-2 ring-white z-20 shadow-xs'
                    : 'bg-amber-950 text-amber-300 border border-amber-500 border-dashed hover:bg-amber-900'
                }`}
              >
                <span className="truncate">TSK-0007</span>
              </div>

              <div
                onClick={() => onSelectTask?.('TSK-0008')}
                onMouseEnter={() => setHovered('Task TSK-0008: 12:00 – 16:00 UTC (Scheduled)')}
                onMouseLeave={() => setHovered(null)}
                style={{ left: '50%', width: '14%' }}
                className="absolute top-0.5 h-4.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/60 flex items-center px-1.5 text-[9px] font-mono truncate cursor-pointer hover:bg-emerald-900"
              >
                TSK-0008
              </div>

              <div
                style={{ left: '72%', width: '18%' }}
                className="absolute top-0.5 h-4.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/60 flex items-center px-1.5 text-[9px] font-mono truncate"
              >
                TSK-0009
              </div>
            </div>
          </div>

          {/* Row 3: BLOCKS */}
          <div className="relative h-8.5 bg-[#070D18]/70 border border-[#1A263D] rounded-md flex items-center px-2">
            <span className="w-11 sm:w-13 text-[9.5px] font-bold uppercase text-[#64748B] shrink-0 font-mono tracking-wider">
              Blocks
            </span>
            <div className="relative flex-1 h-5.5">
              <div
                style={{ left: '10%', width: '22%' }}
                className="absolute top-0.5 h-4.5 bg-[#2563EB]/20 border border-[#2563EB]/60 rounded flex items-center px-1.5 text-[9px] font-mono text-[#93C5FD] truncate"
              >
                SEC-18 (UP)
              </div>

              <div
                style={{ left: '42%', width: '18%' }}
                className={`absolute top-0.5 h-4.5 rounded flex items-center px-1.5 text-[9px] font-mono truncate cursor-pointer ${
                  selectedSectionCode === 'SEC-12'
                    ? 'bg-purple-900/60 text-purple-200 border border-purple-400 ring-1 ring-purple-300'
                    : 'bg-purple-950/40 text-purple-300 border border-purple-500/50'
                }`}
                onMouseEnter={() => setHovered('Block Section SEC-12 (UP Mainline)')}
                onMouseLeave={() => setHovered(null)}
              >
                SEC-12 (UP)
              </div>

              <div
                style={{ left: '75%', width: '16%' }}
                className="absolute top-0.5 h-4.5 bg-purple-950/40 text-purple-300 border border-purple-500/50 rounded flex items-center px-1.5 text-[9px] font-mono truncate"
              >
                SEC-22
              </div>
            </div>
          </div>
        </div>

        {/* Hover inspection tooltip */}
        {hovered && (
          <div className="absolute bottom-1 left-16 bg-[#070B12]/95 border border-[#1A263D] px-2.5 py-1 rounded text-[10px] text-[#F8FAFC] shadow-lg pointer-events-none z-30 font-mono">
            {hovered}
          </div>
        )}
      </div>
    </div>
  );
};
