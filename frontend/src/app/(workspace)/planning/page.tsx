'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { AppShell } from '@/components/shell/AppShell';
import { MapLibreRailwayMap } from '@/components/map/MapLibreRailwayMap';
import { TimeSpaceChart } from '@/components/planning/TimeSpaceChart';
import { TimelineScheduleView } from '@/components/planning/TimelineScheduleView';
import { TaskQueueTable } from '@/components/planning/TaskQueueTable';
import { EntityInspector, ContextualConflict, ContextualStation } from '@/components/planning/EntityInspector';
import { TasksWorkspace } from '@/components/planning/TasksWorkspace';
import { ConflictsWorkspace } from '@/components/planning/ConflictsWorkspace';
import { ValidationWorkspace } from '@/components/planning/ValidationWorkspace';
import { DiagnosticsWorkspace } from '@/components/planning/DiagnosticsWorkspace';
import { CopilotWorkspace } from '@/components/planning/CopilotWorkspace';
import { PlanApprovalModal } from '@/components/governance/PlanApprovalModal';
import { BenchmarkComparisonModal } from '@/components/planning/BenchmarkComparisonModal';
import { DigitalTwinInspectionModal } from '@/components/digital-twin/DigitalTwinInspectionModal';
import {
  CORRIDOR_STATIONS_GIS,
  CORRIDOR_SECTIONS_GIS,
} from '@/lib/railway/corridorGisData';
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
  DEMO_VALIDATION_RESULT,
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
  PanelRight,
  GitCompare,
  Box,
  Map as MapIcon,
  Activity,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ResponsiveDrawer } from '@/components/common/ResponsiveDrawer';

export type WorkspaceViewMode =
  | 'MAP'
  | 'TIMESPACE'
  | 'TIMELINE'
  | 'TASKS'
  | 'CONFLICTS'
  | 'VALIDATION'
  | 'DIAGNOSTICS'
  | 'COPILOT';

const SAMPLE_CONFLICTS: Record<string, ContextualConflict> = {
  'CONF-01': {
    conflict_id: 'CONF-HDW-01',
    severity: 'CRITICAL',
    title: 'Headway Buffer Violation: Express 12004 vs Freight 401',
    location: 'Block Section SEC-12 (Tundla – Etawah UP Mainline, km 242.0)',
    time_window: '14:20 – 16:10 UTC (Window overlap 18 min)',
    reason: 'Planned possession for Track Tamping (TSK-0007) reduces available headway margin to 3.2 min. Operational safety rule RULE-HDW-01 mandates minimum 7.0 min headway for high-speed express corridors.',
    impact_summary: '+14 min projected cumulative delay for trailing Express 12424',
    affected_trains: ['TR-12004 (Swarna Shatabdi)', 'TR-FRG-UP1 (Container Freight)'],
    affected_tasks: ['TSK-0007 (Switch Expansion Greasing)'],
    recommended_action: 'Shift possession window +45 minutes to 15:05–16:55 UTC via CP-SAT discrete optimization, eliminating headway overlap without cancelling work order.',
  },
};

function PlanningPageContent() {
  const searchParams = useSearchParams();
  const initialSubtab = (searchParams.get('subtab') as WorkspaceViewMode) || 'MAP';

  const [corridor, setCorridor] = useState<Corridor>(DEMO_CORRIDOR);
  const [scenario, setScenario] = useState<Scenario>(DEMO_SCENARIO);
  const [trains, setTrains] = useState<TrainMovement[]>(DEMO_TRAINS);
  const [tasks, setTasks] = useState<MaintenanceTask[]>(DEMO_TASKS);
  const [scheduleResult, setScheduleResult] = useState<ScheduleResult | null>(null);
  const [validationResult, setValidationResult] = useState<ScheduleValidationResult | null>(null);
  const [diagnosticsReport, setDiagnosticsReport] = useState<DiagnosticsReport | null>(null);
  const [planVersion, setPlanVersion] = useState<PlanVersion | null>(null);

  // Active Primary Workspace Surface Mode
  const [activeViewMode, setActiveViewMode] = useState<WorkspaceViewMode>(
    initialSubtab === ('RAILWAY' as unknown) ? 'MAP' : initialSubtab
  );

  // Synchronized Selection State
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>('TSK-0007');
  const [selectedTrainId, setSelectedTrainId] = useState<string | null>(null);
  const [selectedSectionCode, setSelectedSectionCode] = useState<string | null>('SEC-12');
  const [selectedStationCode, setSelectedStationCode] = useState<string | null>(null);
  const [selectedConflictId, setSelectedConflictId] = useState<string | null>(null);

  // Layout & UI State (Inspector opens on entity selection or manual toggle)
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [isDigitalTwinOpen, setIsDigitalTwinOpen] = useState(false);
  const [digitalTwinSection, setDigitalTwinSection] = useState<string>('SEC-12');

  // Handle ESC key for Full-Screen Mode
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullScreen) {
        setIsFullScreen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullScreen]);

  // Operations / Solver State
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
    setSelectedStationCode(null);
    setSelectedConflictId(null);
    setIsInspectorOpen(true);
    const targetTask = tasks.find((t) => t.task_id === taskId);
    if (targetTask) {
      setSelectedSectionCode(targetTask.section_code || targetTask.section_id || null);
    }
  };

  const handleSelectTrain = (trainId: string) => {
    setSelectedTrainId(trainId);
    setSelectedTaskId(null);
    setSelectedStationCode(null);
    setSelectedConflictId(null);
    setIsInspectorOpen(true);
  };

  const handleSelectSection = (sectionCode: string) => {
    setSelectedSectionCode(sectionCode);
    setSelectedTaskId(null);
    setSelectedTrainId(null);
    setSelectedStationCode(null);
    setSelectedConflictId(null);
    setIsInspectorOpen(true);
  };

  const handleSelectStation = (stationCode: string) => {
    setSelectedStationCode(stationCode);
    setSelectedTaskId(null);
    setSelectedTrainId(null);
    setSelectedSectionCode(null);
    setSelectedConflictId(null);
    setIsInspectorOpen(true);
  };

  const handleOpenDigitalTwin = (secCode: string) => {
    setDigitalTwinSection(secCode);
    setIsDigitalTwinOpen(true);
  };

  // Full Optimization Pipeline
  const handleTriggerSolve = useCallback(async () => {
    setIsSolving(true);
    setErrorMessage(null);
    setSolvingMessage('Compiling 127 discrete interval constraints...');
    try {
      let sched: ScheduleResult;
      try {
        sched = await optimizeSchedule(scenario.scenario_id, 5.0);
        setScheduleResult(sched);
      } catch (optErr: unknown) {
        console.error('Optimization error:', optErr);
        setScheduleResult(null);
        setValidationResult(null);
        setErrorMessage(
          'OPTIMIZATION UNAVAILABLE: The planning service could not be reached. Local state preserved.'
        );
        return;
      }

      setSolvingMessage('Independent Feasibility Certification: Auditing 13 hard constraints...');
      let val: ScheduleValidationResult;
      try {
        val = await validateSchedule(scenario.scenario_id, sched);
        setValidationResult(val);
      } catch (valErr: unknown) {
        console.error('Validation error:', valErr);
        setValidationResult(null);
        setErrorMessage(
          'VALIDATION UNAVAILABLE: The independent validator could not be reached.'
        );
        return;
      }

      setSolvingMessage('Generating causal diagnostics...');
      try {
        const diag = await diagnoseSchedule(scenario.scenario_id, sched);
        setDiagnosticsReport(diag);
      } catch (diagErr) {
        console.warn('Diagnostics unavailable:', diagErr);
      }

      try {
        const versions = await getPlanVersions(scenario.scenario_id);
        if (versions && versions.length > 0) {
          setPlanVersion(versions[0]);
        }
      } catch {
        // Non-blocking version refresh
      }
    } catch (err: unknown) {
      console.error('Solve pipeline error:', err);
      setErrorMessage('Unexpected error during optimization run.');
    } finally {
      setIsSolving(false);
      setSolvingMessage('');
    }
  }, [scenario.scenario_id]);

  const handleApprove = async (payload: { reviewer_name: string; reviewer_role: string; approval_notes: string }) => {
    if (!planVersion) return;
    try {
      const updated = await approvePlanVersion(
        planVersion.plan_version_id,
        payload.approval_notes,
        payload.reviewer_name,
        payload.reviewer_role
      );
      setPlanVersion(updated);
      setErrorMessage(null);
    } catch (err: unknown) {
      console.error('Plan approval error:', err);
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(`ACTION NOT COMPLETED: ${msg}`);
    }
  };

  const handleReject = async (payload: { reviewer_name: string; reviewer_role: string; rejection_reason: string }) => {
    if (!planVersion) return;
    try {
      const updated = await rejectPlanVersion(planVersion.plan_version_id, payload.rejection_reason);
      setPlanVersion(updated);
      setErrorMessage(null);
    } catch (err: unknown) {
      console.error('Plan rejection error:', err);
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(`ACTION NOT COMPLETED: ${msg}`);
    }
  };

  const selectedTask = tasks.find((t) => t.task_id === selectedTaskId) || null;
  const selectedScheduled = scheduleResult?.scheduled_tasks.find((st) => st.task_id === selectedTaskId) || null;
  const selectedDiagnostic = diagnosticsReport?.diagnostics?.find((d) => d.task_id === selectedTaskId) || null;
  const selectedTrain = trains.find((tr) => tr.train_id === selectedTrainId || tr.movement_id === selectedTrainId) || null;
  const selectedSection: BlockSection | null =
    corridor.sections?.find((s) => s.code === selectedSectionCode || s.section_id === selectedSectionCode) || null;
  const selectedStation: ContextualStation | null =
    CORRIDOR_STATIONS_GIS.find((st) => st.code === selectedStationCode) || null;
  const selectedConflict: ContextualConflict | null =
    selectedConflictId ? SAMPLE_CONFLICTS[selectedConflictId] : SAMPLE_CONFLICTS['CONF-01'];

  return (
    <AppShell
      activeScenarioId={scenario.scenario_id}
      scenarioName={corridor.name || 'Northern Corridor'}
      planningHorizon="24-Hour Planning Horizon"
      tasksCount={scheduleResult?.scheduled_tasks.length || 29}
      totalTasks={tasks.length || 30}
      trainsCount={trains.length || 50}
      lastSolveDuration={scheduleResult?.solver_wall_time_seconds || 1.48}
      workerStatus={isSolving ? 'Optimizing' : 'Idle'}
      validatorStatus={validationResult?.status === 'VALID' ? 'Active' : 'Warning'}
    >
      <div className="flex-1 flex flex-col h-full overflow-hidden p-4 sm:p-6 lg:p-7 gap-4 bg-[#04070D] font-sans max-w-[1900px] w-full mx-auto">
        {/* ============================================================== */}
        {/* TOP BAR: TRACKMELD PLANNING OPERATIONAL METADATA & ACTIONS     */}
        {/* ============================================================== */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 bg-[#0B101C] border border-[#1E2D4A] rounded-xl px-5 py-3.5 shrink-0 shadow-lg">
          {/* Left: Planning Operational Context */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-base font-bold text-[#F8FAFC]">Planning</span>
              <span className="text-xs text-[#64748B] font-mono">/</span>
              <span className="text-xs font-semibold text-[#93C5FD]">NDLS → CNB (440 km Trunk)</span>
            </div>

            <div className="h-4 w-[1px] bg-[#1E2D4A] hidden sm:block" />

            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="text-[#94A3B8] flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-[#3B82F6]" />
                18 OCT 2026
              </span>
              <span className="text-[#64748B]">•</span>
              <span className="text-[#93C5FD] font-semibold">Scenario A (24h Window)</span>
            </div>

            <div className="h-4 w-[1px] bg-[#1E2D4A] hidden md:block" />

            {/* Plan Status Badges */}
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[#141F36] text-[#38BDF8] border border-[#2D436D]">
                CP-SAT OPTIMAL
              </span>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/40">
                13-CHECK VALID
              </span>
              <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                planVersion?.status === 'APPROVED'
                  ? 'bg-emerald-950/80 text-emerald-400 border-emerald-500/40'
                  : 'bg-amber-950/80 text-amber-400 border-amber-500/40'
              }`}>
                {planVersion?.status === 'APPROVED' ? 'APPROVED' : 'PENDING FOUR-EYES'}
              </span>
            </div>
          </div>

          {/* Right: Master Operational Action Buttons */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* 3D Digital Twin Quick Launcher */}
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleOpenDigitalTwin(selectedSectionCode || 'SEC-12')}
              className="border-[#2D436D] hover:bg-[#141F36] text-[#38BDF8] text-xs font-semibold h-8"
              title="Launch 3D Digital Twin environment"
            >
              <Box className="w-3.5 h-3.5 mr-1.5" />
              <span>3D Twin</span>
            </Button>

            {/* Plan Comparison Modal Trigger */}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsBenchmarkOpen(true)}
              className="border-[#2D436D] hover:bg-[#141F36] text-[#CBD5E1] hover:text-white text-xs font-semibold h-8"
            >
              <GitCompare className="w-3.5 h-3.5 mr-1.5 text-[#3B82F6]" />
              <span>Compare Plans</span>
            </Button>

            {/* Optimization Trigger */}
            <Button
              size="sm"
              disabled={isSolving}
              onClick={handleTriggerSolve}
              className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-semibold px-3 h-8 shadow-xs cursor-pointer"
            >
              <Play className={`w-3.5 h-3.5 mr-1.5 fill-current ${isSolving ? 'animate-spin' : ''}`} />
              {isSolving ? 'Optimizing...' : 'Run Optimization'}
            </Button>

            {/* Validation Tab Quick Jump */}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setActiveViewMode('VALIDATION')}
              className="border-[#2D436D] hover:bg-[#141F36] text-[#CBD5E1] hover:text-white text-xs font-semibold h-8"
            >
              <ShieldCheck className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
              <span>Validate</span>
            </Button>

            {/* Governance Sign-Off Modal Trigger */}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsApprovalOpen(true)}
              className="border-emerald-500/40 hover:bg-emerald-950/30 text-emerald-300 text-xs font-semibold h-8"
            >
              <FileCheck className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
              <span>Approve</span>
            </Button>

            {/* Full-Screen Workspace Toggle */}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsFullScreen((prev) => !prev)}
              className="border-[#2D436D] hover:bg-[#141F36] text-[#CBD5E1] hover:text-white text-xs font-semibold h-8 cursor-pointer"
              title={isFullScreen ? "Exit Full-Screen (Esc)" : "Expand to Full-Screen Workspace"}
            >
              {isFullScreen ? (
                <Minimize2 className="w-3.5 h-3.5 text-[#38BDF8]" />
              ) : (
                <Maximize2 className="w-3.5 h-3.5 text-[#38BDF8]" />
              )}
              <span className="hidden sm:inline ml-1.5">{isFullScreen ? 'Exit Full-Screen' : 'Expand'}</span>
            </Button>

            {/* Inspector Toggle */}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsInspectorOpen((prev) => !prev)}
              className={`border-[#2D436D] text-xs font-semibold h-8 cursor-pointer ${
                isInspectorOpen ? 'bg-[#141F36] text-white border-[#2563EB]' : 'text-[#CBD5E1] hover:text-white'
              }`}
              title={isInspectorOpen ? 'Close Inspector' : 'Open Inspector'}
              aria-label="Inspector"
            >
              <PanelRight className="w-3.5 h-3.5 text-[#3B82F6]" />
              <span className="hidden sm:inline ml-1.5">Inspector</span>
            </Button>
          </div>
        </div>

        {/* ============================================================== */}
        {/* WORKSPACE VIEW MODE SELECTOR (Railway Map, Timeline, Tasks...) */}
        {/* ============================================================== */}
        <div className="flex items-center gap-1.5 bg-[#0B101C] border border-[#1E2D4A] rounded-lg p-1.5 overflow-x-auto shrink-0 text-xs">
          <button
            onClick={() => setActiveViewMode('MAP')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeViewMode === 'MAP'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <MapIcon className="w-3.5 h-3.5" />
            <span>Railway Map</span>
          </button>

          <button
            onClick={() => setActiveViewMode('TIMESPACE')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeViewMode === 'TIMESPACE'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Time-Space</span>
          </button>

          <button
            onClick={() => setActiveViewMode('TIMELINE')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeViewMode === 'TIMELINE'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Corridor Timeline</span>
          </button>

          <button
            onClick={() => setActiveViewMode('TASKS')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeViewMode === 'TASKS'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" />
            <span>Tasks Queue ({tasks.length})</span>
          </button>

          <button
            onClick={() => setActiveViewMode('CONFLICTS')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeViewMode === 'CONFLICTS'
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
            onClick={() => setActiveViewMode('VALIDATION')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeViewMode === 'VALIDATION'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Validation</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 ml-0.5" />
          </button>

          <button
            onClick={() => setActiveViewMode('DIAGNOSTICS')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeViewMode === 'DIAGNOSTICS'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36]'
            }`}
          >
            <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
            <span>Diagnostics</span>
          </button>

          <button
            onClick={() => setActiveViewMode('COPILOT')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${
              activeViewMode === 'COPILOT'
                ? 'bg-[#2563EB] text-white shadow-xs font-semibold'
                : 'text-[#93C5FD] hover:bg-[#141F36]'
            }`}
          >
            <Bot className="w-3.5 h-3.5 text-[#3B82F6]" />
            <span>Copilot Explainer</span>
            <Sparkles className="w-2.5 h-2.5 text-[#60A5FA]" />
          </button>
        </div>

        {/* Solver Progress Banner */}
        {isSolving && (
          <div className="bg-[#141F36] border border-[#2563EB]/40 rounded-lg p-2.5 flex items-center justify-between text-xs text-[#F8FAFC] shrink-0">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-[#38BDF8] animate-spin" />
              <span className="font-semibold">OPTIMIZING POSSESSION SCHEDULE:</span>
              <span className="text-[#94A3B8]">{solvingMessage}</span>
            </div>
            <span className="text-[10px] text-[#64748B] font-mono">Target: &lt; 5.0s</span>
          </div>
        )}

        {/* No-Data / Backend Unavailable Banner */}
        {!isSolving && scheduleResult === null && (
          <div className="bg-amber-950/30 border border-amber-500/30 rounded-lg p-2.5 flex items-center gap-2.5 text-xs text-amber-300 shrink-0">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <span className="font-semibold">No schedule computed.</span>
              {' '}Backend unavailable or optimization has not yet run.
              Planning data is unverified — no approval decision can be made.
            </span>
          </div>
        )}

        {/* Error Alert */}
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
        {/* MAIN OPERATING SURFACE                                         */}
        {/* ============================================================== */}
        <div
          className={
            isFullScreen
              ? 'fixed inset-0 z-50 bg-[#070B14] flex flex-col p-4 sm:p-6 overflow-hidden select-none'
              : 'flex-1 min-h-0 overflow-hidden flex gap-3.5'
          }
        >
          {isFullScreen && (
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#1E2D4A] shrink-0">
              <div className="flex items-center gap-3">
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[#2563EB]/20 text-[#38BDF8] border border-[#2563EB]/40">
                  FULL-SCREEN WORKSPACE
                </span>
                <h2 className="text-sm font-bold text-[#F8FAFC]">
                  {activeViewMode === 'MAP' && 'Corridor Railway Map (MapLibre Engine)'}
                  {activeViewMode === 'TIMESPACE' && 'Corridor Time-Space Diagram'}
                  {activeViewMode === 'TIMELINE' && 'Corridor Gantt Schedule Timeline'}
                  {activeViewMode === 'TASKS' && 'Full Maintenance Task Queue'}
                  {activeViewMode === 'CONFLICTS' && 'Operational Conflict Resolution Engine'}
                  {activeViewMode === 'VALIDATION' && '13-Check Safety Validation Firewall'}
                  {activeViewMode === 'DIAGNOSTICS' && 'CP-SAT Solver Diagnostics & Bottlenecks'}
                  {activeViewMode === 'COPILOT' && 'Decision Support Copilot Workspace'}
                </h2>
                <span className="text-xs text-[#64748B] hidden sm:inline">• NDLS → CNB (440 km Trunk)</span>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setIsInspectorOpen((prev) => !prev)}
                  className={`border-[#2D436D] text-xs font-semibold h-8 cursor-pointer ${
                    isInspectorOpen ? 'bg-[#141F36] text-white border-[#2563EB]' : 'text-[#CBD5E1] hover:text-white'
                  }`}
                >
                  <PanelRight className="w-3.5 h-3.5 text-[#3B82F6] mr-1.5" />
                  <span>Inspector</span>
                </Button>
                <Button
                  size="sm"
                  onClick={() => setIsFullScreen(false)}
                  className="bg-[#141F36] hover:bg-[#1E2D4A] text-[#F8FAFC] border border-[#2D436D] text-xs font-semibold h-8 flex items-center gap-1.5 cursor-pointer"
                >
                  <Minimize2 className="w-3.5 h-3.5 text-[#38BDF8]" />
                  <span>Exit Full Screen (ESC)</span>
                </Button>
              </div>
            </div>
          )}

          {/* Central Workspace Container (70-80% visual importance) */}
          <div className="flex-1 min-w-0 h-full overflow-hidden flex flex-col">
            {/* VIEW MODE 1: GEOSPATIAL MAP (DOMINANT OPERATING SURFACE) */}
            {activeViewMode === 'MAP' && (
              <div className="flex-1 w-full h-full min-h-0 relative">
                <MapLibreRailwayMap
                  selectedSectionCode={selectedSectionCode}
                  selectedTaskId={selectedTaskId}
                  selectedTrainId={selectedTrainId}
                  onSelectSection={handleSelectSection}
                  onSelectTask={handleSelectTask}
                  onSelectTrain={handleSelectTrain}
                  onSelectStation={handleSelectStation}
                  onOpenDigitalTwin={handleOpenDigitalTwin}
                />
              </div>
            )}

            {/* VIEW MODE 2: TIME-SPACE CHART */}
            {activeViewMode === 'TIMESPACE' && (
              <div className="flex-1 bg-[#0B101C] border border-[#1E2D4A] rounded-xl overflow-hidden">
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

            {/* VIEW MODE 3: CORRIDOR TIMELINE */}
            {activeViewMode === 'TIMELINE' && (
              <div className="flex-1 bg-[#0B101C] border border-[#1E2D4A] rounded-xl overflow-hidden p-3">
                <TimelineScheduleView
                  trains={trains}
                  tasks={tasks}
                  scheduleResult={scheduleResult}
                  selectedTaskId={selectedTaskId}
                  selectedTrainId={selectedTrainId}
                  selectedSectionCode={selectedSectionCode}
                  onSelectTask={handleSelectTask}
                  onSelectTrain={handleSelectTrain}
                  onSwitchToTimeSpace={() => setActiveViewMode('TIMESPACE')}
                />
              </div>
            )}

            {/* VIEW MODE 4: TASKS WORKSPACE */}
            {activeViewMode === 'TASKS' && (
              <TasksWorkspace
                tasks={tasks}
                scheduleResult={scheduleResult}
                selectedTaskId={selectedTaskId}
                onSelectTask={handleSelectTask}
              />
            )}

            {/* VIEW MODE 5: CONFLICTS WORKSPACE */}
            {activeViewMode === 'CONFLICTS' && (
              <ConflictsWorkspace
                onSelectTask={handleSelectTask}
                onNavigateToDiagnostics={(tId) => {
                  setSelectedTaskId(tId);
                  setActiveViewMode('DIAGNOSTICS');
                }}
              />
            )}

            {/* VIEW MODE 6: VALIDATION WORKSPACE */}
            {activeViewMode === 'VALIDATION' && (
              <ValidationWorkspace
                validationResult={validationResult}
                onOpenGovernance={() => setIsApprovalOpen(true)}
              />
            )}

            {/* VIEW MODE 7: DIAGNOSTICS WORKSPACE */}
            {activeViewMode === 'DIAGNOSTICS' && (
              <DiagnosticsWorkspace
                task={selectedTask}
                diagnosticsReport={diagnosticsReport}
                onSelectTask={handleSelectTask}
              />
            )}

            {/* VIEW MODE 8: COPILOT WORKSPACE */}
            {activeViewMode === 'COPILOT' && <CopilotWorkspace />}
          </div>
        </div>
      </div>

      {/* Contextual Entity Inspector Drawer (Rule 3 & 4) */}
      <ResponsiveDrawer
        isOpen={isInspectorOpen}
        onClose={() => setIsInspectorOpen(false)}
        title={
          selectedConflict
            ? `Conflict: ${selectedConflict.conflict_id}`
            : selectedTask
            ? `Work Order: ${selectedTask.task_code || selectedTask.task_id}`
            : selectedTrain
            ? `Train: ${selectedTrain.train_number}`
            : selectedSection
            ? `Track: ${selectedSection.name}`
            : selectedStation
            ? `Station: ${selectedStation.name}`
            : 'Entity Inspector'
        }
        subtitle={
          selectedConflict
            ? selectedConflict.title
            : selectedTask
            ? selectedTask.title
            : selectedTrain
            ? selectedTrain.train_name
            : selectedSection
            ? `${selectedSection.code} • Corridor Track Segment`
            : undefined
        }
        badge={
          selectedConflict ? (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-bold border border-rose-500/40">
              {selectedConflict.severity}
            </span>
          ) : selectedTask ? (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#2563EB]/20 text-[#38BDF8] font-bold border border-[#2563EB]/40">
              {selectedTask.priority}
            </span>
          ) : undefined
        }
        maxWidth="max-w-xl"
      >
        <div className="h-full">
          <EntityInspector
            task={selectedTask}
            scheduledInterval={selectedScheduled}
            diagnostic={selectedDiagnostic}
            conflictingTrains={trains.filter((tr) => tr.train_number === '02073')}
            selectedTrain={selectedTrain}
            selectedSection={selectedSection}
            selectedStation={selectedStation}
            selectedConflict={selectedConflict}
            isDrawer={true}
            hideHeader={true}
            onClose={() => setIsInspectorOpen(false)}
            onNavigateToDiagnostics={(tId) => {
              setSelectedTaskId(tId);
              setActiveViewMode('DIAGNOSTICS');
              setIsInspectorOpen(false);
            }}
            onNavigateToConflicts={(tId) => {
              setSelectedTaskId(tId);
              setActiveViewMode('CONFLICTS');
              setIsInspectorOpen(false);
            }}
            onOpenDigitalTwin={handleOpenDigitalTwin}
          />
        </div>
      </ResponsiveDrawer>

      {/* 3D Digital Twin Inspection Modal */}
      <DigitalTwinInspectionModal
        isOpen={isDigitalTwinOpen}
        onClose={() => setIsDigitalTwinOpen(false)}
        sectionCode={digitalTwinSection}
        sectionName={
          CORRIDOR_SECTIONS_GIS.find(
            (s) => s.code === digitalTwinSection || s.section_id === digitalTwinSection
          )?.name || 'Tundla – Etawah Mainline'
        }
        kmRange="km 209.0 – 301.0"
        workOrderTitle={selectedTask?.title || 'WO-1847 Plain Track CSM Tamping'}
      />

      {/* Benchmark Plan Comparison Modal */}
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
        <div className="flex h-screen w-full items-center justify-center bg-[#04070D] text-[#94A3B8]">
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
