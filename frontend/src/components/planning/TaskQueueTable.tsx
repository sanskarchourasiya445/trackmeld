'use client';

import React, { useState, useMemo } from 'react';
import { MaintenanceTask } from '@/types/railway';
import { ScheduleResult, ScheduledTaskInterval } from '@/types/planning';
import { StatusBadge } from '@/components/common/StatusBadge';
import {
  Wrench,
  Search,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

interface TaskQueueTableProps {
  tasks: MaintenanceTask[];
  scheduleResult?: ScheduleResult | null;
  selectedTaskId?: string | null;
  selectedSectionCode?: string | null;
  onSelectTask: (taskId: string) => void;
}

export const TaskQueueTable: React.FC<TaskQueueTableProps> = ({
  tasks,
  scheduleResult,
  selectedTaskId,
  selectedSectionCode,
  onSelectTask,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterMode, setFilterMode] = useState<
    'ALL' | 'SCHEDULED' | 'UNSCHEDULED' | 'MANDATORY' | 'CONFLICTS'
  >('ALL');

  const scheduledMap = useMemo(() => {
    const map = new Map<string, ScheduledTaskInterval>();
    scheduleResult?.scheduled_tasks.forEach((st) => {
      map.set(st.task_id, st);
    });
    return map;
  }, [scheduleResult]);

  const scheduledTaskIds = useMemo(() => {
    return new Set(scheduledMap.keys());
  }, [scheduledMap]);

  const conflictsCount = useMemo(() => {
    return tasks.filter((t) => !scheduledTaskIds.has(t.task_id)).length;
  }, [tasks, scheduledTaskIds]);

  const filteredTasks = useMemo(() => {
    return tasks.filter((task) => {
      // Search term filtering
      const term = searchTerm.trim().toLowerCase();
      const matchesSearch =
        term === '' ||
        task.task_id.toLowerCase().includes(term) ||
        (task.task_code && task.task_code.toLowerCase().includes(term)) ||
        task.title.toLowerCase().includes(term) ||
        (task.section_code && task.section_code.toLowerCase().includes(term)) ||
        (task.section_id && task.section_id.toLowerCase().includes(term)) ||
        (task.department && task.department.toLowerCase().includes(term));

      if (!matchesSearch) return false;

      // Filter tabs
      const isScheduled = scheduledTaskIds.has(task.task_id);
      if (filterMode === 'SCHEDULED') return isScheduled;
      if (filterMode === 'UNSCHEDULED') return !isScheduled;
      if (filterMode === 'MANDATORY') return task.mandatory === true;
      if (filterMode === 'CONFLICTS') return !isScheduled;

      return true;
    });
  }, [tasks, searchTerm, filterMode, scheduledTaskIds]);

  const scheduledCount = scheduledTaskIds.size;
  const unscheduledCount = Math.max(0, tasks.length - scheduledCount);
  const mandatoryCount = tasks.filter((t) => t.mandatory).length;

  const formatWindow = (iso?: string | null) => {
    if (!iso) return '—';
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
    } catch {
      return iso;
    }
  };

  return (
    <div className="bg-[#141418] border border-[#202024] rounded-md overflow-hidden flex flex-col h-full select-none font-mono">
      {/* Header & Search */}
      <div className="bg-[#18181C] border-b border-[#202024] p-2.5 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wrench className="w-3.5 h-3.5 text-[#4C87E7]" />
            <span className="text-xs font-semibold text-[#F5F5F5]">
              Maintenance Task Queue ({tasks.length})
            </span>
          </div>
          <div className="text-[10px] text-[#71717A] flex items-center gap-1.5">
            <span className="text-emerald-400 font-bold">{scheduledCount}</span> Sched /
            <span className="text-rose-400 font-bold">{unscheduledCount}</span> Unplaced
          </div>
        </div>

        {/* Search input */}
        <div className="relative">
          <Search className="w-3 h-3 text-[#71717A] absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by ID, title, section, gang..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#0E0E12] border border-[#202024] rounded pl-7 pr-2.5 py-1 text-[11px] text-[#F5F5F5] placeholder-[#71717A] focus:outline-hidden focus:border-[#4C87E7]"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1 overflow-x-auto text-[10px] no-scrollbar pt-0.5">
          <button
            onClick={() => setFilterMode('ALL')}
            className={`px-2 py-0.5 rounded transition-colors whitespace-nowrap ${
              filterMode === 'ALL'
                ? 'bg-[#4C87E7] text-white font-semibold'
                : 'bg-[#0E0E12] text-[#A1A1AA] hover:text-white'
            }`}
          >
            All ({tasks.length})
          </button>
          <button
            onClick={() => setFilterMode('SCHEDULED')}
            className={`px-2 py-0.5 rounded transition-colors whitespace-nowrap flex items-center gap-1 ${
              filterMode === 'SCHEDULED'
                ? 'bg-emerald-600 text-white font-semibold'
                : 'bg-[#0E0E12] text-[#A1A1AA] hover:text-emerald-400'
            }`}
          >
            <CheckCircle2 className="w-2.5 h-2.5" />
            Scheduled ({scheduledCount})
          </button>
          <button
            onClick={() => setFilterMode('UNSCHEDULED')}
            className={`px-2 py-0.5 rounded transition-colors whitespace-nowrap flex items-center gap-1 ${
              filterMode === 'UNSCHEDULED'
                ? 'bg-rose-600 text-white font-semibold'
                : 'bg-[#0E0E12] text-[#A1A1AA] hover:text-rose-400'
            }`}
          >
            <ShieldAlert className="w-2.5 h-2.5" />
            Unscheduled ({unscheduledCount})
          </button>
          <button
            onClick={() => setFilterMode('MANDATORY')}
            className={`px-2 py-0.5 rounded transition-colors whitespace-nowrap ${
              filterMode === 'MANDATORY'
                ? 'bg-amber-600 text-white font-semibold'
                : 'bg-[#0E0E12] text-[#A1A1AA] hover:text-amber-400'
            }`}
          >
            Mandatory ({mandatoryCount})
          </button>
          <button
            onClick={() => setFilterMode('CONFLICTS')}
            className={`px-2 py-0.5 rounded transition-colors whitespace-nowrap flex items-center gap-1 ${
              filterMode === 'CONFLICTS'
                ? 'bg-rose-700 text-white font-semibold'
                : 'bg-[#0E0E12] text-[#A1A1AA] hover:text-rose-400'
            }`}
          >
            <AlertTriangle className="w-2.5 h-2.5" />
            Conflicts ({conflictsCount})
          </button>
        </div>
      </div>

      {/* Table content */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-left text-[11px] border-collapse">
          <thead>
            <tr className="bg-[#0E0E12] border-b border-[#202024] text-[#71717A] uppercase text-[9px] sticky top-0 z-10">
              <th className="py-2 px-2.5 font-semibold">Task ID / Priority</th>
              <th className="py-2 px-2 font-semibold">Activity & Gang</th>
              <th className="py-2 px-2 font-semibold">Block Section</th>
              <th className="py-2 px-2 font-semibold">Assigned Window</th>
              <th className="py-2 px-2 font-semibold">Duration</th>
              <th className="py-2 px-2.5 font-semibold text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#202024]/60">
            {filteredTasks.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-[#71717A] text-xs">
                  No maintenance tasks match the current filters.
                </td>
              </tr>
            ) : (
              filteredTasks.map((task) => {
                const scheduled = scheduledMap.get(task.task_id);
                const isScheduled = !!scheduled;
                const isSelected = selectedTaskId === task.task_id;
                const sec = task.section_code || task.section_id || '';
                const isSectionMatch = selectedSectionCode && sec.includes(selectedSectionCode);
                const duration =
                  task.required_duration_minutes || task.estimated_duration_minutes || 120;

                // Assigned window vs requested window
                const startWindow = scheduled?.interval?.start || scheduled?.start_time;
                const endWindow = scheduled?.interval?.end || scheduled?.end_time;
                const windowText = isScheduled
                  ? `${formatWindow(startWindow)}–${formatWindow(endWindow)} UTC`
                  : `${formatWindow(task.earliest_start || task.window_start)}–${formatWindow(task.latest_finish || task.window_end)} (Req)`;

                // Assigned resources display
                const assignedRes = scheduled?.assigned_resources?.map((r) => r.replace('RES-', '')).join(', ');

                return (
                  <tr
                    key={task.task_id}
                    onClick={() => onSelectTask(task.task_id)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-[#1E1E24] text-[#F5F5F5] border-l-2 border-l-[#4C87E7]'
                        : isSectionMatch
                        ? 'bg-[#4C87E7]/10 text-[#F5F5F5]'
                        : 'hover:bg-[#18181C]/70 text-[#A1A1AA]'
                    }`}
                  >
                    <td className="py-2 px-2.5 whitespace-nowrap">
                      <div className="font-semibold text-[#F5F5F5]">
                        {task.task_code || task.task_id}
                      </div>
                      <div className="flex items-center gap-1 mt-0.5">
                        {task.mandatory && (
                          <span className="text-[8px] px-1 py-0.2 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40">
                            MANDATORY
                          </span>
                        )}
                        <span
                          className={`text-[8px] px-1 py-0.2 rounded font-semibold ${
                            task.priority === 'CRITICAL' || task.urgency === 'CRITICAL'
                              ? 'bg-rose-500/20 text-rose-300'
                              : 'bg-zinc-800 text-zinc-400'
                          }`}
                        >
                          {task.priority || task.urgency || 'ROUTINE'}
                        </span>
                      </div>
                    </td>

                    <td className="py-2 px-2 max-w-[140px]">
                      <div className="truncate text-[#F5F5F5] font-medium font-sans" title={task.title}>
                        {task.title}
                      </div>
                      <div className="text-[9px] text-[#71717A] truncate">
                        {assignedRes ? `Gang: ${assignedRes}` : task.department || 'ENGINEERING'}
                      </div>
                    </td>

                    <td className="py-2 px-2 whitespace-nowrap">
                      <span className="text-[#D4D4D8]">{sec.replace('SEC-', '')}</span>
                      <div className="text-[8.5px] text-[#71717A]">Track: {task.track_type || 'UP'}</div>
                    </td>

                    <td className="py-2 px-2 whitespace-nowrap text-[10px]">
                      <span className={isScheduled ? 'text-emerald-400 font-semibold' : 'text-rose-400/80'}>
                        {windowText}
                      </span>
                    </td>

                    <td className="py-2 px-2 whitespace-nowrap text-[#A1A1AA]">
                      {duration}m
                    </td>

                    <td className="py-2 px-2.5 whitespace-nowrap text-right">
                      <StatusBadge
                        status={isScheduled ? 'FEASIBLE' : 'INFEASIBLE'}
                        size="sm"
                      />
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
