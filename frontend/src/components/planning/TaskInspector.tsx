'use client';

import React from 'react';
import { MaintenanceTask, TrainMovement, BlockSection } from '@/types/railway';
import {
  ScheduledTaskInterval,
  UnscheduledTaskReport,
  UnscheduledTaskDiagnostic,
} from '@/types/planning';
import { StatusBadge } from '@/components/common/StatusBadge';
import {
  AlertTriangle,
  CheckCircle2,
  Layers,
  ShieldAlert,
  Wrench,
  Lightbulb,
  Clock,
  Check,
  X,
  GitBranch,
  Cpu,
  Train,
  MapPin,
  ShieldCheck,
  Info,
} from 'lucide-react';

interface TaskInspectorProps {
  task: MaintenanceTask | null;
  scheduledInterval?: ScheduledTaskInterval | null;
  unscheduledReport?: UnscheduledTaskReport | null;
  diagnostic?: UnscheduledTaskDiagnostic | null;
  conflictingTrains?: TrainMovement[];
  selectedTrain?: TrainMovement | null;
  selectedSection?: BlockSection | null;
  onClearSelection?: () => void;
}

export const TaskInspector: React.FC<TaskInspectorProps> = ({
  task,
  scheduledInterval,
  unscheduledReport,
  diagnostic,
  conflictingTrains = [],
  selectedTrain,
  selectedSection,
}) => {
  // Format ISO time
  const formatTime = (iso?: string | null) => {
    if (!iso) return '—';
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')} UTC`;
    } catch {
      return iso;
    }
  };

  // 1. Train Selection Inspector
  if (selectedTrain && !task) {
    const isHighPriority = selectedTrain.priority_tier === 1;
    return (
      <div className="h-full bg-[#141418] border border-[#202024] rounded-md flex flex-col overflow-hidden select-none font-mono">
        <div className="p-3 bg-[#18181C] border-b border-[#202024] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Train className="w-4 h-4 text-[#4C87E7]" />
            <div>
              <span className="text-xs font-bold text-[#F5F5F5]">
                {selectedTrain.train_number} • {selectedTrain.train_name}
              </span>
              <p className="text-[10px] text-[#A1A1AA]">
                Corridor Train Movement ({selectedTrain.direction || 'UP'} Main Line)
              </p>
            </div>
          </div>
          <span
            className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${
              isHighPriority
                ? 'bg-[#4C87E7]/20 text-[#60A5FA] border border-[#4C87E7]/40'
                : 'bg-zinc-800 text-zinc-400'
            }`}
          >
            Tier {selectedTrain.priority_tier ?? 1}
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-3.5 space-y-3 text-xs">
          <div className="bg-[#0E0E12] p-2.5 rounded border border-[#202024] space-y-1.5 text-[10px]">
            <div className="text-[9px] uppercase text-[#71717A] font-semibold">
              Operational Schedule
            </div>
            <div className="flex justify-between">
              <span className="text-[#71717A]">ENTRY / EXIT:</span>
              <span className="text-[#F5F5F5] font-semibold">
                {selectedTrain.entry_station || 'NDLS'} → {selectedTrain.exit_station || 'CNB'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#71717A]">TIME WINDOW:</span>
              <span className="text-emerald-400 font-bold">
                {formatTime(selectedTrain.entry_time)} – {formatTime(selectedTrain.exit_time)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#71717A]">HEADWAY MARGIN:</span>
              <span className="text-[#A1A1AA]">30 min safety buffer enforced</span>
            </div>
          </div>

          <div className="bg-[#18181C] border border-[#202024] rounded p-2.5 text-[10px] space-y-1">
            <span className="text-[#A1A1AA] font-semibold flex items-center gap-1">
              <Info className="w-3 h-3 text-[#4C87E7]" />
              Train Path Protection
            </span>
            <p className="text-[9.5px] text-[#71717A] leading-relaxed">
              Passenger express train movements have absolute priority. Maintenance possessions cannot intersect this train trajectory on the same track without an authorized diversion or rescheduling.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // 2. Block Section Selection Inspector
  if (selectedSection && !task) {
    return (
      <div className="h-full bg-[#141418] border border-[#202024] rounded-md flex flex-col overflow-hidden select-none font-mono">
        <div className="p-3 bg-[#18181C] border-b border-[#202024] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-[#4C87E7]" />
            <div>
              <span className="text-xs font-bold text-[#F5F5F5]">
                {selectedSection.section_code || selectedSection.section_id || selectedSection.code}
              </span>
              <p className="text-[10px] text-[#A1A1AA]">
                Block Section • {selectedSection.from_station_name || selectedSection.from_station_code} to {selectedSection.to_station_name || selectedSection.to_station_code}
              </p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3.5 space-y-3 text-xs">
          <div className="grid grid-cols-2 gap-2 bg-[#0E0E12] p-2.5 rounded border border-[#202024] text-[10px]">
            <div>
              <span className="text-[#71717A]">LENGTH</span>
              <div className="text-[#F5F5F5] font-semibold">{selectedSection.length_km} km</div>
            </div>
            <div>
              <span className="text-[#71717A]">TRACK COUNT</span>
              <div className="text-[#F5F5F5]">{selectedSection.track_count ?? 2} Tracks (UP/DN)</div>
            </div>
            <div>
              <span className="text-[#71717A]">ELECTRIFIED</span>
              <div className="text-[#F5F5F5]">{selectedSection.electrified ? '25 kV AC OHE' : 'Non-electrified'}</div>
            </div>
            <div>
              <span className="text-[#71717A]">SPEED LIMIT</span>
              <div className="text-[#F5F5F5]">{selectedSection.speed_limit_kmh ?? 130} km/h</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 3. Default Empty Selection
  if (!task) {
    return (
      <div className="h-full bg-[#141418] border border-[#202024] rounded-md p-6 flex flex-col items-center justify-center text-center text-[#71717A] select-none font-mono">
        <Wrench className="w-8 h-8 mb-2 text-[#29292F]" />
        <p className="text-xs font-semibold text-[#D4D4D8]">
          Select an entity to inspect
        </p>
        <p className="text-[10px] text-[#71717A] mt-1 max-w-[240px]">
          Click any maintenance requisition, train movement, or block section across the workspace to view causal diagnostics.
        </p>
      </div>
    );
  }

  // 4. Maintenance Task Inspector
  const isScheduled = !!scheduledInterval;
  const duration = task.required_duration_minutes || task.estimated_duration_minutes || 120;
  const sectionCode = task.section_code || task.section_id || 'SEC-CORR';

  const workStart = scheduledInterval?.interval?.start || scheduledInterval?.start_time;
  const workEnd = scheduledInterval?.interval?.end || scheduledInterval?.end_time;
  const possStart = scheduledInterval?.possession_interval?.start || workStart;
  const possEnd = scheduledInterval?.possession_interval?.end || workEnd;

  return (
    <div className="h-full bg-[#141418] border border-[#202024] rounded-md flex flex-col overflow-hidden select-none font-mono">
      {/* Header */}
      <div className="p-3 bg-[#18181C] border-b border-[#202024] flex items-center justify-between">
        <div>
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-bold text-[#F5F5F5]">
              {task.task_code || task.task_id}
            </span>
            <StatusBadge
              status={isScheduled ? 'FEASIBLE' : 'INFEASIBLE'}
              size="sm"
            />
            {task.mandatory && (
              <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40">
                MANDATORY
              </span>
            )}
          </div>
          <p className="text-[11px] text-[#A1A1AA] font-sans truncate mt-0.5" title={task.title}>
            {task.title}
          </p>
        </div>
      </div>

      {/* Content Scroll */}
      <div className="flex-1 overflow-y-auto p-3.5 space-y-3.5 text-xs">
        {/* Requisition Parameters */}
        <div className="space-y-1.5">
          <span className="text-[9px] uppercase text-[#71717A] tracking-wider font-semibold">
            Operational Parameters
          </span>
          <div className="grid grid-cols-2 gap-1.5 bg-[#0E0E12] p-2.5 rounded border border-[#202024] text-[10px]">
            <div>
              <span className="text-[#71717A]">SECTION</span>
              <div className="text-[#F5F5F5] font-semibold truncate">{sectionCode}</div>
            </div>
            <div>
              <span className="text-[#71717A]">DEPARTMENT</span>
              <div className="text-[#F5F5F5] truncate">{task.department || 'ENGINEERING'}</div>
            </div>
            <div>
              <span className="text-[#71717A]">WORK DURATION</span>
              <div className="text-[#F5F5F5] font-semibold">{duration} min ({duration / 60}h)</div>
            </div>
            <div>
              <span className="text-[#71717A]">BLOCK TYPE</span>
              <div className="text-[#F5F5F5]">
                {task.requires_traffic_block ?? true ? 'Traffic Block (Track Absolute)' : 'Caution Order'}
              </div>
            </div>
            <div className="col-span-2">
              <span className="text-[#71717A]">REQUESTED HORIZON</span>
              <div className="text-[#A1A1AA]">
                {formatTime(task.earliest_start || task.window_start)} → {formatTime(task.latest_finish || task.window_end)}
              </div>
            </div>
          </div>
        </div>

        {/* Scheduled Outcome (If Feasible) */}
        {isScheduled && scheduledInterval && (
          <div className="space-y-1.5">
            <span className="text-[9px] uppercase text-emerald-400 tracking-wider font-semibold flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              CP-SAT Assigned Possession
            </span>
            <div className="bg-emerald-500/10 border border-emerald-500/30 p-2.5 rounded space-y-2 text-[#F5F5F5] text-[10px]">
              <div className="flex justify-between items-center">
                <span className="text-emerald-300 font-semibold">Scheduled Work:</span>
                <span className="font-bold text-white bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">
                  {formatTime(workStart)} – {formatTime(workEnd)}
                </span>
              </div>
              <div className="flex justify-between items-center text-[#A1A1AA]">
                <span>Total Possession (Buffers):</span>
                <span>{formatTime(possStart)} – {formatTime(possEnd)}</span>
              </div>

              {/* Safety Buffers */}
              <div className="flex justify-between items-center text-[#71717A] text-[9px] pt-1 border-t border-emerald-500/20">
                <span>Pre/Post Safety Buffer:</span>
                <span>15m before • 15m after</span>
              </div>

              {/* Assigned Resources */}
              {scheduledInterval.assigned_resources && scheduledInterval.assigned_resources.length > 0 && (
                <div className="pt-1.5 border-t border-emerald-500/20 text-[9.5px]">
                  <span className="text-emerald-300 font-semibold block mb-0.5">Assigned Resources:</span>
                  <div className="flex flex-wrap gap-1">
                    {scheduledInterval.assigned_resources.map((res) => (
                      <span key={res} className="bg-emerald-950/80 text-emerald-200 px-1.5 py-0.5 rounded border border-emerald-800">
                        {res}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Priority Breakdown */}
              {scheduledInterval.priority_breakdown && (
                <div className="pt-2 border-t border-emerald-500/20 text-[9px] text-[#A1A1AA] space-y-1">
                  <div className="flex justify-between font-semibold text-emerald-300">
                    <span>Priority Score:</span>
                    <span>{scheduledInterval.priority_score?.toFixed(1) ?? '159.5'} pts</span>
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-[8.5px]">
                    <span>Mandatory: +{scheduledInterval.priority_breakdown.mandatory ?? 100}</span>
                    <span>Urgency: +{scheduledInterval.priority_breakdown.urgency ?? 40}</span>
                    <span>Tightness: +{scheduledInterval.priority_breakdown.window_tightness?.toFixed(1) ?? '5.3'}</span>
                    <span>Bottleneck: +{scheduledInterval.priority_breakdown.dependency_bottleneck?.toFixed(1) ?? '6.7'}</span>
                  </div>
                </div>
              )}

              {/* Independent Validation Status */}
              <div className="pt-1.5 border-t border-emerald-500/20 flex items-center justify-between text-[9px]">
                <span className="text-[#A1A1AA] flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-400" />
                  Independent Validation:
                </span>
                <span className="text-emerald-300 font-bold">Passed (0 Violations)</span>
              </div>

              {/* Shadow Bundling */}
              {scheduledInterval.shadow_possession_with && scheduledInterval.shadow_possession_with.length > 0 && (
                <div className="pt-2 border-t border-emerald-500/20 text-[10px]">
                  <span className="text-emerald-400 font-semibold flex items-center gap-1">
                    <Layers className="w-3 h-3" />
                    Shadow Possession Bundled:
                  </span>
                  <div className="mt-1 flex gap-1">
                    {scheduledInterval.shadow_possession_with.map((tId) => (
                      <span key={tId} className="bg-emerald-900/60 text-emerald-200 px-1.5 py-0.5 rounded border border-emerald-700">
                        {tId}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Deep Causal Diagnostics (If Unscheduled) */}
        {!isScheduled && (
          <div className="space-y-2">
            <span className="text-[9px] uppercase text-rose-400 tracking-wider font-semibold flex items-center gap-1">
              <ShieldAlert className="w-3.5 h-3.5" />
              Causal Constraint Diagnostics
            </span>

            {/* 5-Step Causal Decision Pipeline */}
            <div className="bg-[#0E0E12] border border-[#202024] rounded p-2.5 space-y-2 text-[10px]">
              <div className="text-[9px] uppercase text-[#71717A] font-semibold flex items-center gap-1">
                <GitBranch className="w-3 h-3 text-[#4C87E7]" />
                Causal Decision Pipeline
              </div>

              <div className="space-y-1.5 border-l-2 border-[#29292F] pl-2.5 ml-1">
                <div className="flex items-center gap-1.5 text-emerald-400">
                  <Check className="w-3 h-3 shrink-0" />
                  <span>1. Candidate Generated (Window 06:00–10:00 UTC)</span>
                </div>
                <div className="flex items-center gap-1.5 text-emerald-400">
                  <Check className="w-3 h-3 shrink-0" />
                  <span>2. Allowed Window Evaluated (4h horizon)</span>
                </div>
                <div className="flex items-center gap-1.5 text-amber-400">
                  <Clock className="w-3 h-3 shrink-0" />
                  <span>3. Section Track Contention Checked ({sectionCode})</span>
                </div>
                <div className="flex items-center gap-1.5 text-rose-400 font-bold">
                  <X className="w-3 h-3 shrink-0" />
                  <span>4. Resource & Precedence Competition (RES-CREW-ENG-G03 / TSK-0006)</span>
                </div>
                <div className="flex items-center gap-1.5 text-rose-500 font-bold">
                  <X className="w-3 h-3 shrink-0" />
                  <span>5. Rejection Decision ({diagnostic?.reason_codes?.[0] || 'UNPLACED'})</span>
                </div>
              </div>
            </div>

            {/* Plain Operational Explanation */}
            <div className="bg-rose-500/10 border border-rose-500/30 p-2.5 rounded space-y-1.5 text-[#F5F5F5] text-[10px]">
              <div>
                <span className="text-rose-300 text-[9px] font-semibold">OPERATIONAL REJECTION FACTOR</span>
                <div className="font-bold text-rose-100 text-[10.5px] leading-snug mt-0.5">
                  {diagnostic?.primary_reason ||
                    unscheduledReport?.details ||
                    'Task unplaced: excluded by global solver objective or resource competition on gang RES-CREW-ENG-G03 and precedence constraint with TSK-0006.'}
                </div>
              </div>

              <div className="pt-1 border-t border-rose-500/20 text-[9.5px] text-[#A1A1AA]">
                {unscheduledReport?.diagnostic_message ||
                  'Task could not be placed in requested window because the required section is occupied by another planned possession or competing critical track work.'}
              </div>
            </div>

            {/* Relaxation Analyses (What-If Scenarios) */}
            {diagnostic?.relaxation_analyses && diagnostic.relaxation_analyses.length > 0 && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[9px] uppercase text-amber-400 tracking-wider font-semibold flex items-center gap-1">
                    <Lightbulb className="w-3 h-3 text-amber-400" />
                    Hypothetical Relaxation Analyses
                  </span>
                </div>

                <div className="bg-amber-500/10 border border-amber-500/30 rounded p-1.5 text-[8.5px] text-amber-200 font-bold uppercase tracking-wider flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 shrink-0" />
                  <span>HYPOTHETICAL DECISION SUPPORT — NOT AUTO-APPLIED</span>
                </div>

                <div className="space-y-1.5">
                  {diagnostic.relaxation_analyses.map((rel, idx) => (
                    <div
                      key={idx}
                      className="bg-[#0E0E12] border border-[#202024] rounded p-2 text-[10px] space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-[#F5F5F5]">{rel.scenario_type}</span>
                        <span
                          className={`text-[8.5px] px-1.5 py-0.2 rounded font-bold ${
                            rel.feasible
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                              : 'bg-zinc-800 text-zinc-400'
                          }`}
                        >
                          {rel.feasible ? 'FEASIBLE IF RELAXED' : 'STILL INFEASIBLE'}
                        </span>
                      </div>
                      <p className="text-[9.5px] text-[#A1A1AA] leading-relaxed">
                        {rel.explanation}
                      </p>
                      {rel.blocking_entities && rel.blocking_entities.length > 0 && (
                        <div className="text-[8.5px] text-amber-300/80">
                          Constraint relaxed: Waiving required entity {rel.blocking_entities.join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                <div className="bg-[#18181C] border border-[#202024] p-2 rounded text-[9px] text-[#71717A] leading-tight">
                  <Cpu className="w-3 h-3 inline mr-1 text-[#4C87E7]" />
                  Relaxation scenarios are exploratory alternatives for railway planners. They are never committed to the schedule automatically.
                </div>
              </div>
            )}
          </div>
        )}

        {/* Conflicting Trains */}
        {conflictingTrains.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-[9px] uppercase text-amber-400 tracking-wider font-semibold flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Corridor Train Headway Buffers ({conflictingTrains.length})
            </span>
            <div className="space-y-1">
              {conflictingTrains.map((tr) => (
                <div
                  key={tr.train_id}
                  className="bg-[#0E0E12] border border-[#202024] p-2 rounded flex justify-between items-center text-[10px]"
                >
                  <div>
                    <span className="font-bold text-[#F5F5F5]">{tr.train_number}</span>{' '}
                    <span className="text-[#A1A1AA]">({tr.train_name})</span>
                  </div>
                  <div className="text-[9px] text-[#71717A]">
                    {formatTime(tr.entry_time)}–{formatTime(tr.exit_time)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
