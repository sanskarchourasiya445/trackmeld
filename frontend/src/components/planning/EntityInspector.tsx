'use client';

import React, { useState } from 'react';
import { MaintenanceTask, TrainMovement, BlockSection, TrainTraversal, formatTrackSpatial } from '@/types/railway';
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
  Box,
  Eye,
  Radio,
  Zap,
  Activity,
  Layers,
  ArrowRight,
  Clock,
  Sparkles,
  GitBranch,
  ShieldAlert,
  Calendar,
  Gauge,
  CheckCircle2,
  Map as MapIcon,
} from 'lucide-react';

export interface ContextualStation {
  code: string;
  name: string;
  distance_km: number;
  track_count?: number;
  facilities?: string[];
  division?: string;
}

export interface ContextualConflict {
  conflict_id: string;
  severity: 'CRITICAL' | 'MAJOR' | 'MINOR';
  title: string;
  location: string;
  time_window: string;
  reason: string;
  impact_summary: string;
  affected_trains: string[];
  affected_tasks: string[];
  recommended_action: string;
}

export interface ContextualSignal {
  id: string;
  type: string;
  aspect: string;
  km: number;
  track: string;
  overlap_distance_m?: number;
  interlocking?: string;
}

export interface ContextualOHE {
  id: string;
  km: number;
  track: string;
  voltage_kv: number;
  feeder_zone: string;
  contact_wire_height_m?: number;
  neutral_section?: boolean;
}

interface EntityInspectorProps {
  task?: MaintenanceTask | null;
  scheduledInterval?: ScheduledTaskInterval | null;
  diagnostic?: UnscheduledTaskDiagnostic | null;
  conflictingTrains?: TrainMovement[];
  selectedTrain?: TrainMovement | null;
  selectedSection?: BlockSection | null;
  selectedStation?: ContextualStation | null;
  selectedConflict?: ContextualConflict | null;
  selectedSignal?: ContextualSignal | null;
  selectedOHE?: ContextualOHE | null;
  traversals?: TrainTraversal[];
  onClose?: () => void;
  onNavigateToDiagnostics?: (taskId: string) => void;
  onNavigateToConflicts?: (taskId: string) => void;
  onOpenDigitalTwin?: (sectionCode: string) => void;
  isDrawer?: boolean;
  hideHeader?: boolean;
}

export const EntityInspector: React.FC<EntityInspectorProps> = ({
  task,
  scheduledInterval,
  conflictingTrains = [],
  selectedTrain,
  selectedSection,
  selectedStation,
  selectedConflict,
  selectedSignal,
  selectedOHE,
  traversals = [],
  onClose,
  onNavigateToDiagnostics,
  onNavigateToConflicts,
  onOpenDigitalTwin,
  isDrawer = false,
  hideHeader = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'OVERVIEW' | 'TIMELINE' | 'CONSTRAINTS' | 'IMPACT'>('OVERVIEW');

  const isTask = !!task;
  const isTrain = !task && !!selectedTrain;
  const isSection = !task && !selectedTrain && !!selectedSection;
  const isStation = !task && !selectedTrain && !selectedSection && !!selectedStation;
  const isConflict = !task && !selectedTrain && !selectedSection && !selectedStation && !!selectedConflict;
  const isSignal = !task && !selectedTrain && !selectedSection && !selectedStation && !selectedConflict && !!selectedSignal;
  const isOHE = !task && !selectedTrain && !selectedSection && !selectedStation && !selectedConflict && !selectedSignal && !!selectedOHE;

  // Format ISO time helper
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

  const getEntityBadge = () => {
    if (isConflict) return { label: 'CONFLICT', color: 'bg-rose-500/20 text-rose-400 border-rose-500/40' };
    if (isTask) return { label: 'WORK ORDER', color: 'bg-amber-500/20 text-amber-400 border-amber-500/40' };
    if (isTrain) return { label: 'TRAIN MOVEMENT', color: 'bg-[#2563EB]/20 text-[#38BDF8] border-[#2563EB]/40' };
    if (isStation) return { label: 'STATION HUB', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' };
    if (isSection) return { label: 'TRACK SECTION', color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40' };
    return { label: 'INFRASTRUCTURE', color: 'bg-[#141F36] text-[#94A3B8] border-[#1E2D4A]' };
  };

  const badge = getEntityBadge();

  return (
    <aside
      aria-label="Contextual Entity Inspector"
      className={`h-full bg-[#0B1120] flex flex-col overflow-hidden select-none font-sans text-xs transition-all duration-200 ${
        isDrawer
          ? 'w-full'
          : isExpanded
          ? 'w-full md:w-[480px]'
          : 'w-full'
      }`}
    >
      {/* 1. Standardized Inspector Header */}
      {!hideHeader && (
        <div className="h-10 bg-[#070D18] border-b border-[#1A263D] px-3.5 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-bold text-[#F8FAFC] tracking-tight">Inspector</span>
            <span className={`text-[9.5px] font-mono font-bold px-2 py-0.5 rounded border ${badge.color}`}>
              {badge.label}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            {/* Quick 3D Digital Twin Button if section context exists */}
            {(selectedSection || task) && (
              <button
                onClick={() =>
                  onOpenDigitalTwin?.(
                    selectedSection?.code ||
                      selectedSection?.section_code ||
                      task?.section_code ||
                      task?.section_id ||
                      'SEC-12'
                  )
                }
                className="bg-[#2563EB]/20 hover:bg-[#2563EB]/30 text-[#38BDF8] border border-[#2563EB]/40 px-2 py-0.5 rounded text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                title="Launch high-fidelity 3D digital twin"
              >
                <Eye className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">3D Twin</span>
              </button>
            )}

            <button
              onClick={() => setIsExpanded((prev) => !prev)}
              className="p-1 rounded text-[#94A3B8] hover:text-white hover:bg-[#162238] transition-colors cursor-pointer"
              title={isExpanded ? 'Restore width' : 'Expand width'}
            >
              {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="p-1 rounded text-[#94A3B8] hover:text-white hover:bg-rose-500/20 hover:text-rose-400 transition-colors cursor-pointer"
                title="Close Inspector"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* 2. Content Tabs */}
      <div className="flex items-center border-b border-[#1A263D] bg-[#070D18]/60 px-3.5 py-1.5 gap-1.5 text-xs shrink-0 overflow-x-auto">
        {(['OVERVIEW', 'TIMELINE', 'CONSTRAINTS', 'IMPACT'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-2.5 py-1 rounded-md transition-colors font-medium whitespace-nowrap cursor-pointer ${
              activeTab === tab
                ? 'bg-[#162238] text-[#38BDF8] font-bold border border-[#2563EB]/40'
                : 'text-[#94A3B8] hover:text-[#CBD5E1]'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* 3. Main Body */}
      <div className="flex-1 overflow-y-auto p-3.5 space-y-3.5">
        {/* ============================================================ */}
        {/* A. CONFLICT INSPECTION VIEW                                   */}
        {/* ============================================================ */}
        {isConflict && selectedConflict && (
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-bold font-mono text-[#F8FAFC]">
                  {selectedConflict.conflict_id}
                </span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/40 font-mono">
                  {selectedConflict.severity} CONFLICT
                </span>
              </div>
              <h2 className="text-xs font-semibold text-rose-300 leading-normal">
                {selectedConflict.title}
              </h2>
            </div>

            {activeTab === 'OVERVIEW' && (
              <div className="space-y-3">
                <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-2.5 text-xs">
                  <div className="flex justify-between items-start">
                    <span className="text-[#64748B] uppercase text-[10px] font-bold">Location:</span>
                    <span className="font-mono text-[#F8FAFC] font-semibold text-right">
                      {selectedConflict.location}
                    </span>
                  </div>
                  <div className="flex justify-between items-start">
                    <span className="text-[#64748B] uppercase text-[10px] font-bold">Window:</span>
                    <span className="font-mono text-amber-400 text-right">
                      {selectedConflict.time_window}
                    </span>
                  </div>
                  <div className="pt-2 border-t border-[#1E2D4A] space-y-1">
                    <span className="text-[#64748B] uppercase text-[10px] font-bold block">Why (Root Cause):</span>
                    <p className="text-[11px] text-[#CBD5E1] leading-relaxed">
                      {selectedConflict.reason}
                    </p>
                  </div>
                </div>

                <div className="bg-[#141F36] border border-[#2563EB]/40 rounded-xl p-3.5 space-y-2">
                  <span className="text-[10px] font-mono font-bold text-[#38BDF8] uppercase tracking-wider block">
                    RECOMMENDED RESOLUTION (CP-SAT)
                  </span>
                  <p className="text-[11px] text-[#F8FAFC] leading-relaxed">
                    {selectedConflict.recommended_action}
                  </p>
                  <button
                    onClick={() => onNavigateToConflicts?.('TSK-0007')}
                    className="w-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white py-2 rounded-md font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer mt-1"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Auto-Resolve with CP-SAT</span>
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'TIMELINE' && (
              <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-3 font-mono text-xs">
                <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider">
                  TRAJECTORY OVERLAP TIMELINE
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between items-center bg-[#0A0E17] p-2.5 rounded-lg border border-[#1E2D4A]">
                    <span className="text-[#94A3B8]">Possession Slot Request:</span>
                    <span className="text-white font-bold">14:00 – 15:30 UTC</span>
                  </div>
                  <div className="flex justify-between items-center bg-[#0A0E17] p-2.5 rounded-lg border border-[#1E2D4A]">
                    <span className="text-[#94A3B8]">Train 02073 Traversal:</span>
                    <span className="text-rose-400 font-bold">14:20 – 14:38 UTC</span>
                  </div>
                  <div className="flex justify-between items-center bg-[#0A0E17] p-2.5 rounded-lg border border-rose-500/30 text-rose-300">
                    <span>Direct Overlap:</span>
                    <span className="font-bold">18 minutes</span>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'CONSTRAINTS' && (
              <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-2.5 text-xs">
                <span className="text-[10px] font-mono font-bold text-[#64748B] uppercase tracking-wider block">
                  VIOLATED STATUTORY CONSTRAINTS
                </span>
                <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-3 space-y-1 text-rose-300">
                  <div className="font-bold text-[11px] flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>RULE-HEADWAY-01: Express Spacing</span>
                  </div>
                  <p className="text-[10.5px] leading-relaxed text-rose-200">
                    Mandatory minimum 7.0 min headway margin between express passenger services and active work zone approach signals. Current buffer: 3.2 min.
                  </p>
                </div>
              </div>
            )}

            {activeTab === 'IMPACT' && (
              <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-2.5 text-xs">
                <span className="text-[10px] font-mono font-bold text-[#64748B] uppercase tracking-wider block">
                  DOWNSTREAM OPERATIONAL IMPACT
                </span>
                <div className="space-y-2">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[#94A3B8]">Trailing Express Delay:</span>
                    <span className="font-mono text-rose-400 font-bold">+14 minutes (TR-12424)</span>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[#94A3B8]">Platform Holding at Tundla:</span>
                    <span className="font-mono text-amber-400 font-bold">18 min gate occupancy</span>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[#94A3B8]">Passenger Punctuality Delta:</span>
                    <span className="font-mono text-rose-400 font-bold">-4.2% on Northern Trunk</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ============================================================ */}
        {/* B. WORK ORDER / TASK VIEW                                    */}
        {/* ============================================================ */}
        {isTask && (
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-bold font-mono text-[#F8FAFC]">
                  {task.task_code || task.task_id}
                </span>
                {scheduledInterval ? (
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                    SCHEDULED (CP-SAT)
                  </span>
                ) : (
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/40">
                    UNSCHEDULED
                  </span>
                )}
              </div>
              <h2 className="text-xs font-semibold text-[#CBD5E1] leading-normal">
                {task.title}
              </h2>
            </div>

            {activeTab === 'OVERVIEW' && (
              <div className="space-y-3">
                <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-2.5 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-[#64748B]">Section:</span>
                    <span className="font-mono text-[#F8FAFC] font-semibold">
                      {task.section_code || task.section_id || 'SEC-12'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[#64748B]">Location:</span>
                    <span className="font-mono text-[#38BDF8]">
                      {formatTrackSpatial(task)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[#64748B]">Department:</span>
                    <span className="text-[#F8FAFC]">
                      {task.department || 'ENGINEERING (P-WAY)'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[#64748B]">Duration Required:</span>
                    <span className="font-mono text-[#F8FAFC]">
                      {(task.required_duration_minutes || 180) / 60}h ({task.required_duration_minutes || 180}m)
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[#64748B]">Priority:</span>
                    <span className="font-mono text-rose-400 font-bold">
                      {task.priority || 'CRITICAL'}
                    </span>
                  </div>
                </div>

                {/* Possession Window & Schedule */}
                <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-2 text-xs">
                  <span className="text-[10px] font-mono font-bold text-[#64748B] uppercase tracking-wider block">
                    POSSESSION WINDOW & SCHEDULE
                  </span>
                  <div className="flex justify-between items-center">
                    <span className="text-[#64748B]">Allowed Window:</span>
                    <span className="font-mono text-[#93C5FD]">
                      {formatTime(task.earliest_start || task.window_start, '07:00')} –{' '}
                      {formatTime(task.latest_finish || task.window_end, '12:00')}
                    </span>
                  </div>
                  {scheduledInterval ? (
                    <div className="p-2.5 rounded-lg bg-emerald-950/30 border border-emerald-500/30 text-emerald-300 font-mono text-[11px] space-y-1">
                      <div className="flex justify-between">
                        <span>Assigned Start:</span>
                        <span className="font-bold">{formatTime(scheduledInterval.interval?.start || scheduledInterval.start_time)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Assigned End:</span>
                        <span className="font-bold">{formatTime(scheduledInterval.interval?.end || scheduledInterval.end_time)}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="p-2.5 rounded-lg bg-rose-950/30 border border-rose-500/30 text-rose-300 text-[11px]">
                      <span>Unplaced in Current Scenario</span>
                    </div>
                  )}
                </div>

                <button
                  onClick={() =>
                    onOpenDigitalTwin?.(task.section_code || task.section_id || 'SEC-12')
                  }
                  className="w-full bg-[#141F36] hover:bg-[#1A2846] text-[#38BDF8] border border-[#2563EB]/40 py-2.5 rounded-lg font-semibold text-xs flex items-center justify-center gap-2 transition-colors cursor-pointer"
                >
                  <Eye className="w-4 h-4" />
                  <span>Inspect Work Zone in 3D Digital Twin</span>
                </button>

                <div className="grid grid-cols-2 gap-2 pt-1">
                  <a
                    href={`/planning?subtab=TASKS&taskId=${task.task_id}`}
                    className="bg-[#0F172A] hover:bg-[#141F36] border border-[#1E2D4A] hover:border-[#2D436D] text-[#CBD5E1] hover:text-white py-2 rounded-lg font-medium text-[11px] flex items-center justify-center gap-1.5 transition-colors text-center"
                  >
                    <Layers className="w-3.5 h-3.5 text-[#38BDF8]" />
                    <span>Open in Planning</span>
                  </a>
                  <a
                    href={`/planning?subtab=MAP&taskId=${task.task_id}&section=${task.section_code || 'SEC-12'}`}
                    className="bg-[#0F172A] hover:bg-[#141F36] border border-[#1E2D4A] hover:border-[#2D436D] text-[#CBD5E1] hover:text-white py-2 rounded-lg font-medium text-[11px] flex items-center justify-center gap-1.5 transition-colors text-center"
                  >
                    <MapIcon className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Show on Map</span>
                  </a>
                </div>
              </div>
            )}

            {activeTab === 'TIMELINE' && (
              <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-3 font-mono text-xs">
                <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider block">
                  WINDOW & EXECUTION INTERVAL
                </span>
                <div className="space-y-2">
                  <div className="flex justify-between bg-[#0A0E17] p-2.5 rounded-lg border border-[#1E2D4A]">
                    <span className="text-[#94A3B8]">Requisition Window:</span>
                    <span className="text-[#93C5FD]">
                      {formatTime(task.earliest_start || task.window_start, '07:00')} –{' '}
                      {formatTime(task.latest_finish || task.window_end, '12:00')}
                    </span>
                  </div>
                  {scheduledInterval ? (
                    <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-500/30 text-emerald-300 space-y-1.5">
                      <div className="flex justify-between">
                        <span>Assigned Start:</span>
                        <span className="font-bold">{formatTime(scheduledInterval.interval?.start || scheduledInterval.start_time)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Assigned End:</span>
                        <span className="font-bold">{formatTime(scheduledInterval.interval?.end || scheduledInterval.end_time)}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="p-3 rounded-lg bg-rose-950/30 border border-rose-500/30 text-rose-300">
                      <span>Unplaced in candidate plan</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'CONSTRAINTS' && (
              <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-3 text-xs">
                <span className="text-[10px] font-mono font-bold text-[#64748B] uppercase tracking-wider block">
                  APPLICABLE CONSTRAINTS & RULES
                </span>
                <div className="space-y-2">
                  <div className="bg-[#0A0E17] p-2.5 rounded-lg border border-[#1E2D4A] flex justify-between">
                    <span className="text-[#94A3B8]">Traffic Block Required:</span>
                    <span className="font-mono text-emerald-400 font-bold">{task.requires_traffic_block ? 'YES' : 'NO'}</span>
                  </div>
                  <div className="bg-[#0A0E17] p-2.5 rounded-lg border border-[#1E2D4A] flex justify-between">
                    <span className="text-[#94A3B8]">OHE 25kV Isolation:</span>
                    <span className="font-mono text-amber-400 font-bold">{task.requires_ohe_isolation ? 'REQUIRED' : 'NONE'}</span>
                  </div>
                  <div className="bg-[#0A0E17] p-2.5 rounded-lg border border-[#1E2D4A] flex justify-between">
                    <span className="text-[#94A3B8]">Assigned Machinery:</span>
                    <span className="font-mono text-white">{task.machinery_required?.join(', ') || 'CSM-01'}</span>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'IMPACT' && (
              <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-2.5 text-xs">
                <span className="text-[10px] font-mono font-bold text-[#64748B] uppercase tracking-wider block">
                  OPERATIONAL CORRIDOR IMPACT
                </span>
                <div className="space-y-2">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[#94A3B8]">Track Availability Impact:</span>
                    <span className="font-mono text-white font-bold">1 Track Closed (UP Main)</span>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[#94A3B8]">Temporary Speed Restriction:</span>
                    <span className="font-mono text-amber-400 font-bold">45 km/h for 2.5 km</span>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[#94A3B8]">Average Freight Rescheduling:</span>
                    <span className="font-mono text-white font-bold">+22 min</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ============================================================ */}
        {/* C. TRAIN VIEW                                                */}
        {/* ============================================================ */}
        {isTrain && selectedTrain && (
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-bold font-mono text-[#F8FAFC]">
                  {selectedTrain.train_number}
                </span>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[#2563EB]/20 text-[#38BDF8] border border-[#2563EB]/40">
                  TIER {selectedTrain.priority_tier ?? 1} EXPRESS
                </span>
              </div>
              <h2 className="text-xs font-semibold text-[#CBD5E1]">
                {selectedTrain.train_name}
              </h2>
            </div>

            <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-2.5 text-xs">
              <div className="flex justify-between">
                <span className="text-[#64748B]">Route:</span>
                <span className="font-mono text-[#F8FAFC]">
                  {selectedTrain.entry_station || 'NDLS'} → {selectedTrain.exit_station || 'CNB'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Direction:</span>
                <span className="font-mono text-[#38BDF8]">
                  {selectedTrain.direction || 'UP'} MAIN LINE
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Speed:</span>
                <span className="font-mono text-emerald-400 font-bold">130 km/h</span>
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

        {/* ============================================================ */}
        {/* D. STATION VIEW                                              */}
        {/* ============================================================ */}
        {isStation && selectedStation && (
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-bold font-mono text-[#F8FAFC]">
                  {selectedStation.code}
                </span>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                  STATION HUB
                </span>
              </div>
              <h2 className="text-xs font-semibold text-[#CBD5E1]">
                {selectedStation.name}
              </h2>
            </div>

            <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-2.5 text-xs">
              <div className="flex justify-between">
                <span className="text-[#64748B]">Chainage:</span>
                <span className="font-mono text-[#F8FAFC]">km {selectedStation.distance_km}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Running Tracks:</span>
                <span className="font-mono text-[#38BDF8]">{selectedStation.track_count || 6} Lines</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Division:</span>
                <span className="font-mono text-[#F8FAFC]">{selectedStation.division || 'PRYJ'}</span>
              </div>
            </div>

            {selectedStation.facilities && (
              <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-2">
                <span className="text-[10px] font-mono font-bold text-[#64748B] uppercase tracking-wider block">
                  INTERLOCKING & FACILITIES
                </span>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {selectedStation.facilities.map((fac, idx) => (
                    <span
                      key={idx}
                      className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#141F36] text-[#93C5FD] border border-[#2D436D]"
                    >
                      {fac}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ============================================================ */}
        {/* E. TRACK SECTION VIEW                                        */}
        {/* ============================================================ */}
        {isSection && selectedSection && (
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-bold font-mono text-[#F8FAFC]">
                  {selectedSection.section_code || selectedSection.code}
                </span>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/40">
                  BLOCK SECTION
                </span>
              </div>
              <h2 className="text-xs font-semibold text-[#CBD5E1]">
                {selectedSection.from_station_code || 'NDLS'} → {selectedSection.to_station_code || 'GZB'}
              </h2>
            </div>

            <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-2.5 text-xs">
              <div className="flex justify-between">
                <span className="text-[#64748B]">Section Length:</span>
                <span className="font-mono text-[#F8FAFC]">{selectedSection.length_km} km</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Speed Limit:</span>
                <span className="font-mono text-emerald-400 font-bold">{selectedSection.speed_limit_kmh ?? 130} km/h</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Traction:</span>
                <span className="text-amber-400">25 kV AC Catenary</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Tracks:</span>
                <span className="text-[#F8FAFC]">{selectedSection.track_count ?? 2} (UP & DOWN Main)</span>
              </div>
            </div>

            <button
              onClick={() =>
                onOpenDigitalTwin?.(selectedSection.code || selectedSection.section_code || 'SEC-12')
              }
              className="w-full bg-[#141F36] hover:bg-[#1A2846] text-[#38BDF8] border border-[#2563EB]/40 py-2.5 rounded-lg font-semibold text-xs flex items-center justify-center gap-2 transition-colors cursor-pointer"
            >
              <Eye className="w-4 h-4" />
              <span>Launch 3D Digital Twin Inspection</span>
            </button>
          </div>
        )}

        {/* ============================================================ */}
        {/* F. RAILWAY SIGNAL VIEW                                       */}
        {/* ============================================================ */}
        {isSignal && selectedSignal && (
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-bold font-mono text-[#F8FAFC]">
                  {selectedSignal.id}
                </span>
                <span
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                    selectedSignal.aspect === 'green'
                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                      : selectedSignal.aspect === 'red'
                      ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
                      : 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                  }`}
                >
                  ASPECT: {selectedSignal.aspect.toUpperCase()}
                </span>
              </div>
              <h2 className="text-xs font-semibold text-[#CBD5E1]">
                {selectedSignal.type.replace(/_/g, ' ').toUpperCase()}
              </h2>
            </div>

            <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-2.5 text-xs">
              <div className="flex justify-between">
                <span className="text-[#64748B]">Corridor Kilometre:</span>
                <span className="font-mono text-[#F8FAFC]">km {selectedSignal.km.toFixed(1)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Assigned Track:</span>
                <span className="font-mono text-[#38BDF8]">{selectedSignal.track} Mainline</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Overlap Distance:</span>
                <span className="font-mono text-emerald-400 font-bold">{selectedSignal.overlap_distance_m || 180}m</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Interlocking:</span>
                <span className="text-[#F8FAFC]">{selectedSignal.interlocking || 'Electronic Interlocking (EI)'}</span>
              </div>
            </div>

            <button
              onClick={() => onOpenDigitalTwin?.('SEC-12')}
              className="w-full bg-[#141F36] hover:bg-[#1A2846] text-[#38BDF8] border border-[#2563EB]/40 py-2.5 rounded-lg font-semibold text-xs flex items-center justify-center gap-2 transition-colors cursor-pointer"
            >
              <Eye className="w-4 h-4" />
              <span>Inspect Signal Mast in 3D Digital Twin</span>
            </button>
          </div>
        )}

        {/* ============================================================ */}
        {/* G. CATENARY / OHE VIEW                                       */}
        {/* ============================================================ */}
        {isOHE && selectedOHE && (
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-bold font-mono text-[#F8FAFC]">
                  {selectedOHE.id}
                </span>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  {selectedOHE.voltage_kv} kV AC ENERGIZED
                </span>
              </div>
              <h2 className="text-xs font-semibold text-[#CBD5E1]">
                Traction Mast & Contact Wire Suspension
              </h2>
            </div>

            <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-xl p-3.5 space-y-2.5 text-xs">
              <div className="flex justify-between">
                <span className="text-[#64748B]">Location:</span>
                <span className="font-mono text-[#F8FAFC]">km {selectedOHE.km.toFixed(1)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Feeder Substation:</span>
                <span className="text-[#38BDF8]">{selectedOHE.feeder_zone} (Traction Power)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Wire Height:</span>
                <span className="font-mono text-emerald-400 font-bold">{selectedOHE.contact_wire_height_m || 5.60}m</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Neutral Section:</span>
                <span className="font-mono text-[#F8FAFC]">{selectedOHE.neutral_section ? 'YES (PTFE Isolator)' : 'NO (Continuous)'}</span>
              </div>
            </div>

            <button
              onClick={() => onOpenDigitalTwin?.('SEC-12')}
              className="w-full bg-[#141F36] hover:bg-[#1A2846] text-[#38BDF8] border border-[#2563EB]/40 py-2.5 rounded-lg font-semibold text-xs flex items-center justify-center gap-2 transition-colors cursor-pointer"
            >
              <Eye className="w-4 h-4" />
              <span>Inspect Catenary in 3D Digital Twin</span>
            </button>
          </div>
        )}

        {/* Empty State */}
        {!isTask && !isTrain && !isSection && !isStation && !isConflict && !isSignal && !isOHE && (
          <div className="py-20 flex flex-col items-center justify-center text-center text-[#64748B]">
            <Radio className="w-8 h-8 mb-2 text-[#1E2D4A] animate-pulse" />
            <p className="text-xs font-semibold text-[#CBD5E1]">Corridor Telemetry Ready</p>
            <p className="text-[11px] text-[#64748B] mt-1 max-w-[260px] leading-relaxed">
              Select any railway track section, train movement, station hub, or work order on the map to inspect live operational facts.
            </p>
          </div>
        )}
      </div>
    </aside>
  );
};
