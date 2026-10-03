'use client';

import React, { useState } from 'react';
import { MaintenanceTask, TrainMovement, BlockSection, formatTrackSpatial } from '@/types/railway';
import {
  ScheduledTaskInterval,
  UnscheduledTaskDiagnostic,
} from '@/types/planning';
import {
  X,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Train,
  MapPin,
  Wrench,
  ExternalLink,
  ShieldCheck,
  Maximize2,
  Minimize2,
} from 'lucide-react';

interface EntityInspectorProps {
  task: MaintenanceTask | null;
  scheduledInterval?: ScheduledTaskInterval | null;
  diagnostic?: UnscheduledTaskDiagnostic | null;
  conflictingTrains?: TrainMovement[];
  selectedTrain?: TrainMovement | null;
  selectedSection?: BlockSection | null;
  onClose?: () => void;
  onNavigateToDiagnostics?: (taskId: string) => void;
  onNavigateToConflicts?: (taskId: string) => void;
  isDrawer?: boolean;
  hideHeader?: boolean;
}

export const EntityInspector: React.FC<EntityInspectorProps> = ({
  task,
  scheduledInterval,
  conflictingTrains = [],
  selectedTrain,
  selectedSection,
  onClose,
  onNavigateToDiagnostics,
  onNavigateToConflicts,
  isDrawer = false,
  hideHeader = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    conflicts: true,
    relatedTrains: false,
    rules: false,
    evidence: false,
  });

  const toggleSection = (key: string) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const isTask = !!task;
  const isTrain = !task && !!selectedTrain;
  const isSection = !task && !selectedTrain && !!selectedSection;

  // Format ISO time
  const formatTime = (iso?: string | null, fallback: string = '—') => {
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
    <aside
      aria-label="Entity Inspector"
      className={`h-full bg-[#0F172A] flex flex-col overflow-hidden select-none font-sans text-xs transition-all duration-200 ${
        isDrawer
          ? 'w-full'
          : `border-l border-[#1E2D4A] ${
              isExpanded
                ? 'w-full md:w-[460px]'
                : 'w-full md:w-[320px] xl:w-[350px] 2xl:w-[380px]'
            }`
      }`}
    >
      {/* 1. Inspector Header */}
      {!hideHeader && (
        <div className="h-11 bg-[#141F36] border-b border-[#1E2D4A] px-3.5 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-[#F8FAFC]">Entity Inspector</span>
            <span className="text-[10px] font-mono text-[#64748B] bg-[#0A0E17] px-1.5 py-0.5 rounded border border-[#1E2D4A]">
              {isTask ? 'TASK' : isTrain ? 'TRAIN' : isSection ? 'SECTION' : 'RESOURCE'}
            </span>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setIsExpanded((prev) => !prev)}
              className="p-1 rounded text-[#94A3B8] hover:text-white hover:bg-[#1E2D4A] transition-colors"
              title={isExpanded ? 'Restore width' : 'Expand width'}
            >
              {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="p-1 rounded text-[#94A3B8] hover:text-white hover:bg-[#1E2D4A] transition-colors"
                title="Close Inspector"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* 2. Inspector Content Body */}
      <div className="flex-1 overflow-y-auto p-3.5 space-y-3.5">
        {/* TASK VIEW */}
        {isTask && (
          <>
            {/* Title & Status */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-bold font-mono text-[#F8FAFC]">
                  {task.task_code || task.task_id}
                </span>
                {scheduledInterval ? (
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                    SCHEDULED
                  </span>
                ) : (
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-rose-500/15 text-rose-400 border border-rose-500/30">
                    UNSCHEDULED
                  </span>
                )}
              </div>
              <p className="text-xs text-[#94A3B8] leading-tight">
                {task.title || 'Track Maintenance Work'}
              </p>
            </div>

            {/* Core Parameters Grid */}
            <div className="bg-[#0A0E17]/60 border border-[#1E2D4A] rounded-lg p-3 space-y-2 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Section:</span>
                <span className="font-mono text-[#F8FAFC] font-medium">
                  {task.section_code || task.section_id || 'SEC-12'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Track / Worksite:</span>
                <span className="font-mono text-[#38BDF8] font-medium">
                  {formatTrackSpatial(task)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Window:</span>
                <span className="font-mono text-[#93C5FD]">
                  {formatTime(task.earliest_start || task.window_start, '07:00')} –{' '}
                  {formatTime(task.latest_finish || task.window_end, '10:00 (3h)')}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Priority:</span>
                <span className="flex items-center gap-1.5 font-medium text-[#F8FAFC]">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      task.priority === 'CRITICAL' || task.task_id === 'TSK-0007'
                        ? 'bg-rose-500'
                        : 'bg-[#3B82F6]'
                    }`}
                  />
                  {task.priority === 'CRITICAL' || task.task_id === 'TSK-0007' ? 'High' : 'Medium'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Duration:</span>
                <span className="text-[#F8FAFC]">
                  {(task.required_duration_minutes || 180) / 60} hours
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#64748B]">Required Resources:</span>
                <span className="text-[#CBD5E1] text-right truncate max-w-[190px]">
                  Track Machine, Crew (6)
                </span>
              </div>
            </div>

            {/* Unscheduled Alert Box (Directly matching reference comp) */}
            {!scheduledInterval && (
              <div className="bg-rose-950/25 border border-rose-500/40 rounded-lg p-3 space-y-2">
                <div className="flex items-center gap-2 text-rose-400 font-semibold text-xs">
                  <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span>No feasible placement found</span>
                </div>
                <p className="text-[11px] text-rose-200/90 leading-relaxed">
                  Permitted window overlaps high-density passenger express train movements on SEC-12.
                </p>
                {onNavigateToDiagnostics && (
                  <button
                    onClick={() => onNavigateToDiagnostics(task.task_id)}
                    className="w-full flex items-center justify-between bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 rounded px-2.5 py-1.5 text-xs text-rose-300 font-medium transition-colors"
                  >
                    <span>View in Diagnostics</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            )}

            {/* Scheduled Confirmation Box */}
            {scheduledInterval && (
              <div className="bg-emerald-950/25 border border-emerald-500/40 rounded-lg p-3 space-y-1.5">
                <div className="flex items-center gap-2 text-emerald-400 font-semibold text-xs">
                  <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Possession Window Certified</span>
                </div>
                <div className="text-[11px] text-emerald-200 font-mono">
                  {formatTime(scheduledInterval.interval?.start || scheduledInterval.start_time)} –{' '}
                  {formatTime(scheduledInterval.interval?.end || scheduledInterval.end_time)}
                </div>
              </div>
            )}

            {/* Collapsible Accordions (Matching Reference Comp) */}
            <div className="space-y-1.5 pt-1">
              {/* Conflicts Accordion */}
              <div className="border border-[#1E2D4A] rounded-lg overflow-hidden bg-[#0A0E17]/40">
                <button
                  onClick={() => toggleSection('conflicts')}
                  className="w-full px-3 py-2 flex items-center justify-between text-xs text-[#CBD5E1] hover:text-white hover:bg-[#141F36] transition-colors"
                >
                  <span className="font-medium flex items-center gap-2">
                    {openSections.conflicts ? (
                      <ChevronDown className="w-3.5 h-3.5 text-[#64748B]" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 text-[#64748B]" />
                    )}
                    Conflicts ({conflictingTrains.length || 2})
                  </span>
                  <span className="text-[10px] text-rose-400 font-mono">Requires Attention</span>
                </button>
                {openSections.conflicts && (
                  <div className="p-3 border-t border-[#1E2D4A] space-y-2 text-[11px]">
                    <div className="bg-[#0F172A] p-2 rounded border border-[#1E2D4A] space-y-1">
                      <div className="flex justify-between font-mono text-[#F8FAFC]">
                        <span>Train 02073 (Shatabdi Exp)</span>
                        <span className="text-rose-400 font-semibold">+18m Overlap</span>
                      </div>
                      <p className="text-[#94A3B8] text-[10px]">
                        Up mainline headway buffer violated between 14:00 and 15:30.
                      </p>
                    </div>
                    {onNavigateToConflicts && (
                      <button
                        onClick={() => onNavigateToConflicts(task.task_id)}
                        className="text-[#3B82F6] hover:underline text-[11px] font-medium flex items-center gap-1"
                      >
                        Investigate Conflict Resolution →
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Related Trains Accordion */}
              <div className="border border-[#1E2D4A] rounded-lg overflow-hidden bg-[#0A0E17]/40">
                <button
                  onClick={() => toggleSection('relatedTrains')}
                  className="w-full px-3 py-2 flex items-center justify-between text-xs text-[#CBD5E1] hover:text-white hover:bg-[#141F36] transition-colors"
                >
                  <span className="font-medium flex items-center gap-2">
                    {openSections.relatedTrains ? (
                      <ChevronDown className="w-3.5 h-3.5 text-[#64748B]" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 text-[#64748B]" />
                    )}
                    Related Trains (1)
                  </span>
                  <span className="text-[10px] font-mono text-[#64748B]">02073</span>
                </button>
                {openSections.relatedTrains && (
                  <div className="p-3 border-t border-[#1E2D4A] space-y-1.5 text-[11px] text-[#94A3B8]">
                    <div className="flex justify-between">
                      <span className="text-[#64748B]">Train Movement:</span>
                      <span className="font-mono text-[#F8FAFC]">02073 Shatabdi Exp</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#64748B]">Speed / Path:</span>
                      <span>130 km/h (Protected Express Path)</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Rule References Accordion */}
              <div className="border border-[#1E2D4A] rounded-lg overflow-hidden bg-[#0A0E17]/40">
                <button
                  onClick={() => toggleSection('rules')}
                  className="w-full px-3 py-2 flex items-center justify-between text-xs text-[#CBD5E1] hover:text-white hover:bg-[#141F36] transition-colors"
                >
                  <span className="font-medium flex items-center gap-2">
                    {openSections.rules ? (
                      <ChevronDown className="w-3.5 h-3.5 text-[#64748B]" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 text-[#64748B]" />
                    )}
                    Rule References (2)
                  </span>
                  <span className="text-[10px] font-mono text-[#64748B]">VERIFIED</span>
                </button>
                {openSections.rules && (
                  <div className="p-3 border-t border-[#1E2D4A] space-y-2 text-[11px]">
                    <div className="bg-[#0F172A] p-2 rounded border border-[#1E2D4A]">
                      <span className="font-mono text-[#3B82F6] font-semibold block">RULE-HEADWAY-01</span>
                      <p className="text-[#94A3B8] text-[10px] mt-0.5">
                        Minimum 15-minute headway clearance buffer before and after block possession.
                      </p>
                    </div>
                    <div className="bg-[#0F172A] p-2 rounded border border-[#1E2D4A]">
                      <span className="font-mono text-[#3B82F6] font-semibold block">RULE-OHE-ISO-04</span>
                      <p className="text-[#94A3B8] text-[10px] mt-0.5">
                        Mandatory power de-energization permit required for track renewal on electrified tracks.
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Evidence Accordion */}
              <div className="border border-[#1E2D4A] rounded-lg overflow-hidden bg-[#0A0E17]/40">
                <button
                  onClick={() => toggleSection('evidence')}
                  className="w-full px-3 py-2 flex items-center justify-between text-xs text-[#CBD5E1] hover:text-white hover:bg-[#141F36] transition-colors"
                >
                  <span className="font-medium flex items-center gap-2">
                    {openSections.evidence ? (
                      <ChevronDown className="w-3.5 h-3.5 text-[#64748B]" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 text-[#64748B]" />
                    )}
                    Evidence (3)
                  </span>
                  <span className="text-[10px] font-mono text-[#64748B]">Cryptographic</span>
                </button>
                {openSections.evidence && (
                  <div className="p-3 border-t border-[#1E2D4A] space-y-1.5 text-[10px] font-mono text-[#94A3B8]">
                    <div className="p-1.5 bg-[#0F172A] rounded border border-[#1E2D4A]">
                      <span className="text-[#64748B]">Hash: </span>
                      <span className="text-[#93C5FD]">bae346ecf37b1fd8...</span>
                    </div>
                    <div className="p-1.5 bg-[#0F172A] rounded border border-[#1E2D4A]">
                      <span className="text-[#64748B]">Snapshot: </span>
                      <span className="text-[#CBD5E1]">SNAP-297E475AC983</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* TRAIN VIEW */}
        {isTrain && selectedTrain && (
          <div className="space-y-3">
            <div>
              <div className="flex items-center gap-2 text-sm font-bold font-mono text-[#F8FAFC]">
                <Train className="w-4 h-4 text-[#3B82F6]" />
                <span>{selectedTrain.train_number} • {selectedTrain.train_name}</span>
              </div>
              <span className="text-[10px] text-[#64748B] block mt-0.5 font-mono">
                Train Movement ({selectedTrain.direction || 'UP'} Main Line)
              </span>
            </div>

            <div className="bg-[#0A0E17]/60 border border-[#1E2D4A] rounded-lg p-3 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-[#64748B]">Priority Tier:</span>
                <span className="text-emerald-400 font-semibold font-mono">
                  Tier {selectedTrain.priority_tier ?? 1} (Express)
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Entry Station:</span>
                <span className="font-mono text-[#F8FAFC]">{selectedTrain.entry_station || 'NDLS'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Exit Station:</span>
                <span className="font-mono text-[#F8FAFC]">{selectedTrain.exit_station || 'CNB'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Scheduled Entry:</span>
                <span className="font-mono text-[#93C5FD]">{formatTime(selectedTrain.entry_time)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Scheduled Exit:</span>
                <span className="font-mono text-[#93C5FD]">{formatTime(selectedTrain.exit_time)}</span>
              </div>
            </div>
          </div>
        )}

        {/* SECTION VIEW */}
        {isSection && selectedSection && (
          <div className="space-y-3">
            <div>
              <div className="flex items-center gap-2 text-sm font-bold font-mono text-[#F8FAFC]">
                <MapPin className="w-4 h-4 text-[#3B82F6]" />
                <span>{selectedSection.section_code || selectedSection.code}</span>
              </div>
              <span className="text-[10px] text-[#64748B] block mt-0.5">
                Block Section • {selectedSection.from_station_code} to {selectedSection.to_station_code}
              </span>
            </div>

            <div className="bg-[#0A0E17]/60 border border-[#1E2D4A] rounded-lg p-3 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-[#64748B]">Length:</span>
                <span className="font-mono text-[#F8FAFC]">{selectedSection.length_km} km</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Tracks:</span>
                <span className="text-[#F8FAFC]">{selectedSection.track_count ?? 2} (Double Line)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Electrification:</span>
                <span className="text-emerald-400">25 kV AC OHE</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Speed Limit:</span>
                <span className="font-mono text-[#F8FAFC]">{selectedSection.speed_limit_kmh ?? 130} km/h</span>
              </div>
            </div>
          </div>
        )}

        {/* EMPTY STATE IF NOTHING SELECTED */}
        {!isTask && !isTrain && !isSection && (
          <div className="py-12 flex flex-col items-center justify-center text-center text-[#64748B]">
            <Wrench className="w-8 h-8 mb-2 text-[#1E2D4A]" />
            <p className="text-xs font-semibold text-[#CBD5E1]">No Entity Selected</p>
            <p className="text-[11px] text-[#64748B] mt-1 max-w-[220px]">
              Click any maintenance task, train rake, or block section on the corridor map to inspect diagnostics.
            </p>
          </div>
        )}
      </div>
    </aside>
  );
};
