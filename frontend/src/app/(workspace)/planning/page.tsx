'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { AppShell } from '@/components/shell/AppShell';
import { RailwayCanvas } from '@/components/railway/RailwayCanvas';
import { TimeSpaceChart } from '@/components/planning/TimeSpaceChart';
import { TimelineScheduleView } from '@/components/planning/TimelineScheduleView';
import { TaskInspector } from '@/components/planning/TaskInspector';
import { TaskQueueTable } from '@/components/planning/TaskQueueTable';
import { PlanApprovalModal } from '@/components/governance/PlanApprovalModal';
import { BenchmarkComparisonModal } from '@/components/planning/BenchmarkComparisonModal';
import { CopilotDrawer } from '@/components/copilot/CopilotDrawer';
import {
  getScenarioBundle,
  optimizeSchedule,
  validateSchedule,
  diagnoseSchedule,
  getPlanVersions,
  approvePlanVersion,
  rejectPlanVersion,
  DEMO_SCENARIO,
  DEMO_CORRIDOR,
  DEMO_TRAINS,
  DEMO_TASKS,
  DEMO_SCHEDULE_RESULT,
  DEMO_PLAN_VERSION,
  DEMO_VALIDATION_RESULT,
  DEMO_DIAGNOSTICS,
} from '@/lib/api/client';
import {
  Corridor,
  Scenario,
  TrainMovement,
  MaintenanceTask,
  BlockSection,
} from '@/types/railway';
import {
  ScheduleResult,
  PlanVersion,
  ScheduleValidationResult,
  DiagnosticsReport,
} from '@/types/planning';
import {
  Play,
  FileCheck,
  RefreshCw,
  AlertCircle,
  Clock,
  Layers,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function PlanningPage() {
  const [corridor, setCorridor] = useState<Corridor>(DEMO_CORRIDOR);
  const [scenario, setScenario] = useState<Scenario>(DEMO_SCENARIO);
  const [trains, setTrains] = useState<TrainMovement[]>(DEMO_TRAINS);
  const [tasks, setTasks] = useState<MaintenanceTask[]>(DEMO_TASKS);
  const [scheduleResult, setScheduleResult] = useState<ScheduleResult | null>(DEMO_SCHEDULE_RESULT);
  const [validationResult, setValidationResult] = useState<ScheduleValidationResult | null>(DEMO_VALIDATION_RESULT);
  const [diagnosticsReport, setDiagnosticsReport] = useState<DiagnosticsReport | null>(DEMO_DIAGNOSTICS);
  const [planVersion, setPlanVersion] = useState<PlanVersion | null>(DEMO_PLAN_VERSION);

  // Subnavigation tabs
  const [activeSubtab, setActiveSubtab] = useState<
    'RAILWAY' | 'TIMESPACE' | 'TASKS' | 'CONFLICTS' | 'VALIDATION' | 'DIAGNOSTICS' | 'COPILOT'
  >('RAILWAY');

  // Synchronized Selection
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>('TSK-0007');
  const [selectedTrainId, setSelectedTrainId] = useState<string | null>(null);
  const [selectedSectionCode, setSelectedSectionCode] = useState<string | null>('SEC-12');

  // Operations state
  const [isSolving, setIsSolving] = useState(false);
  const [solvingMessage, setSolvingMessage] = useState<string>('');
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [isBenchmarkOpen, setIsBenchmarkOpen] = useState(false);
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadInitialData() {
      try {
        const bundle = await getScenarioBundle('SCN-DEMO-001');
        if (cancelled) return;
        if (bundle.corridor) setCorridor(bundle.corridor);
        if (bundle.scenario) setScenario(bundle.scenario);
        if (bundle.trains && bundle.trains.length > 0) setTrains(bundle.trains);
        if (bundle.tasks && bundle.tasks.length > 0) setTasks(bundle.tasks);

        const versions = await getPlanVersions('SCN-DEMO-001');
        if (!cancelled && versions && versions.length > 0) {
          setPlanVersion(versions[0]);
        }
      } catch (err) {
        console.warn('Initial data load warning:', err);
      }
    }
    loadInitialData();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSelectTask = (taskId: string) => {
    setSelectedTaskId(taskId);
    setSelectedTrainId(null);
    const targetTask = tasks.find((t) => t.task_id === taskId);
    if (targetTask) {
      setSelectedSectionCode(targetTask.section_code || targetTask.section_id || null);
    }
  };

  const handleSelectTrain = (trainId: string) => {
    setSelectedTrainId(trainId);
    setSelectedTaskId(null);
  };

  const handleSelectSection = (sectionCode: string) => {
    setSelectedSectionCode(sectionCode);
  };

  // Full Optimization Pipeline
  const handleTriggerSolve = useCallback(async () => {
    setIsSolving(true);
    setErrorMessage(null);
    setSolvingMessage('Evaluating possession windows and train headway buffers...');
    try {
      const sched = await optimizeSchedule(scenario.scenario_id, 5.0);
      setScheduleResult(sched);
      setSolvingMessage('Independent Feasibility Certification: Auditing 12 hard constraints...');

      const val = await validateSchedule(scenario.scenario_id, sched);
      setValidationResult(val);
      setSolvingMessage('Running causal diagnostics...');

      const diag = await diagnoseSchedule(scenario.scenario_id, sched);
      setDiagnosticsReport(diag);

      const versions = await getPlanVersions(scenario.scenario_id);
      if (versions && versions.length > 0) {
        setPlanVersion(versions[0]);
      }
    } catch (err) {
      console.error('Solve pipeline error:', err);
      setErrorMessage('Optimization request failed. Preserving candidate schedule.');
    } finally {
      setIsSolving(false);
      setSolvingMessage('');
    }
  }, [scenario.scenario_id]);

  const handleApprove = async (payload: { reviewer_name: string; reviewer_role: string; approval_notes: string }) => {
    if (!planVersion) return;
    try {
      const updated = await approvePlanVersion(planVersion.plan_version_id, payload.approval_notes);
      setPlanVersion(updated);
    } catch (err) {
      console.error('Plan approval error:', err);
      setErrorMessage('Plan approval transaction failed.');
    }
  };

  const handleReject = async (payload: { reviewer_name: string; reviewer_role: string; rejection_reason: string }) => {
    if (!planVersion) return;
    try {
      const updated = await rejectPlanVersion(planVersion.plan_version_id, payload.rejection_reason);
      setPlanVersion(updated);
    } catch (err) {
      console.error('Plan rejection error:', err);
      setErrorMessage('Plan rejection transaction failed.');
    }
  };

  const selectedTask = tasks.find((t) => t.task_id === selectedTaskId) || null;
  const selectedScheduled = scheduleResult?.scheduled_tasks.find((st) => st.task_id === selectedTaskId) || null;
  const selectedUnscheduled = scheduleResult?.unscheduled_tasks.find((ut) => ut.task_id === selectedTaskId) || null;
  const selectedDiagnostic = diagnosticsReport?.diagnostics?.find((d) => d.task_id === selectedTaskId) || null;
  const selectedTrain = trains.find((tr) => tr.train_id === selectedTrainId || tr.movement_id === selectedTrainId) || null;
  const selectedSection: BlockSection | null =
    corridor.sections?.find((s) => s.code === selectedSectionCode || s.section_id === selectedSectionCode) || null;

  return (
    <AppShell activeScenarioId={scenario.scenario_id}>
      <div className="flex-1 flex flex-col h-full overflow-hidden p-4 gap-3 bg-[#0A0E17] font-sans">
        {/* Top Workstation Subnavigation Bar */}
        <div className="flex items-center justify-between bg-[#0F172A] border border-[#1E2D4A] rounded-lg px-3.5 py-2 shrink-0">
          {/* Subnavigation Tabs */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setActiveSubtab('RAILWAY')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                activeSubtab === 'RAILWAY'
                  ? 'bg-[#2563EB] text-white shadow-xs'
                  : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
              }`}
            >
              Railway View
            </button>
            <button
              onClick={() => setActiveSubtab('TIMESPACE')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                activeSubtab === 'TIMESPACE'
                  ? 'bg-[#2563EB] text-white shadow-xs'
                  : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
              }`}
            >
              Time-Space
            </button>
            <button
              onClick={() => setActiveSubtab('TASKS')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                activeSubtab === 'TASKS'
                  ? 'bg-[#2563EB] text-white shadow-xs'
                  : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
              }`}
            >
              Tasks
            </button>
            <button
              onClick={() => setActiveSubtab('CONFLICTS')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                activeSubtab === 'CONFLICTS'
                  ? 'bg-[#2563EB] text-white shadow-xs'
                  : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
              }`}
            >
              Conflicts
            </button>
            <button
              onClick={() => setIsApprovalOpen(true)}
              className="px-3 py-1.5 rounded-md text-xs font-medium text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36] transition-colors"
            >
              Validation
            </button>
            <button
              onClick={() => setIsBenchmarkOpen(true)}
              className="px-3 py-1.5 rounded-md text-xs font-medium text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36] transition-colors"
            >
              Diagnostics
            </button>
            <button
              onClick={() => setIsCopilotOpen(true)}
              className="px-3 py-1.5 rounded-md text-xs font-medium text-[#93C5FD] hover:bg-[#141F36] transition-colors flex items-center gap-1"
            >
              <Sparkles className="w-3 h-3 text-[#2563EB]" />
              Copilot
            </button>
          </div>

          {/* Right Status & Action Controls */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-[#64748B] flex items-center gap-1 font-mono">
              <Clock className="w-3 h-3 text-[#64748B]" />
              Saved 14:32
            </span>

            <div className="h-4 w-[1px] bg-[#1E2D4A]" />

            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-[#1E2D4A] border border-[#2D436D] flex items-center justify-center text-[10px] font-bold text-[#F8FAFC]">
                MP
              </div>
              <span className="text-xs text-[#94A3B8] hidden sm:inline">
                Planner / Maintenance Planner
              </span>
            </div>

            <div className="h-4 w-[1px] bg-[#1E2D4A]" />

            {/* Run CP-SAT Button */}
            <Button
              size="sm"
              disabled={isSolving}
              onClick={handleTriggerSolve}
              className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-semibold px-3 h-8 shadow-xs"
            >
              <Play className={`w-3.5 h-3.5 mr-1.5 fill-current ${isSolving ? 'animate-spin' : ''}`} />
              {isSolving ? 'Optimizing...' : 'Run CP-SAT'}
            </Button>

            {/* Governance Action */}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsApprovalOpen(true)}
              className="border-emerald-600/40 text-emerald-400 hover:bg-emerald-950/40 text-xs font-semibold h-8"
            >
              <FileCheck className="w-3.5 h-3.5 mr-1.5" />
              Governance
            </Button>
          </div>
        </div>

        {/* Error Notice */}
        {errorMessage && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-1.5 text-xs text-rose-300 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
            <button onClick={() => setErrorMessage(null)} className="text-[#94A3B8] hover:text-white text-xs">
              Dismiss
            </button>
          </div>
        )}

        {/* Active Solver Progress Strip */}
        {isSolving && (
          <div className="bg-[#141F36] border border-[#2563EB]/40 rounded-lg p-2.5 flex items-center justify-between text-xs text-[#F8FAFC] shrink-0">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-[#2563EB] animate-spin" />
              <span className="font-semibold">OPTIMIZING POSSESSION SCHEDULE:</span>
              <span className="text-[#94A3B8]">{solvingMessage}</span>
            </div>
            <span className="text-[10px] text-[#64748B] font-mono">Target: &lt; 5.0s</span>
          </div>
        )}

        {/* Workstation Body */}
        {activeSubtab === 'TIMESPACE' ? (
          /* Focused Time-Space View */
          <div className="flex-1 min-h-0 bg-[#0F172A] border border-[#1E2D4A] rounded-lg overflow-hidden">
            <TimeSpaceChart
              corridor={corridor}
              trains={trains}
              tasks={tasks}
              scheduleResult={scheduleResult}
              selectedTaskId={selectedTaskId}
              selectedTrainId={selectedTrainId}
              selectedSectionCode={selectedSectionCode}
              onSelectTask={handleSelectTask}
              onSelectTrain={handleSelectTrain}
              onSelectSection={handleSelectSection}
            />
          </div>
        ) : (
          /* Flagship Multi-Pane Master Workstation Layout */
          <div className="flex-1 flex flex-col gap-3 min-h-0 overflow-hidden">
            {/* Upper Split: Corridor Map (Left) + Selected Entity & Copilot (Right) */}
            <div className="flex-1 grid grid-cols-12 gap-3 min-h-0">
              {/* Middle Left: Railway Corridor Map (65%) */}
              <div className="col-span-12 lg:col-span-8 h-full relative rounded-lg overflow-hidden border border-[#1E2D4A]">
                <RailwayCanvas
                  corridor={corridor}
                  tasks={tasks}
                  trains={trains}
                  scheduleResult={scheduleResult}
                  selectedTaskId={selectedTaskId}
                  selectedSectionCode={selectedSectionCode}
                  selectedTrainId={selectedTrainId}
                  onSelectTask={handleSelectTask}
                  onSelectSection={handleSelectSection}
                  onSelectTrain={handleSelectTrain}
                />

                {/* Prominent Overlay Callout Badge (Direct match to reference comp) */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10 bg-[#0F172A]/95 backdrop-blur-md border border-[#2563EB] rounded-lg p-3 shadow-2xl pointer-events-none min-w-[260px] text-xs">
                  <div className="flex items-center justify-between pb-1 mb-1 border-b border-[#1E2D4A]">
                    <span className="font-semibold text-[#F8FAFC] flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-[#2563EB] animate-pulse" />
                      Block-Section SEC-12
                    </span>
                    <span className="text-[10px] font-mono text-[#93C5FD] bg-[#1E3A8A]/50 px-1.5 py-0.5 rounded border border-[#2563EB]/40">
                      UP Mainline
                    </span>
                  </div>
                  <div className="text-[11px] text-[#CBD5E1] space-y-0.5 font-mono">
                    <p>Occupied: <span className="text-amber-400 font-semibold">14:00 - 15:30 UTC</span></p>
                    <p>By: <span className="text-[#F8FAFC] font-semibold">Maintenance Task TSK-0007</span></p>
                  </div>
                </div>

                {/* Bottom Corridor Station Indicator Bar */}
                <div className="absolute bottom-2.5 left-2.5 right-2.5 bg-[#0F172A]/90 backdrop-blur-xs border border-[#1E2D4A] rounded-md px-3 py-1.5 flex items-center justify-between text-[11px] text-[#94A3B8]">
                  <div className="flex items-center gap-4 font-mono text-[10px]">
                    <span className="text-[#F8FAFC] font-semibold">NDLS (0 km)</span>
                    <span className="text-[#64748B]">→</span>
                    <span>GZB (26 km)</span>
                    <span className="text-[#64748B]">→</span>
                    <span>ALJN (131 km)</span>
                    <span className="text-[#64748B]">→</span>
                    <span>TDL (209 km)</span>
                    <span className="text-[#64748B]">→</span>
                    <span>ETW (301 km)</span>
                    <span className="text-[#64748B]">→</span>
                    <span className="text-[#F8FAFC] font-semibold">CNB (440 km)</span>
                  </div>
                  <span className="text-[10px] text-[#64748B] flex items-center gap-1 font-sans">
                    <Layers className="w-3 h-3 text-[#2563EB]" />
                    Double Electrified (25kV AC)
                  </span>
                </div>
              </div>

              {/* Middle Right: Selected Entity Inspector + Integrated Copilot (35%) */}
              <div className="col-span-12 lg:col-span-4 h-full overflow-hidden">
                <TaskInspector
                  task={selectedTask}
                  scheduledInterval={selectedScheduled}
                  unscheduledReport={selectedUnscheduled}
                  diagnostic={selectedDiagnostic}
                  conflictingTrains={trains.filter((tr) => tr.train_number === '02073')}
                  selectedTrain={selectedTrain}
                  selectedSection={selectedSection}
                  onClearSelection={() => {
                    setSelectedTaskId(null);
                    setSelectedTrainId(null);
                    setSelectedSectionCode(null);
                  }}
                  onSelectTask={handleSelectTask}
                />
              </div>
            </div>

            {/* Bottom Split: Task List (Left 45%) + Timeline Schedule Diagram (Right 55%) */}
            <div className="h-[270px] grid grid-cols-12 gap-3 shrink-0">
              {/* Bottom Left: Task List (45%) */}
              <div className="col-span-12 lg:col-span-5 h-full overflow-hidden">
                <TaskQueueTable
                  tasks={tasks}
                  scheduleResult={scheduleResult}
                  selectedTaskId={selectedTaskId}
                  selectedSectionCode={selectedSectionCode}
                  onSelectTask={handleSelectTask}
                />
              </div>

              {/* Bottom Right: Timeline / Time-Space Schedule (55%) */}
              <div className="col-span-12 lg:col-span-7 h-full overflow-hidden">
                <TimelineScheduleView
                  corridor={corridor}
                  trains={trains}
                  tasks={tasks}
                  scheduleResult={scheduleResult}
                  selectedTaskId={selectedTaskId}
                  selectedTrainId={selectedTrainId}
                  selectedSectionCode={selectedSectionCode}
                  onSelectTask={handleSelectTask}
                  onSelectTrain={handleSelectTrain}
                  onSelectSection={handleSelectSection}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modals & Drawers */}
      <BenchmarkComparisonModal
        isOpen={isBenchmarkOpen}
        onClose={() => setIsBenchmarkOpen(false)}
        scenarioId={scenario.scenario_id}
      />

      <PlanApprovalModal
        isOpen={isApprovalOpen}
        onClose={() => setIsApprovalOpen(false)}
        planVersion={planVersion}
        validationSummary={validationResult}
        onApprove={handleApprove}
        onReject={handleReject}
      />

      <CopilotDrawer
        isOpen={isCopilotOpen}
        onClose={() => setIsCopilotOpen(false)}
        selectedTaskId={selectedTaskId}
        onSelectTask={handleSelectTask}
      />
    </AppShell>
  );
}
