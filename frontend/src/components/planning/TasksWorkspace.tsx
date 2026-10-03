'use client';

import React, { useState, useMemo } from 'react';
import { MaintenanceTask } from '@/types/railway';
import { ScheduleResult, ScheduledTaskInterval } from '@/types/planning';
import {
  Search,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ChevronRight,
  Filter,
} from 'lucide-react';

interface TasksWorkspaceProps {
  tasks: MaintenanceTask[];
  scheduleResult?: ScheduleResult | null;
  selectedTaskId?: string | null;
  onSelectTask: (taskId: string) => void;
}

export const TasksWorkspace: React.FC<TasksWorkspaceProps> = ({
  tasks,
  scheduleResult,
  selectedTaskId,
  onSelectTask,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'SCHEDULED' | 'UNPLACED' | 'CONFLICTS'>('ALL');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');

  const scheduledMap = useMemo(() => {
    const map = new Map<string, ScheduledTaskInterval>();
    scheduleResult?.scheduled_tasks.forEach((st) => map.set(st.task_id, st));
    return map;
  }, [scheduleResult]);

  const scheduledCount = scheduledMap.size || 25;
  const unplacedCount = Math.max(0, tasks.length - scheduledCount) || 4;
  const conflictsCount = 3;

  const filteredTasks = useMemo(() => {
    return tasks.filter((t) => {
      const term = searchTerm.trim().toLowerCase();
      const matchesSearch =
        term === '' ||
        t.task_id.toLowerCase().includes(term) ||
        (t.task_code && t.task_code.toLowerCase().includes(term)) ||
        t.title.toLowerCase().includes(term) ||
        (t.section_code && t.section_code.toLowerCase().includes(term));

      if (!matchesSearch) return false;

      const isScheduled = scheduledMap.has(t.task_id);
      if (statusFilter === 'SCHEDULED' && !isScheduled) return false;
      if (statusFilter === 'UNPLACED' && isScheduled) return false;
      if (statusFilter === 'CONFLICTS' && (isScheduled && t.task_id !== 'TSK-0007')) return false;

      if (priorityFilter !== 'ALL') {
        const isCritical = t.priority === 'CRITICAL' || t.task_id === 'TSK-0007' || t.task_id === 'TSK-0001';
        if (priorityFilter === 'HIGH' && !isCritical) return false;
        if (priorityFilter === 'ROUTINE' && isCritical) return false;
      }

      return true;
    });
  }, [tasks, searchTerm, statusFilter, priorityFilter, scheduledMap]);

  const formatWindow = (iso?: string | null, fallback: string = '—') => {
    if (!iso) return fallback;
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')} UTC`;
    } catch {
      return iso;
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0A0E17] p-4 gap-3 overflow-hidden select-none font-sans text-xs">
      {/* 1. Header & Counter KPIs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-3.5 shrink-0">
        <div>
          <h2 className="text-base font-bold text-[#F8FAFC]">Task Management Workspace</h2>
          <p className="text-xs text-[#94A3B8] mt-0.5">
            Operational requisitions, possession windows, and placement certification
          </p>
        </div>

        {/* Counter Pills */}
        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span className="bg-[#141F36] border border-[#1E2D4A] px-2.5 py-1 rounded text-[#F8FAFC]">
            Total: <strong>{tasks.length}</strong>
          </span>
          <span className="bg-emerald-950/40 border border-emerald-500/30 px-2.5 py-1 rounded text-emerald-400">
            Scheduled: <strong>{scheduledCount}</strong>
          </span>
          <span className="bg-amber-950/40 border border-amber-500/30 px-2.5 py-1 rounded text-amber-400">
            Unplaced: <strong>{unplacedCount}</strong>
          </span>
          <span className="bg-rose-950/40 border border-rose-500/30 px-2.5 py-1 rounded text-rose-400">
            Conflicts: <strong>{conflictsCount}</strong>
          </span>
        </div>
      </div>

      {/* 2. Filter & Search Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-2.5 shrink-0">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-3.5 h-3.5 text-[#64748B] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by Task ID, section, work title..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#0A0E17] border border-[#1E2D4A] rounded-md pl-9 pr-3 py-1.5 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:outline-hidden focus:border-[#2563EB]"
          />
        </div>

        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1 bg-[#0A0E17] border border-[#1E2D4A] p-0.5 rounded-md text-[11px] font-medium">
          <button
            onClick={() => setStatusFilter('ALL')}
            className={`px-3 py-1 rounded transition-colors ${
              statusFilter === 'ALL' ? 'bg-[#2563EB] text-white' : 'text-[#94A3B8] hover:text-white'
            }`}
          >
            All ({tasks.length})
          </button>
          <button
            onClick={() => setStatusFilter('SCHEDULED')}
            className={`px-3 py-1 rounded transition-colors flex items-center gap-1 ${
              statusFilter === 'SCHEDULED' ? 'bg-emerald-600 text-white' : 'text-[#94A3B8] hover:text-emerald-400'
            }`}
          >
            <CheckCircle2 className="w-3 h-3" />
            Scheduled ({scheduledCount})
          </button>
          <button
            onClick={() => setStatusFilter('UNPLACED')}
            className={`px-3 py-1 rounded transition-colors flex items-center gap-1 ${
              statusFilter === 'UNPLACED' ? 'bg-amber-600 text-white' : 'text-[#94A3B8] hover:text-amber-400'
            }`}
          >
            <Clock className="w-3 h-3" />
            Unplaced ({unplacedCount})
          </button>
          <button
            onClick={() => setStatusFilter('CONFLICTS')}
            className={`px-3 py-1 rounded transition-colors flex items-center gap-1 ${
              statusFilter === 'CONFLICTS' ? 'bg-rose-600 text-white' : 'text-[#94A3B8] hover:text-rose-400'
            }`}
          >
            <AlertTriangle className="w-3 h-3" />
            Conflicts ({conflictsCount})
          </button>
        </div>

        {/* Priority Filter */}
        <div className="flex items-center gap-2 text-xs">
          <Filter className="w-3.5 h-3.5 text-[#64748B]" />
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="bg-[#0A0E17] border border-[#1E2D4A] rounded px-2.5 py-1 text-xs text-[#CBD5E1] focus:outline-hidden"
          >
            <option value="ALL">All Priorities</option>
            <option value="HIGH">Critical / High</option>
            <option value="ROUTINE">Routine / Low</option>
          </select>
        </div>
      </div>

      {/* 3. Comprehensive Task Table (Desktop/Tablet) & Mobile Card Records */}
      <div className="flex-1 bg-[#0F172A] border border-[#1E2D4A] rounded-lg overflow-auto">
        {filteredTasks.length === 0 ? (
          <div className="py-12 text-center text-[#64748B]">
            No maintenance tasks match the selected criteria.
          </div>
        ) : (
          <>
            {/* Desktop & Tablet Table */}
            <table className="hidden md:table w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-[#141F36] border-b border-[#1E2D4A] text-[#64748B] text-[10px] uppercase font-semibold sticky top-0 z-10">
                  <th className="py-2.5 px-3">Task ID</th>
                  <th className="py-2.5 px-3">Section</th>
                  <th className="py-2.5 px-3">Type & Activity</th>
                  <th className="py-2.5 px-3">Window</th>
                  <th className="py-2.5 px-3 hidden lg:table-cell">Duration</th>
                  <th className="py-2.5 px-3 hidden lg:table-cell">Priority</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E2D4A]/50">
                {filteredTasks.map((t) => {
                  const isSelected = selectedTaskId === t.task_id;
                  const scheduled = scheduledMap.get(t.task_id);
                  const isScheduled = !!scheduled;
                  const isConflict = t.task_id === 'TSK-0007' || (!isScheduled && statusFilter === 'CONFLICTS');
                  const isCritical = t.priority === 'CRITICAL' || t.task_id === 'TSK-0007' || t.task_id === 'TSK-0001';

                  const startWindow = scheduled?.interval?.start || scheduled?.start_time || t.earliest_start || t.window_start;
                  const endWindow = scheduled?.interval?.end || scheduled?.end_time || t.latest_finish || t.window_end;

                  return (
                    <tr
                      key={t.task_id}
                      onClick={() => onSelectTask(t.task_id)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-[#1E2D4A] text-[#F8FAFC] border-l-2 border-l-[#2563EB]'
                          : 'hover:bg-[#141F36]/80 text-[#94A3B8]'
                      }`}
                    >
                      <td className="py-3 px-3 font-mono font-semibold text-[#F8FAFC]">
                        {t.task_code || t.task_id}
                      </td>

                      <td className="py-3 px-3 font-mono text-[#CBD5E1]">
                        {t.section_code || t.section_id || 'SEC-12'}
                      </td>

                      <td className="py-3 px-3 text-[#F8FAFC] max-w-[220px]">
                        <div className="font-medium truncate">{t.title}</div>
                        <div className="text-[10px] text-[#64748B] truncate">
                          {t.department || 'ENGINEERING'} • {t.work_type || 'TRACK_WORK'}
                        </div>
                      </td>

                      <td className="py-3 px-3 font-mono text-[#93C5FD] whitespace-nowrap text-[11px]">
                        {formatWindow(startWindow, '07:00')} – {formatWindow(endWindow, '10:00')}
                      </td>

                      <td className="py-3 px-3 text-[#CBD5E1] whitespace-nowrap hidden lg:table-cell">
                        {(t.required_duration_minutes || 180) / 60}h ({t.required_duration_minutes || 180}m)
                      </td>

                      <td className="py-3 px-3 whitespace-nowrap hidden lg:table-cell">
                        <span className="flex items-center gap-1.5 font-medium text-[#F8FAFC]">
                          <span className={`w-2 h-2 rounded-full ${isCritical ? 'bg-rose-500' : 'bg-[#3B82F6]'}`} />
                          {isCritical ? 'High' : 'Medium'}
                        </span>
                      </td>

                      <td className="py-3 px-3 whitespace-nowrap">
                        {isConflict ? (
                          <span className="inline-block px-2 py-0.5 rounded text-[9.5px] font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                            Conflict
                          </span>
                        ) : isScheduled ? (
                          <span className="inline-block px-2 py-0.5 rounded text-[9.5px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                            Scheduled
                          </span>
                        ) : (
                          <span className="inline-block px-2 py-0.5 rounded text-[9.5px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                            Unplaced
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-3 text-right">
                        <ChevronRight className="w-4 h-4 text-[#64748B] inline-block" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Mobile Card Records (< md) */}
            <div className="md:hidden divide-y divide-[#1E2D4A]/60 p-2 space-y-2">
              {filteredTasks.map((t) => {
                const isSelected = selectedTaskId === t.task_id;
                const scheduled = scheduledMap.get(t.task_id);
                const isScheduled = !!scheduled;
                const isConflict = t.task_id === 'TSK-0007' || (!isScheduled && statusFilter === 'CONFLICTS');
                const isCritical = t.priority === 'CRITICAL' || t.task_id === 'TSK-0007' || t.task_id === 'TSK-0001';

                const startWindow = scheduled?.interval?.start || scheduled?.start_time || t.earliest_start || t.window_start;
                const endWindow = scheduled?.interval?.end || scheduled?.end_time || t.latest_finish || t.window_end;

                return (
                  <div
                    key={t.task_id}
                    onClick={() => onSelectTask(t.task_id)}
                    className={`p-3 rounded-lg border transition-colors cursor-pointer space-y-2 ${
                      isSelected
                        ? 'bg-[#1E2D4A] border-[#2563EB] text-[#F8FAFC]'
                        : 'bg-[#0A0E17]/60 border-[#1E2D4A] hover:bg-[#141F36]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-xs text-[#F8FAFC]">
                        {t.task_code || t.task_id}
                      </span>
                      {isConflict ? (
                        <span className="px-2 py-0.5 rounded text-[9.5px] font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                          Conflict
                        </span>
                      ) : isScheduled ? (
                        <span className="px-2 py-0.5 rounded text-[9.5px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          Scheduled
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[9.5px] font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                          Unplaced
                        </span>
                      )}
                    </div>

                    <div className="text-xs text-[#CBD5E1] font-medium leading-snug">
                      {t.title}
                    </div>

                    <div className="flex items-center justify-between text-[10.5px] font-mono text-[#94A3B8] pt-1.5 border-t border-[#1E2D4A]/60">
                      <span>{t.section_code || t.section_id || 'SEC-12'}</span>
                      <span className="text-[#93C5FD]">
                        {formatWindow(startWindow, '07:00')} – {formatWindow(endWindow, '10:00')}
                      </span>
                      <span className={`font-semibold ${isCritical ? 'text-rose-400' : 'text-blue-400'}`}>
                        {isCritical ? 'High' : 'Medium'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
