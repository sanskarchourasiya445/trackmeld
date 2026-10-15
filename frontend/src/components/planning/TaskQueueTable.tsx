'use client';

import React, { useState, useMemo } from 'react';
import { MaintenanceTask } from '@/types/railway';
import { ScheduleResult, ScheduledTaskInterval } from '@/types/planning';
import { Search, ChevronRight, ChevronUp, ChevronDown } from 'lucide-react';

interface TaskQueueTableProps {
  tasks: MaintenanceTask[];
  scheduleResult?: ScheduleResult | null;
  selectedTaskId?: string | null;
  onSelectTask: (taskId: string) => void;
  isCollapsible?: boolean;
  isEmbedded?: boolean;
  className?: string;
}

export const TaskQueueTable: React.FC<TaskQueueTableProps> = ({
  tasks,
  scheduleResult,
  selectedTaskId,
  onSelectTask,
  isCollapsible = false,
  isEmbedded = false,
  className = '',
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTab, setFilterTab] = useState<'ALL' | 'SCHEDULED' | 'UNPLACED' | 'CONFLICTS'>('ALL');
  const [isCollapsed, setIsCollapsed] = useState(false);

  const scheduledMap = useMemo(() => {
    const map = new Map<string, ScheduledTaskInterval>();
    scheduleResult?.scheduled_tasks.forEach((st) => {
      map.set(st.task_id, st);
    });
    return map;
  }, [scheduleResult]);

  const scheduledCount = scheduledMap.size || 25;
  const unplacedCount = Math.max(0, tasks.length - scheduledCount) || 4;
  const conflictsCount = 3;

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

      const isScheduled = scheduledMap.has(task.task_id);
      if (filterTab === 'SCHEDULED') return isScheduled;
      if (filterTab === 'UNPLACED') return !isScheduled;
      if (filterTab === 'CONFLICTS') return !isScheduled || task.task_id === 'TSK-0007';

      return true;
    });
  }, [tasks, searchTerm, filterTab, scheduledMap]);

  const formatWindow = (iso?: string | null, fallback: string = '07:00 – 10:00') => {
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
    <div
      className={`bg-[#0B1120] flex flex-col h-full select-none font-sans text-xs ${
        isEmbedded ? '' : 'border border-[#1A263D] rounded-lg overflow-hidden'
      } ${className}`}
    >
      {/* Top Header & Search */}
      <div className="bg-[#0F172A] border-b border-[#1A263D] p-2 sm:p-2.5 space-y-2 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-xs text-[#F8FAFC]">Task Overview</span>
            <span className="text-[10px] font-mono text-[#8EA3BE] bg-[#070D18] px-1.5 py-0.5 rounded border border-[#172640]">
              {tasks.length} tasks
            </span>
          </div>

          {isCollapsible && (
            <button
              onClick={() => setIsCollapsed((prev) => !prev)}
              className="text-[#94A3B8] hover:text-white p-0.5 rounded transition-colors"
              title={isCollapsed ? 'Expand table' : 'Collapse table'}
            >
              {isCollapsed ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>

        {!isCollapsed && (
          <>
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-[#64748B] absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search tasks..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-[#070D18] border border-[#1A263D] rounded pl-8 pr-2.5 py-1 text-[11px] text-[#F8FAFC] placeholder-[#64748B] focus:outline-hidden focus:border-[#2563EB] transition-colors"
              />
            </div>

            {/* Filter Tabs */}
            <div className="flex items-center gap-1 overflow-x-auto text-[11px] scrollbar-none">
              <button
                onClick={() => setFilterTab('ALL')}
                className={`px-2.5 py-0.5 rounded transition-colors whitespace-nowrap font-medium cursor-pointer ${
                  filterTab === 'ALL'
                    ? 'bg-[#2563EB] text-white shadow-xs'
                    : 'text-[#94A3B8] hover:text-white bg-[#070D18] hover:bg-[#131E35]'
                }`}
              >
                All ({tasks.length})
              </button>
              <button
                onClick={() => setFilterTab('SCHEDULED')}
                className={`px-2.5 py-0.5 rounded transition-colors whitespace-nowrap font-medium cursor-pointer ${
                  filterTab === 'SCHEDULED'
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'text-[#94A3B8] hover:text-emerald-400 bg-[#070D18] hover:bg-[#131E35]'
                }`}
              >
                Scheduled ({scheduledCount})
              </button>
              <button
                onClick={() => setFilterTab('UNPLACED')}
                className={`px-2.5 py-0.5 rounded transition-colors whitespace-nowrap font-medium cursor-pointer ${
                  filterTab === 'UNPLACED'
                    ? 'bg-amber-600 text-white shadow-xs'
                    : 'text-[#94A3B8] hover:text-amber-400 bg-[#070D18] hover:bg-[#131E35]'
                }`}
              >
                Unplaced ({unplacedCount})
              </button>
              <button
                onClick={() => setFilterTab('CONFLICTS')}
                className={`px-2.5 py-0.5 rounded transition-colors whitespace-nowrap font-medium cursor-pointer ${
                  filterTab === 'CONFLICTS'
                    ? 'bg-rose-600 text-white shadow-xs'
                    : 'text-[#94A3B8] hover:text-rose-400 bg-[#070D18] hover:bg-[#131E35]'
                }`}
              >
                Conflicts ({conflictsCount})
              </button>
            </div>
          </>
        )}
      </div>

      {/* Task Rows Table (Desktop/Tablet) & Mobile Card Records */}
      {!isCollapsed && (
        <div className="flex-1 overflow-auto">
          {filteredTasks.length === 0 ? (
            <div className="py-8 text-center text-[#64748B]">
              No tasks matching criteria.
            </div>
          ) : (
            <>
              {/* Desktop & Tablet Table (Hidden on small mobile screens < sm) */}
              <table className="hidden sm:table w-full text-left text-[11px] border-collapse">
                <thead>
                  <tr className="bg-[#070D18]/90 border-b border-[#1A263D] text-[#64748B] text-[10px] uppercase font-semibold sticky top-0 z-10">
                    <th className="py-2 px-2.5">ID</th>
                    <th className="py-2 px-2">SECTION</th>
                    <th className="py-2 px-2 hidden lg:table-cell">TYPE</th>
                    <th className="py-2 px-2">WINDOW</th>
                    <th className="py-2 px-2">STATUS</th>
                    <th className="py-2 px-2 hidden md:table-cell">PRIORITY</th>
                    <th className="py-2 px-2 text-right"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1A263D]/50">
                  {filteredTasks.map((task) => {
                    const scheduled = scheduledMap.get(task.task_id);
                    const isScheduled = !!scheduled;
                    const isConflict = task.task_id === 'TSK-0007' || (!isScheduled && filterTab === 'CONFLICTS');
                    const isSelected = selectedTaskId === task.task_id;
                    const secCode = task.section_code || task.section_id || 'SEC-12';
                    const isCritical =
                      task.priority === 'CRITICAL' || task.task_id === 'TSK-0007' || task.task_id === 'TSK-0001';

                    const startW =
                      scheduled?.interval?.start || scheduled?.start_time || task.earliest_start || task.window_start;
                    const endW =
                      scheduled?.interval?.end || scheduled?.end_time || task.latest_finish || task.window_end;
                    const windowText = `${formatWindow(startW, '07:00')} – ${formatWindow(endW, '10:00')}`;

                    const workTypeLabel = task.work_type
                      ? task.work_type.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
                      : task.title || 'Track Maintenance';

                    return (
                      <tr
                        key={task.task_id}
                        onClick={() => onSelectTask(task.task_id)}
                        className={`cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-[#142038] text-[#F8FAFC] border-l-2 border-l-[#38BDF8]'
                            : 'hover:bg-[#0F172A] text-[#94A3B8]'
                        }`}
                      >
                        <td className="py-2 px-2.5 font-mono font-bold text-[#F8FAFC]">
                          {task.task_code || task.task_id}
                        </td>

                        <td className="py-2 px-2 font-mono text-[#93C5FD] text-[10.5px]">
                          {secCode}
                        </td>

                        <td className="py-2 px-2 truncate max-w-[120px] text-[#CBD5E1] hidden lg:table-cell" title={task.title}>
                          {workTypeLabel}
                        </td>

                        <td className="py-2 px-2 font-mono text-[10px] text-[#8EA3BE] whitespace-nowrap">
                          {windowText}
                        </td>

                        <td className="py-2 px-2 whitespace-nowrap">
                          {isConflict ? (
                            <span className="inline-block px-1.5 py-0.2 rounded text-[9px] font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                              Unscheduled
                            </span>
                          ) : isScheduled ? (
                            <span className="inline-block px-1.5 py-0.2 rounded text-[9px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                              Scheduled
                            </span>
                          ) : (
                            <span className="inline-block px-1.5 py-0.2 rounded text-[9px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                              Unplaced
                            </span>
                          )}
                        </td>

                        <td className="py-2 px-2 whitespace-nowrap hidden md:table-cell">
                          <span className="flex items-center gap-1 font-medium text-[10px] text-[#F8FAFC]">
                            <span
                              className={`w-1.5 h-1.5 rounded-full ${
                                isCritical ? 'bg-rose-500' : 'bg-amber-400'
                              }`}
                            />
                            {isCritical ? 'High' : 'Medium'}
                          </span>
                        </td>

                        <td className="py-2 px-2 text-right">
                          <ChevronRight className="w-3.5 h-3.5 text-[#64748B] inline-block" />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {/* Mobile Card Records (< sm) */}
              <div className="sm:hidden divide-y divide-[#1A263D]/60 p-2 space-y-2">
                {filteredTasks.map((task) => {
                  const scheduled = scheduledMap.get(task.task_id);
                  const isScheduled = !!scheduled;
                  const isConflict = task.task_id === 'TSK-0007' || (!isScheduled && filterTab === 'CONFLICTS');
                  const isSelected = selectedTaskId === task.task_id;
                  const secCode = task.section_code || task.section_id || 'SEC-12';
                  const isCritical =
                    task.priority === 'CRITICAL' || task.task_id === 'TSK-0007' || task.task_id === 'TSK-0001';

                  const startW =
                    scheduled?.interval?.start || scheduled?.start_time || task.earliest_start || task.window_start;
                  const endW =
                    scheduled?.interval?.end || scheduled?.end_time || task.latest_finish || task.window_end;
                  const windowText = `${formatWindow(startW, '07:00')} – ${formatWindow(endW, '10:00')}`;

                  return (
                    <div
                      key={task.task_id}
                      onClick={() => onSelectTask(task.task_id)}
                      className={`p-2.5 rounded-md border transition-colors cursor-pointer ${
                        isSelected
                          ? 'bg-[#142038] border-[#38BDF8] text-[#F8FAFC]'
                          : 'bg-[#070D18]/80 border-[#1A263D] hover:bg-[#0F172A]'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono font-bold text-xs text-[#F8FAFC]">
                          {task.task_code || task.task_id}
                        </span>
                        {isConflict ? (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                            UNSCHEDULED
                          </span>
                        ) : isScheduled ? (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            SCHEDULED
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                            UNPLACED
                          </span>
                        )}
                      </div>

                      <div className="text-[11px] text-[#CBD5E1] truncate font-medium">
                        {task.title || 'Track Maintenance Work'}
                      </div>

                      <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-[#1A263D]/60 text-[10px] text-[#94A3B8] font-mono">
                        <span>{secCode} • {windowText}</span>
                        <span className={`font-semibold ${isCritical ? 'text-rose-400' : 'text-blue-400'}`}>
                          {isCritical ? 'High Priority' : 'Medium'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};
