'use client';

import React from 'react';
import { Corridor, MaintenanceTask } from '@/types/railway';
import { ScheduleResult } from '@/types/planning';
import { Layers, MapPin } from 'lucide-react';

interface RailwayFallback2DProps {
  corridor: Corridor;
  tasks: MaintenanceTask[];
  scheduleResult?: ScheduleResult | null;
  selectedTaskId?: string | null;
  selectedSectionCode?: string | null;
  onSelectTask?: (taskId: string) => void;
  onSelectSection?: (sectionCode: string) => void;
}

export const RailwayFallback2D: React.FC<RailwayFallback2DProps> = ({
  corridor,
  tasks,
  scheduleResult,
  selectedTaskId,
  selectedSectionCode,
  onSelectTask,
  onSelectSection,
}) => {
  const stations = corridor.stations && corridor.stations.length > 0 ? corridor.stations : [
    { code: 'NDLS', name: 'New Delhi', distance_km: 0 },
    { code: 'GZB', name: 'Ghaziabad Jn', distance_km: 26 },
    { code: 'ALJN', name: 'Aligarh Jn', distance_km: 131 },
    { code: 'TDL', name: 'Tundla Jn', distance_km: 209 },
    { code: 'ETW', name: 'Etawah Jn', distance_km: 301 },
    { code: 'CNB', name: 'Kanpur Central', distance_km: 440 },
  ];

  const scheduledTaskIds = new Set(
    scheduleResult?.scheduled_tasks.map((st) => st.task_id) || []
  );

  return (
    <div className="h-full w-full bg-[#0A0A0A] p-4 flex flex-col justify-between select-none font-mono">
      <div className="flex items-center justify-between text-xs text-[#71717A] mb-2">
        <span className="flex items-center gap-1.5 text-[#A1A1AA]">
          <Layers className="w-3.5 h-3.5 text-[#4C87E7]" />
          <span>Linear Corridor Track Schematic (2D Fallback Mode)</span>
        </span>
        <span className="text-[10px] bg-[#141418] px-2 py-0.5 rounded border border-[#202024]">
          Deterministic Spatial View
        </span>
      </div>

      {/* Schematic Linear Track Strip */}
      <div className="flex-1 flex flex-col items-center justify-center py-4 overflow-x-auto">
        <div className="relative min-w-[700px] w-full max-w-4xl px-8">
          {/* Main Track Rails */}
          <div className="h-2.5 bg-[#1E1E24] border border-[#29292F] rounded-full relative flex items-center mb-6">
            <div className="absolute inset-x-0 h-[1.5px] bg-[#4C87E7]/50"></div>
          </div>

          {/* Stations positioned proportionally along track */}
          <div className="relative h-12 flex justify-between">
            {stations.map((st) => (
              <button
                key={st.code}
                onClick={() => onSelectSection?.(st.code)}
                className="flex flex-col items-center relative -top-8 cursor-pointer group"
              >
                <div className="w-3.5 h-3.5 rounded-full bg-[#18181C] border-2 border-[#4C87E7] shadow-sm mb-1 group-hover:scale-125 transition-transform" />
                <span className="text-xs font-bold text-[#F5F5F5] flex items-center gap-0.5">
                  <MapPin className="w-2.5 h-2.5 text-[#4C87E7]" />
                  {st.code}
                </span>
                <span className="text-[9px] text-[#71717A]">
                  {st.distance_km}km
                </span>
              </button>
            ))}
          </div>

          {/* Block Section Buttons */}
          {corridor.sections && (
            <div className="flex items-center justify-between gap-1 mb-4 text-[9px]">
              {corridor.sections.slice(0, 5).map((sec) => {
                const isSelected = selectedSectionCode && (sec.code?.includes(selectedSectionCode) || sec.section_id?.includes(selectedSectionCode));
                return (
                  <button
                    key={sec.code || sec.section_id}
                    onClick={() => onSelectSection?.(sec.code || sec.section_id || '')}
                    className={`flex-1 py-1 px-1 text-center rounded border truncate ${
                      isSelected
                        ? 'border-[#3B82F6] bg-[#4C87E7]/20 text-white font-bold'
                        : 'border-[#202024] bg-[#0E0E12] text-[#71717A] hover:text-[#A1A1AA]'
                    }`}
                  >
                    {(sec.code || sec.section_id || '').replace('SEC-', '')}
                  </button>
                );
              })}
            </div>
          )}

          {/* Possession Zone Markers along corridor */}
          <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 max-h-40 overflow-y-auto pr-1">
            {tasks.map((task) => {
              const isScheduled = scheduledTaskIds.has(task.task_id);
              const isSelected = selectedTaskId === task.task_id;
              const sec = task.section_code || task.section_id || '';

              return (
                <button
                  key={task.task_id}
                  onClick={() => onSelectTask?.(task.task_id)}
                  className={`text-left p-2 rounded border text-[10px] transition-all cursor-pointer ${
                    isSelected
                      ? 'border-[#3B82F6] bg-[#4C87E7]/25 text-white ring-1 ring-[#3B82F6]'
                      : isScheduled
                      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                      : 'border-rose-500/30 bg-rose-500/10 text-rose-300'
                  }`}
                >
                  <div className="font-bold">{task.task_code || task.task_id}</div>
                  <div className="text-[9px] text-[#A1A1AA] truncate font-sans">
                    {task.title}
                  </div>
                  <div className="text-[8px] mt-1 font-semibold flex items-center justify-between">
                    <span>{sec.replace('SEC-', '')}</span>
                    <span>{isScheduled ? 'SCHEDULED' : 'UNPLACED'}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
