'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { AppShell } from '@/components/shell/AppShell';
import { RailwayCanvas } from '@/components/railway/RailwayCanvas';
import { TimeSpaceChart } from '@/components/planning/TimeSpaceChart';
import { TimelineScheduleView } from '@/components/planning/TimelineScheduleView';
import { TaskQueueTable } from '@/components/planning/TaskQueueTable';
import { EntityInspector } from '@/components/planning/EntityInspector';
import { TasksWorkspace } from '@/components/planning/TasksWorkspace';
import { ConflictsWorkspace } from '@/components/planning/ConflictsWorkspace';
import { ValidationWorkspace } from '@/components/planning/ValidationWorkspace';
import { DiagnosticsWorkspace } from '@/components/planning/DiagnosticsWorkspace';
import { CopilotWorkspace } from '@/components/planning/CopilotWorkspace';
import { PlanApprovalModal } from '@/components/governance/PlanApprovalModal';
import { BenchmarkComparisonModal } from '@/components/planning/BenchmarkComparisonModal';
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
  Sparkles,
  Layers,
  ShieldCheck,
  AlertTriangle,
  GitBranch,
  Bot,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export type WorkspaceSubtab =
  | 'RAILWAY'
  | 'TIMESPACE'
  | 'TASKS'
  | 'CONFLICTS'
  | 'VALIDATION'
  | 'DIAGNOSTICS'
  | 'COPILOT';

function PlanningPageContent() {
  const searchParams = useSearchParams();
  const initialSubtab = (searchParams.get('subtab') as WorkspaceSubtab) || 'RAILWAY';

  const [corridor, setCorridor] = useState<Corridor>(DEMO_CORRIDOR);
  const [scenario, setScenario] = useState<Scenario>(DEMO_SCENARIO);
  const [trains, setTrains] = useState<TrainMovement[]>(DEMO_TRAINS);
  const [tasks, setTasks] = useState<MaintenanceTask[]>(DEMO_TASKS);
  const [scheduleResult, setScheduleResult] = useState<ScheduleResult | null>(DEMO_SCHEDULE_RESULT);
  const [validationResult, setValidationResult] = useState<ScheduleValidationResult | null>(DEMO_VALIDATION_RESULT);
  const [diagnosticsReport, setDiagnosticsReport] = useState<DiagnosticsReport | null>(DEMO_DIAGNOSTICS);
  const [planVersion, setPlanVersion] = useState<PlanVersion | null>(DEMO_PLAN_VERSION);

  // Active Workspace Mode (Progressive Disclosure)
  const [activeSubtab, setActiveSubtab] = useState<WorkspaceSubtab>(initialSubtab);

  // Synchronized Selection
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>('TSK-0007');
  const [selectedTrainId, setSelectedTrainId] = useState<string | null>(null);
  const [selectedSectionCode, setSelectedSectionCode] = useState<string | null>('SEC-12');
  const [isInspectorOpen, setIsInspectorOpen] = useState(true);

  // Operations state
  const [isSolving, setIsSolving] = useState(false);
  const [solvingMessage, setSolvingMessage] = useState<string>('');
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [isBenchmarkOpen, setIsBenchmarkOpen] = useState(false);
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
    setIsInspectorOpen(true);
    const targetTask = tasks.find((t) => t.task_id === taskId);
    if (targetTask) {
      setSelectedSectionCode(targetTask.section_code || targetTask.section_id || null);
    }
  };

  const handleSelectTrain = (trainId: string) => {
    setSelectedTrainId(trainId);
    setSelectedTaskId(null);
    setIsInspectorOpen(true);
  };

  const handleSelectSection = (sectionCode: string) => {
    setSelectedSectionCode(sectionCode);
    setIsInspectorOpen(true);
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
  const selectedDiagnostic = diagnosticsReport?.diagnostics?.find((d) => d.task_id === selectedTaskId) || null;
  const selectedTrain = trains.find((tr) => tr.train_id === selectedTrainId || tr.movement_id === selectedTrainId) || null;
  const selectedSection: BlockSection | null =
    corridor.sections?.find((s) => s.code === selectedSectionCode || s.section_id === selectedSectionCode) || null;

  return (
    <AppShell
      activeScenarioId={scenario.scenario_id}
      scenarioName={corridor.name || 'Northern Corridor'}
      planningHorizon="72-Hour Planning Horizon"
      tasksCount={scheduleResult?.scheduled_tasks.length || 29}
      totalTasks={tasks.length || 30}
      trainsCount={trains.length || 14}
      lastSolveDuration={scheduleResult?.solver_wall_time_seconds || 1.48}
      workerStatus={isSolving ? 'Optimizing' : 'Idle'}
      validatorStatus={validationResult?.status === 'VALID' ? 'Active' : 'Warning'}
    >
      <div className="flex-1 flex flex-col h-full overflow-hidden p-3.5 sm:p-4 gap-3 bg-[#0A0E17] font-sans">
        {/* ============================================================== */}
        {/* A. PLANNING WORKSPACE HEADER (Matching Reference Comp)          */}
        {/* ============================================================== */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#0F172A] border border-[#1E2D4A] rounded-lg px-4 py-2.5 shrink-0">
          {/* Left: Title + LIVE status */}
          <div className="flex items-center gap-2.5">
            <h1 className="text-base font-bold text-[#F8FAFC]">Planning Workspace</h1>
            <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 font-bold border border-emerald-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              LIVE
            </span>
          </div>

          {/* Right: Engine Status Badges & Action Buttons */}
          <div className="flex items-center gap-2.5 flex-wrap">
            {/* Engine Badges */}
            <span className="text-[10px] font-mono font-bold px-2 py-1 rounded bg-[#141F36] text-[#93C5FD] border border-[#2D436D]">
              CP-SAT
            </span>
            <span className="text-[10px] font-mono font-bold px-2 py-1 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/40">
              VALID
            </span>
            <span className="text-[10px] font-mono font-bold px-2 py-1 rounded bg-amber-950/80 text-amber-400 border border-amber-500/40">
              {planVersion?.status === 'APPROVED' ? 'APPROVED' : 'PENDING REVIEW'}
            </span>

            <div className="h-5 w-[1px] bg-[#1E2D4A] mx-1 hidden sm:block" />

            {/* Run Optimization Button */}
            <Button
              size="sm"
              disabled={isSolving}
              onClick={handleTriggerSolve}
              className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-semibold px-3 h-8 shadow-xs"
            >
              <Play className={`w-3.5 h-3.5 mr-1.5 fill-current ${isSolving ? 'animate-spin' : ''}`} />
              {isSolving ? 'Optimizing...' : 'Run Optimization'}
            </Button>

            {/* Governance Review Button */}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsApprovalOpen(true)}
              className="border-[#2D436D] hover:bg-[#141F36] text-[#CBD5E1] hover:text-white text-xs font-semibold h-8"
            >
              <FileCheck className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
              Governance
            </Button>
          </div>
        </div>

        {/* ============================================================== */}
        {/* B. WORKSPACE MODE NAVIGATION TABS (Primary Surface Selector)    */}
        {/* ============================================================== */}
        <div className="flex items-center gap-1.5 bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-1.5 overflow-x-auto shrink-0 text-xs">
          <button
            onClick={() => setActiveSubtab('RAILWAY')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeSubtab === 'RAILWAY'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Railway</span>
          </button>

          <button
            onClick={() => setActiveSubtab('TIMESPACE')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeSubtab === 'TIMESPACE'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Time-Space</span>
          </button>

          <button
            onClick={() => setActiveSubtab('TASKS')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeSubtab === 'TASKS'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" />
            <span>Tasks</span>
          </button>

          <button
            onClick={() => setActiveSubtab('CONFLICTS')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeSubtab === 'CONFLICTS'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            <span>Conflicts</span>
            <span className="text-[9.5px] font-mono px-1.5 py-0.2 rounded-full bg-rose-500 text-white font-bold ml-0.5">
              3
            </span>
          </button>

          <button
            onClick={() => setActiveSubtab('VALIDATION')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeSubtab === 'VALIDATION'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Validation</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 ml-0.5" />
          </button>

          <button
            onClick={() => setActiveSubtab('DIAGNOSTICS')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeSubtab === 'DIAGNOSTICS'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
            <span>Diagnostics</span>
          </button>

          <button
            onClick={() => setActiveSubtab('COPILOT')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeSubtab === 'COPILOT'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#93C5FD] hover:bg-[#141F36]'
            }`}
          >
            <Bot className="w-3.5 h-3.5 text-[#3B82F6]" />
            <span>Copilot</span>
            <Sparkles className="w-2.5 h-2.5 text-[#60A5FA]" />
          </button>
        </div>

        {/* Solver Progress Banner */}
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

        {/* Error Alert Notice */}
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

        {/* ============================================================== */}
        {/* C. PRIMARY WORKSPACE SURFACE (Progressive Disclosure)          */}
        {/* ============================================================== */}
        <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
          {/* MODE 1: RAILWAY VIEW (DEFAULT MASTER WORKSTATION) */}
          {activeSubtab === 'RAILWAY' && (
            <div className="flex-1 flex gap-3 min-h-0 overflow-hidden relative">
              {/* Left/Central Column (Map 70% + Contextual Bottom 30%) */}
              <div className="flex-1 flex flex-col gap-3 min-h-0 overflow-hidden">
                {/* Upper: Railway GIS Map Canvas (70-75% height) */}
                <div className="flex-[7] min-h-[300px] relative rounded-lg overflow-hidden border border-[#1E2D4A]">
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
                      <p>Occupied: <span className="text-amber-400 font-semibold">07:00 – 10:00 UTC</span></p>
                      <p>By: <span className="text-[#F8FAFC] font-semibold">Maintenance Task TSK-0007</span></p>
                    </div>
                  </div>
                </div>

                {/* Lower: Contextual Bottom Split (Task Overview 45% + Timeline 55%) */}
                <div className="flex-[3] min-h-[200px] grid grid-cols-12 gap-3 shrink-0">
                  {/* Bottom Left: Task Overview */}
                  <div className="col-span-12 md:col-span-5 h-full overflow-hidden">
                    <TaskQueueTable
                      tasks={tasks}
                      scheduleResult={scheduleResult}
                      selectedTaskId={selectedTaskId}
                      onSelectTask={handleSelectTask}
                      isCollapsible={true}
                    />
                  </div>

                  {/* Bottom Right: Timeline / Time-Space Schedule */}
                  <div className="col-span-12 md:col-span-7 h-full overflow-hidden">
                    <TimelineScheduleView
                      trains={trains}
                      tasks={tasks}
                      scheduleResult={scheduleResult}
                      selectedTaskId={selectedTaskId}
                      selectedTrainId={selectedTrainId}
                      selectedSectionCode={selectedSectionCode}
                      onSelectTask={handleSelectTask}
                      onSelectTrain={handleSelectTrain}
                      onSwitchToTimeSpace={() => setActiveSubtab('TIMESPACE')}
                    />
                  </div>
                </div>
              </div>

              {/* Right: Contextual Entity Inspector (Slide-out or Collapsible) */}
              {isInspectorOpen && (
                <div className="hidden lg:block h-full shrink-0">
                  <EntityInspector
                    task={selectedTask}
                    scheduledInterval={selectedScheduled}
                    diagnostic={selectedDiagnostic}
                    conflictingTrains={trains.filter((tr) => tr.train_number === '02073')}
                    selectedTrain={selectedTrain}
                    selectedSection={selectedSection}
                    onClose={() => setIsInspectorOpen(false)}
                    onNavigateToDiagnostics={(tId) => {
                      setSelectedTaskId(tId);
                      setActiveSubtab('DIAGNOSTICS');
                    }}
                    onNavigateToConflicts={(tId) => {
                      setSelectedTaskId(tId);
                      setActiveSubtab('CONFLICTS');
                    }}
                  />
                </div>
              )}
            </div>
          )}

          {/* MODE 2: TIME-SPACE VIEW (DEDICATED FULL DIAGRAM WORKSPACE) */}
          {activeSubtab === 'TIMESPACE' && (
            <div className="flex-1 bg-[#0F172A] border border-[#1E2D4A] rounded-lg overflow-hidden">
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
          )}

          {/* MODE 3: TASKS VIEW (DEDICATED COMPREHENSIVE TASK MANAGEMENT) */}
          {activeSubtab === 'TASKS' && (
            <TasksWorkspace
              tasks={tasks}
              scheduleResult={scheduleResult}
              selectedTaskId={selectedTaskId}
              onSelectTask={handleSelectTask}
            />
          )}

          {/* MODE 4: CONFLICTS VIEW (DEDICATED CONFLICT RESOLUTION) */}
          {activeSubtab === 'CONFLICTS' && (
            <ConflictsWorkspace
              onSelectTask={handleSelectTask}
              onNavigateToDiagnostics={(tId) => {
                setSelectedTaskId(tId);
                setActiveSubtab('DIAGNOSTICS');
              }}
            />
          )}

          {/* MODE 5: VALIDATION VIEW (DEDICATED INDEPENDENT VALIDATION CERTIFICATION) */}
          {activeSubtab === 'VALIDATION' && (
            <ValidationWorkspace
              validationResult={validationResult}
              onOpenGovernance={() => setIsApprovalOpen(true)}
            />
          )}

          {/* MODE 6: DIAGNOSTICS VIEW (DEDICATED CAUSAL ROOT CAUSE INVESTIGATION) */}
          {activeSubtab === 'DIAGNOSTICS' && (
            <DiagnosticsWorkspace
              task={selectedTask}
              diagnosticsReport={diagnosticsReport}
              onSelectTask={handleSelectTask}
            />
          )}

          {/* MODE 7: COPILOT VIEW (DEDICATED READ-ONLY DECISION SUPPORT) */}
          {activeSubtab === 'COPILOT' && <CopilotWorkspace />}
        </div>
      </div>

      {/* Benchmark Comparison Modal */}
      <BenchmarkComparisonModal
        isOpen={isBenchmarkOpen}
        onClose={() => setIsBenchmarkOpen(false)}
        scenarioId={scenario.scenario_id}
      />

      {/* Human Governance Approval Modal */}
      <PlanApprovalModal
        isOpen={isApprovalOpen}
        onClose={() => setIsApprovalOpen(false)}
        planVersion={planVersion}
        validationSummary={validationResult}
        onApprove={handleApprove}
        onReject={handleReject}
      />
    </AppShell>
  );
}

export default function PlanningPage() {
  return (
    <React.Suspense
      fallback={
        <div className="flex h-screen w-full items-center justify-center bg-[#0A0E17] text-[#94A3B8]">
          <div className="flex items-center gap-2 font-mono text-sm">
            <RefreshCw className="w-4 h-4 animate-spin text-[#2563EB]" />
            <span>Loading TrackMeld Planning Workspace...</span>
          </div>
        </div>
      }
    >
      <PlanningPageContent />
    </React.Suspense>
  );
}

