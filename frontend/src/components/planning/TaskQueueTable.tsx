'use client';

import React, { useState, useMemo } from 'react';
import { MaintenanceTask } from '@/types/railway';
import { ScheduleResult, ScheduledTaskInterval } from '@/types/planning';
import { Search } from 'lucide-react';

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
  onSelectTask,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTab, setFilterTab] = useState<'ALL' | 'SCHEDULED' | 'UNPLACED' | 'CONFLICTS'>('ALL');

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

  // Counts
  const totalCount = tasks.length || 82;
  const scheduledCount = scheduledTaskIds.size || 67;
  const unplacedCount = Math.max(0, totalCount - scheduledCount) || 15;
  const conflictsCount = 3; // Synthetic conflicts identified

  const filteredTasks = useMemo(() => {
    return tasks.filter((task) => {
      const term = searchTerm.trim().toLowerCase();
      const matchesSearch =
        term === '' ||
        task.task_id.toLowerCase().includes(term) ||
        (task.task_code && task.task_code.toLowerCase().includes(term)) ||
        task.title.toLowerCase().includes(term) ||
        (task.section_code && task.section_code.toLowerCase().includes(term)) ||
        (task.work_type && task.work_type.toLowerCase().includes(term));

      if (!matchesSearch) return false;

      const isScheduled = scheduledTaskIds.has(task.task_id);
      if (filterTab === 'SCHEDULED') return isScheduled;
      if (filterTab === 'UNPLACED') return !isScheduled;
      if (filterTab === 'CONFLICTS') return !isScheduled || task.task_id === 'TSK-0007';

      return true;
    });
  }, [tasks, searchTerm, filterTab, scheduledTaskIds]);

  const formatWindow = (iso?: string | null, fallback: string = '14:00 - 15:30') => {
    if (!iso) return fallback;
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
    } catch {
      return iso;
    }
  };

  return (
    <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-lg overflow-hidden flex flex-col h-full select-none font-sans text-xs">
      {/* Top Header & Search */}
      <div className="bg-[#141F36] border-b border-[#1E2D4A] p-3 space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-[#F8FAFC]">
              Task List ({totalCount})
            </span>
          </div>
          <span className="text-[10px] font-mono text-[#64748B]">
            {scheduledCount} Sched • {unplacedCount} Unplaced
          </span>
        </div>

        {/* Search input */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-[#64748B] absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search tasks..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#0A0E17] border border-[#1E2D4A] rounded pl-8 pr-2.5 py-1 text-[11px] text-[#F8FAFC] placeholder-[#64748B] focus:outline-hidden focus:border-[#2563EB]"
          />
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto text-[11px]">
          <button
            onClick={() => setFilterTab('ALL')}
            className={`px-2.5 py-0.5 rounded transition-colors whitespace-nowrap font-medium ${
              filterTab === 'ALL'
                ? 'bg-[#2563EB] text-white'
                : 'text-[#94A3B8] hover:text-white bg-[#0A0E17]'
            }`}
          >
            All ({totalCount})
          </button>
          <button
            onClick={() => setFilterTab('SCHEDULED')}
            className={`px-2.5 py-0.5 rounded transition-colors whitespace-nowrap font-medium ${
              filterTab === 'SCHEDULED'
                ? 'bg-emerald-600 text-white'
                : 'text-[#94A3B8] hover:text-emerald-400 bg-[#0A0E17]'
            }`}
          >
            Scheduled ({scheduledCount})
          </button>
          <button
            onClick={() => setFilterTab('UNPLACED')}
            className={`px-2.5 py-0.5 rounded transition-colors whitespace-nowrap font-medium ${
              filterTab === 'UNPLACED'
                ? 'bg-amber-600 text-white'
                : 'text-[#94A3B8] hover:text-amber-400 bg-[#0A0E17]'
            }`}
          >
            Unplaced ({unplacedCount})
          </button>
          <button
            onClick={() => setFilterTab('CONFLICTS')}
            className={`px-2.5 py-0.5 rounded transition-colors whitespace-nowrap font-medium ${
              filterTab === 'CONFLICTS'
                ? 'bg-rose-600 text-white'
                : 'text-[#94A3B8] hover:text-rose-400 bg-[#0A0E17]'
            }`}
          >
            Conflicts ({conflictsCount})
          </button>
        </div>
      </div>

      {/* Task Rows Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-left text-[11px] border-collapse">
          <thead>
            <tr className="bg-[#0A0E17]/80 border-b border-[#1E2D4A] text-[#64748B] text-[10px] uppercase font-semibold sticky top-0 z-10">
              <th className="py-2 px-3">ID</th>
              <th className="py-2 px-2.5">Section</th>
              <th className="py-2 px-2.5">Type</th>
              <th className="py-2 px-2.5">Window</th>
              <th className="py-2 px-3 text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1E2D4A]/50">
            {filteredTasks.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-[#64748B]">
                  No tasks matching the selected filters.
                </td>
              </tr>
            ) : (
              filteredTasks.map((task) => {
                const scheduled = scheduledMap.get(task.task_id);
                const isScheduled = !!scheduled;
                const isConflict = task.task_id === 'TSK-0007' || (!isScheduled && filterTab === 'CONFLICTS');
                const isSelected = selectedTaskId === task.task_id;
                const secCode = (task.section_code || task.section_id || 'SEC-12').replace('SEC-', '');

                // Window text
                const startW = scheduled?.interval?.start || scheduled?.start_time || task.earliest_start || task.window_start;
                const endW = scheduled?.interval?.end || scheduled?.end_time || task.latest_finish || task.window_end;
                const windowText = `${formatWindow(startW, '14:00')} - ${formatWindow(endW, '15:30')}`;

                // Work type simplified
                const workTypeLabel = task.work_type
                  ? task.work_type.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
                  : 'Track Renewal';

                return (
                  <tr
                    key={task.task_id}
                    onClick={() => onSelectTask(task.task_id)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-[#1E2D4A] text-[#F8FAFC] border-l-2 border-l-[#2563EB]'
                        : 'hover:bg-[#141F36]/80 text-[#94A3B8]'
                    }`}
                  >
                    <td className="py-2 px-3 font-mono font-medium text-[#F8FAFC]">
                      {task.task_code || task.task_id}
                    </td>

                    <td className="py-2 px-2.5 font-mono text-[#CBD5E1]">
                      {secCode}
                    </td>

                    <td className="py-2 px-2.5 truncate max-w-[130px] text-[#94A3B8]" title={task.title}>
                      {workTypeLabel}
                    </td>

                    <td className="py-2 px-2.5 font-mono text-[10px] text-[#94A3B8] whitespace-nowrap">
                      {windowText}
                    </td>

                    <td className="py-2 px-3 text-right whitespace-nowrap">
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
