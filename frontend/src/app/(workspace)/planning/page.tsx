'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { useWorkspace } from '@/contexts/WorkspaceContext';
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
import { ComparePlansModal } from '@/components/planning/ComparePlansModal';
import { DigitalTwinInspectionModal } from '@/components/digital-twin/DigitalTwinInspectionModal';
import { PlanLifecycleBar, LifecycleStage } from '@/components/planning/PlanLifecycleBar';
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
  createPlanningRun,
  createPlanVersionFromRun,
  approvePlanVersion,
  rejectPlanVersion,
  ApiError,
  isApiError,
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
  DataProvenance,
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
  LayoutGrid,
  Database,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ResponsiveDrawer } from '@/components/common/ResponsiveDrawer';

export type WorkspaceViewMode =
  | 'INTEGRATED'
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
  const initialSubtab = (searchParams.get('subtab') as WorkspaceViewMode) || 'INTEGRATED';

  const [corridor, setCorridor] = useState<Corridor>(DEMO_CORRIDOR);
  const [scenario, setScenario] = useState<Scenario>(DEMO_SCENARIO);
  const [trains, setTrains] = useState<TrainMovement[]>(DEMO_TRAINS);
  const [tasks, setTasks] = useState<MaintenanceTask[]>(DEMO_TASKS);
  const [scheduleResult, setScheduleResult] = useState<ScheduleResult | null>(null);
  const [validationResult, setValidationResult] = useState<ScheduleValidationResult | null>(null);
  const [diagnosticsReport, setDiagnosticsReport] = useState<DiagnosticsReport | null>(null);
  const [planVersion, setPlanVersion] = useState<PlanVersion | null>(null);
  const [scheduleProvenance, setScheduleProvenance] = useState<DataProvenance>('unavailable');
  const [scenarioProvenance, setScenarioProvenance] = useState<DataProvenance>('loading');

  // Active Primary Workspace Surface Mode (Defaults to master 3-panel split)
  const [activeViewMode, setActiveViewMode] = useState<WorkspaceViewMode>(
    initialSubtab === ('RAILWAY' as unknown) ? 'INTEGRATED' : initialSubtab
  );

  // Subtab for Bottom-Right Panel in 3-Panel Integrated Mode
  const [bottomTab, setBottomTab] = useState<'TIMELINE' | 'TIMESPACE' | 'DIAGNOSTICS'>('TIMELINE');

  // Synchronized Selection State
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>('TSK-0007');
  const [selectedTrainId, setSelectedTrainId] = useState<string | null>(null);
  const [selectedSectionCode, setSelectedSectionCode] = useState<string | null>('SEC-12');
  const [selectedStationCode, setSelectedStationCode] = useState<string | null>(null);
  const [selectedConflictId, setSelectedConflictId] = useState<string | null>(null);

  // Layout & UI State (Docked Inspector open on wide desktop screens only)
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [isDigitalTwinOpen, setIsDigitalTwinOpen] = useState(false);
  const [digitalTwinSection, setDigitalTwinSection] = useState<string>('SEC-12');

  // Synchronize URL search params (e.g. ?subtab=TIMESPACE) to activeViewMode
  useEffect(() => {
    const subtabParam = searchParams.get('subtab') as WorkspaceViewMode | null;
    if (subtabParam) {
      const targetMode = subtabParam === ('RAILWAY' as unknown) ? 'INTEGRATED' : subtabParam;
      const timer = setTimeout(() => {
        setActiveViewMode(targetMode);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [searchParams]);

  // Auto-expand docked inspector on desktop >= 1280px for docked view modes only
  useEffect(() => {
    const timer = setTimeout(() => {
      if (
        typeof window !== 'undefined' &&
        window.innerWidth >= 1280 &&
        (activeViewMode === 'INTEGRATED' || activeViewMode === 'MAP')
      ) {
        setIsInspectorOpen(true);
      } else {
        setIsInspectorOpen(false);
      }
    }, 0);
    return () => clearTimeout(timer);
  }, [activeViewMode]);

  const handleSelectViewMode = (mode: WorkspaceViewMode) => {
    setActiveViewMode(mode);
    if (mode === 'INTEGRATED' || mode === 'MAP') {
      if (typeof window !== 'undefined' && window.innerWidth >= 1280) {
        setIsInspectorOpen(true);
      }
    } else {
      setIsInspectorOpen(false);
    }
  };

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
  const [isApprovalSubmitting, setIsApprovalSubmitting] = useState(false);
  const [isBenchmarkOpen, setIsBenchmarkOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPersisting, setIsPersisting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadInitialData() {
      try {
        const bundle = await getScenarioBundle('SCN-DEMO-001');
        if (cancelled) return;
        if (bundle.corridor) setCorridor(bundle.corridor);
        if (bundle.scenario) setScenario(bundle.scenario);
        if (bundle.trains !== undefined) setTrains(bundle.trains);
        if (bundle.tasks !== undefined) setTasks(bundle.tasks);
        setScenarioProvenance('backend');

        // Check if an authoritative persisted PlanVersion exists for this scenario
        try {
          const versions = await getPlanVersions('SCN-DEMO-001');
          if (!cancelled && versions && versions.length > 0) {
            const active = versions[0];
            setPlanVersion(active);
            const schedResult = (active as unknown as { schedule_result?: ScheduleResult }).schedule_result;
            if (schedResult) {
              setScheduleResult(schedResult);
              setScheduleProvenance('backend');
              const valData = schedResult.validation || (schedResult as unknown as { validation_summary?: ScheduleValidationResult }).validation_summary;
              if (valData) {
                setValidationResult(valData as ScheduleValidationResult);
              } else if (active.validation_status && active.schedule_identity) {
                setValidationResult({
                  status: active.validation_status as 'VALID' | 'INVALID',
                  valid: active.validation_status === 'VALID',
                  is_approvable: active.is_approvable ?? (active.validation_status === 'VALID'),
                  schedule_identity: active.schedule_identity,
                  findings: [],
                  error_count: (active.validation_findings_summary?.error_count as number) || 0,
                  warning_count: 0,
                  info_count: 0,
                  checked_task_count: 0,
                  checked_section_count: 0,
                  checked_resource_count: 0,
                  checked_train_movement_count: 0,
                  checks_executed: [],
                  approval_gate_message: 'Certified under authoritative backend governance record',
                });
              }
            }
          } else if (!cancelled) {
            setPlanVersion(null);
          }
        } catch {
          if (!cancelled) setPlanVersion(null);
        }
      } catch (err) {
        console.warn('Initial data load warning:', err);
        if (!cancelled) {
          setScenarioProvenance('synthetic');
        }
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
    setScheduleProvenance('loading');
    setSolvingMessage('Compiling discrete interval constraints...');
    try {
      let sched: ScheduleResult;
      try {
        sched = await optimizeSchedule(scenario.scenario_id, 5.0);
        setScheduleResult(sched);
        setScheduleProvenance('backend');
      } catch (optErr: unknown) {
        console.warn('Optimization service error:', optErr);
        const errMsg = optErr instanceof Error ? optErr.message : String(optErr);
        setScheduleResult(null);
        setValidationResult(null);
        setDiagnosticsReport(null);
        setScheduleProvenance('unavailable');
        setErrorMessage(`OPTIMIZATION UNAVAILABLE: ${errMsg}`);
        return;
      }

      setSolvingMessage('Independent Feasibility Certification: Auditing hard constraints...');
      let val: ScheduleValidationResult;
      try {
        val = await validateSchedule(scenario.scenario_id, sched);
        setValidationResult(val);
      } catch (valErr: unknown) {
        console.warn('Validation service error:', valErr);
        const errMsg = valErr instanceof Error ? valErr.message : String(valErr);
        setValidationResult(null);
        setErrorMessage(`VALIDATION UNAVAILABLE: ${errMsg}`);
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
        const matchingVersion = versions?.find((v) => v.schedule_identity === val.schedule_identity);
        if (matchingVersion) {
          setPlanVersion(matchingVersion);
        } else {
          // Optimization solved an in-memory candidate schedule that has not yet
          // been promoted/persisted as an authoritative PlanVersion in the database.
          // Never substitute an unrelated older version (e.g. versions[0]).
          setPlanVersion(null);
        }
      } catch {
        setPlanVersion(null);
      }
    } catch (err: unknown) {
      console.error('Solve pipeline error:', err);
      const errMsg = err instanceof Error ? err.message : String(err);
      setErrorMessage(`OPTIMIZATION UNAVAILABLE: ${errMsg}`);
      setScheduleProvenance('unavailable');
    } finally {
      setIsSolving(false);
      setSolvingMessage('');
    }
  }, [scenario.scenario_id]);

  const handlePersistCandidatePlan = async () => {
    if (!scheduleResult || !validationResult) {
      setErrorMessage('CANNOT PERSIST: No candidate schedule available.');
      return;
    }
    if (scheduleProvenance !== 'backend') {
      setErrorMessage('CANNOT PERSIST: Synthetic demo schedules cannot be persisted to backend.');
      return;
    }
    if (!validationResult.is_approvable) {
      setErrorMessage('CANNOT PERSIST: Only certified valid schedules may be persisted as plan versions.');
      return;
    }
    setIsPersisting(true);
    setErrorMessage(null);
    try {
      // 1. Submit planning run via supported API
      const run = await createPlanningRun({
        scenario_id: scenario.scenario_id,
        scheduler_type: scheduleResult.scheduler_type || 'CP_SAT',
        time_limit_seconds: 5.0,
        validate_after_solve: true,
      });

      // 2. Instantiate PlanVersion candidate from completed run
      const newPlanVersion = await createPlanVersionFromRun(
        run.run_id,
        'Instantiated PlanVersion from optimization workspace.'
      );

      setPlanVersion(newPlanVersion);
      setErrorMessage(null);
    } catch (err: unknown) {
      console.warn('Candidate persistence notice:', err);
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(`PERSISTENCE UNAVAILABLE: ${msg}. Backend database connection is required to issue an authoritative PlanVersion ID.`);
    } finally {
      setIsPersisting(false);
    }
  };

  const handleLoadDemoSchedule = () => {
    setScheduleResult(DEMO_SCHEDULE_RESULT);
    setValidationResult(DEMO_VALIDATION_RESULT);
    setDiagnosticsReport(null);
    setErrorMessage(null);
    setScheduleProvenance('synthetic');
  };

  const handleApprove = async (payload: { reviewer_name: string; reviewer_role: string; approval_notes: string }) => {
    if (!planVersion || isApprovalSubmitting) {
      const err = 'CANNOT APPROVE: Schedule candidate is not linked to a persisted plan version.';
      setErrorMessage(err);
      throw new Error(err);
    }
    if (!validationResult || planVersion.schedule_identity !== validationResult.schedule_identity) {
      const err = 'CANNOT APPROVE: Cryptographic identity mismatch between plan version and validation certification.';
      setErrorMessage(err);
      throw new Error(err);
    }
    if (scheduleProvenance !== 'backend') {
      const err = 'CANNOT APPROVE: Synthetic demo schedules cannot be approved.';
      setErrorMessage(err);
      throw new Error(err);
    }
    setIsApprovalSubmitting(true);
    setErrorMessage(null);
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
      if (isApiError(err) && err.status === 409) {
        setErrorMessage(`CONFLICT (409): ${msg}. Refreshing plan version.`);
        try {
          const fresh = await getPlanVersions(scenario.scenario_id);
          const current = fresh?.find((v) => v.plan_version_id === planVersion.plan_version_id);
          if (current) setPlanVersion(current);
        } catch {
          // ignore refresh error
        }
      } else if (isApiError(err) && err.status === 401) {
        setErrorMessage(`UNAUTHORIZED (401): ${msg}`);
      } else if (isApiError(err) && err.status === 403) {
        setErrorMessage(`PERMISSION DENIED (403): ${msg}`);
      } else {
        setErrorMessage(`ACTION NOT COMPLETED: ${msg}`);
      }
      throw err;
    } finally {
      setIsApprovalSubmitting(false);
    }
  };

  const handleReject = async (payload: { reviewer_name: string; reviewer_role: string; rejection_reason: string }) => {
    if (!planVersion || isApprovalSubmitting) {
      const err = 'CANNOT REJECT: Schedule candidate is not linked to a persisted plan version.';
      setErrorMessage(err);
      throw new Error(err);
    }
    if (!validationResult || planVersion.schedule_identity !== validationResult.schedule_identity) {
      const err = 'CANNOT REJECT: Cryptographic identity mismatch between plan version and validation certification.';
      setErrorMessage(err);
      throw new Error(err);
    }
    if (scheduleProvenance !== 'backend') {
      const err = 'CANNOT REJECT: Synthetic demo schedules cannot be rejected.';
      setErrorMessage(err);
      throw new Error(err);
    }
    setIsApprovalSubmitting(true);
    setErrorMessage(null);
    try {
      const updated = await rejectPlanVersion(planVersion.plan_version_id, payload.rejection_reason);
      setPlanVersion(updated);
      setErrorMessage(null);
    } catch (err: unknown) {
      console.error('Plan rejection error:', err);
      const msg = err instanceof Error ? err.message : String(err);
      if (isApiError(err) && err.status === 409) {
        setErrorMessage(`CONFLICT (409): ${msg}. Refreshing plan version.`);
        try {
          const fresh = await getPlanVersions(scenario.scenario_id);
          const current = fresh?.find((v) => v.plan_version_id === planVersion.plan_version_id);
          if (current) setPlanVersion(current);
        } catch {
          // ignore refresh error
        }
      } else if (isApiError(err) && err.status === 401) {
        setErrorMessage(`UNAUTHORIZED (401): ${msg}`);
      } else if (isApiError(err) && err.status === 403) {
        setErrorMessage(`PERMISSION DENIED (403): ${msg}`);
      } else {
        setErrorMessage(`ACTION NOT COMPLETED: ${msg}`);
      }
      throw err;
    } finally {
      setIsApprovalSubmitting(false);
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

  const { updateTelemetry } = useWorkspace();

  useEffect(() => {
    updateTelemetry({
      activeScenarioId: scenario.scenario_id,
      scenarioName: corridor.name || 'Northern Corridor',
      planningHorizon: '24-Hour Planning Horizon',
      tasksCount: scheduleResult ? scheduleResult.scheduled_tasks.length : null,
      totalTasks: tasks.length > 0 ? tasks.length : null,
      trainsCount: trains.length > 0 ? trains.length : null,
      lastSolveDuration: scheduleResult ? scheduleResult.solver_wall_time_seconds : null,
      workerStatus: isSolving ? 'Optimizing' : scheduleResult ? 'Idle' : 'Standby',
      validatorStatus: validationResult?.status === 'VALID' ? 'Active' : validationResult ? 'Warning' : 'Standby',
      activePlanVersionId: planVersion?.plan_version_id || null,
      activeScheduleIdentity: planVersion?.schedule_identity || null,
    });
  }, [
    scenario.scenario_id,
    corridor.name,
    scheduleResult,
    tasks.length,
    trains.length,
    isSolving,
    validationResult,
    planVersion,
    updateTelemetry,
  ]);

  return (
    <>
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden p-2 sm:p-2.5 lg:p-3 gap-2 bg-[#04070D] font-sans max-w-[1920px] w-full mx-auto">
        {/* ============================================================== */}
        {/* ============================================================== */}
        {/* TOP BAR: TRACKMELD PLANNING OPERATIONAL METADATA & ACTIONS     */}
        {/* ============================================================== */}
        <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-2.5 bg-[#0B1120] border border-[#1A263D] rounded-xl px-3.5 py-2.5 shrink-0 shadow-xs">
          {/* Left: Planning Operational Context & Authoritative 3-Stage Lifecycle */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-[#F8FAFC]">Planning Workspace</span>
              <span className="text-xs text-[#64748B] font-mono">/</span>
              <span className="text-xs font-semibold text-[#93C5FD]">Corridor Schedule</span>
              <span className="text-xs font-mono text-[#64748B] hidden md:inline">•</span>
              <span className="text-xs font-medium text-slate-300">NDLS → CNB (440 km Trunk)</span>
              <span className="text-xs font-mono text-[#64748B] hidden md:inline">•</span>
              <span className="text-xs font-medium text-slate-400">
                Scenario A (24h Window)
                {(scenarioProvenance === 'synthetic' || scenario.is_synthetic || (scenario.classification && scenario.classification !== 'REAL')) && (
                  <span className="ml-1 text-[10px] font-mono text-amber-400">(Synthetic Fixture)</span>
                )}
              </span>
              {scheduleProvenance === 'synthetic' && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 font-medium">
                  DEMO SCHEDULE (SYNTHETIC)
                </span>
              )}
              {scheduleProvenance === 'backend' && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-medium">
                  {scenario.is_synthetic || (scenario.classification && scenario.classification !== 'REAL')
                    ? 'BACKEND SCHEDULE (SYNTHETIC SCENARIO)'
                    : 'BACKEND SCHEDULE'}
                </span>
              )}
            </div>

            <div className="h-3.5 w-[1px] bg-[#1A263D] hidden sm:block" />

            {/* Authoritative 3-Stage Pipeline: Solver -> Validation -> Governance */}
            <div className="flex items-center rounded-lg bg-[#070D18] border border-[#1A263D] p-0.5 text-[10px] font-mono shrink-0 overflow-x-auto scrollbar-none max-w-full">
              {/* Stage 1: Solver */}
              <div
                className={`px-2 py-0.5 rounded flex items-center gap-1 shrink-0 ${
                  isSolving
                    ? 'bg-blue-950/80 text-blue-300 font-bold animate-pulse'
                    : !scheduleResult
                      ? 'text-zinc-500 font-medium'
                      : scheduleResult.status === 'OPTIMAL'
                        ? 'text-[#38BDF8] font-bold bg-[#162238]'
                        : scheduleResult.status === 'FEASIBLE'
                          ? 'text-blue-400 font-bold'
                          : 'text-rose-400 font-bold'
                }`}
                title="Stage 1: CP-SAT Discrete Optimization"
              >
                <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold">1</span>
                <span>
                  {isSolving
                    ? 'SOLVER: RUNNING'
                    : !scheduleResult
                      ? 'SOLVER: IDLE'
                      : `CP-SAT ${scheduleResult.status}`}
                </span>
              </div>

              <span className="text-[#334155] px-0.5 shrink-0">→</span>

              {/* Stage 2: Validation Firewall */}
              <div
                className={`px-2 py-0.5 rounded flex items-center gap-1 shrink-0 ${
                  !validationResult
                    ? 'text-zinc-500 font-medium'
                    : validationResult.status === 'VALID'
                      ? 'text-emerald-400 font-bold bg-emerald-950/40'
                      : 'text-rose-400 font-bold bg-rose-950/40'
                }`}
                title="Stage 2: Independent Feasibility Validation"
              >
                <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold">2</span>
                <span>
                  {!validationResult
                    ? 'VALIDATION: STANDBY'
                    : validationResult.status === 'VALID'
                      ? 'FEASIBLE (0 ERRORS)'
                      : 'VALIDATION FAILED'}
                </span>
              </div>

              <span className="text-[#334155] px-0.5 shrink-0">→</span>

              {/* Stage 3: Four-Eyes Governance Approval */}
              <div
                className={`px-2 py-0.5 rounded flex items-center gap-1 shrink-0 ${
                  !scheduleResult || !validationResult
                    ? 'text-zinc-600 font-medium'
                    : !validationResult.is_approvable
                      ? 'text-rose-400 font-bold bg-rose-950/40'
                      : scheduleProvenance === 'synthetic'
                        ? 'text-amber-400 font-bold bg-amber-950/40'
                        : !planVersion
                          ? 'text-amber-400 font-bold bg-amber-950/40'
                          : planVersion.schedule_identity !== validationResult.schedule_identity
                            ? 'text-rose-400 font-bold bg-rose-950/40'
                            : planVersion.status === 'APPROVED'
                              ? 'text-emerald-400 font-bold bg-emerald-950/50'
                              : 'text-amber-400 font-bold bg-amber-950/40'
                }`}
                title="Stage 3: Four-Eyes Human Governance Sign-Off"
              >
                <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold">3</span>
                <span>
                  {!scheduleResult || !validationResult
                    ? 'GOVERNANCE: BLOCKED'
                    : !validationResult.is_approvable
                      ? 'VALIDATION FAILED'
                      : scheduleProvenance === 'synthetic'
                        ? 'DEMO • READ ONLY'
                        : !planVersion
                          ? 'UNPERSISTED CANDIDATE'
                          : planVersion.schedule_identity !== validationResult.schedule_identity
                            ? 'IDENTITY MISMATCH'
                            : planVersion.status === 'APPROVED'
                              ? 'APPROVED'
                              : 'PENDING FOUR-EYES'}
                </span>
              </div>
            </div>
          </div>

          {/* Right: Operational Actions Hierarchy */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Primary Workflow Actions (Tier 1) */}
            <div className="flex items-center gap-2">
              {/* Run Optimization (Dominant Primary CTA) */}
              <Button
                size="sm"
                disabled={isSolving}
                onClick={handleTriggerSolve}
                className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-semibold px-3.5 h-8 shadow-xs cursor-pointer transition-colors flex items-center gap-1.5 rounded-lg"
              >
                <Play className={`w-3.5 h-3.5 fill-current ${isSolving ? 'animate-spin' : ''}`} />
                <span>{isSolving ? 'Optimizing...' : 'Run Optimization'}</span>
              </Button>

              {/* Persist Candidate as PlanVersion (Supported API Workflow) */}
              {scheduleResult && !planVersion && scheduleProvenance === 'backend' && (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={isPersisting || !validationResult?.is_approvable}
                  onClick={handlePersistCandidatePlan}
                  className="bg-amber-950/40 hover:bg-amber-900/50 border-amber-500/40 text-amber-300 text-xs font-semibold h-8 px-3 cursor-pointer flex items-center gap-1.5 transition-colors rounded-lg"
                  title={
                    !validationResult?.is_approvable
                      ? 'Independent validation must certify plan before persistence'
                      : 'Persist this candidate schedule via supported backend API to issue an authoritative PlanVersion ID'
                  }
                >
                  <Database className={`w-3.5 h-3.5 text-amber-400 ${isPersisting ? 'animate-spin' : ''}`} />
                  <span>{isPersisting ? 'Persisting...' : 'Persist Plan Candidate'}</span>
                </Button>
              )}

              {/* Approve Plan (Distinct Governance Action) */}
              <Button
                size="sm"
                variant="outline"
                disabled={
                  !scheduleResult ||
                  !validationResult?.is_approvable ||
                  scheduleProvenance !== 'backend' ||
                  !planVersion ||
                  planVersion.schedule_identity !== validationResult.schedule_identity ||
                  planVersion.status === 'APPROVED' ||
                  planVersion.status === 'REJECTED'
                }
                onClick={() => setIsApprovalOpen(true)}
                className={`text-xs font-semibold h-8 px-3 cursor-pointer flex items-center gap-1.5 transition-colors rounded-lg ${
                  scheduleResult &&
                  validationResult?.is_approvable &&
                  scheduleProvenance === 'backend' &&
                  planVersion &&
                  planVersion.schedule_identity === validationResult.schedule_identity &&
                  planVersion.status !== 'APPROVED' &&
                  planVersion.status !== 'REJECTED'
                    ? 'bg-emerald-950/50 hover:bg-emerald-900/60 border-emerald-500/50 text-emerald-300 shadow-xs'
                    : 'border-[#1A263D] text-[#64748B] opacity-50 cursor-not-allowed bg-transparent'
                }`}
                title={
                  !scheduleResult
                    ? 'Run optimization before submitting for governance sign-off'
                    : !validationResult?.is_approvable
                      ? 'Independent validation must certify plan before approval'
                      : scheduleProvenance !== 'backend'
                        ? 'Synthetic demo plans are read-only and cannot be submitted for governance approval'
                        : !planVersion
                          ? 'Schedule candidate has not been persisted as an authoritative plan version'
                          : planVersion.schedule_identity !== validationResult.schedule_identity
                            ? 'Cryptographic identity mismatch between plan version and validation certification'
                            : planVersion.status === 'APPROVED'
                              ? 'Plan is already approved'
                              : planVersion.status === 'REJECTED'
                                ? 'Plan was rejected'
                                : 'Open Four-Eyes Governance Sign-Off'
                }
              >
                <FileCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>
                  {planVersion?.status === 'APPROVED'
                    ? 'Approved'
                    : planVersion?.status === 'REJECTED'
                      ? 'Rejected'
                      : !planVersion && scheduleResult
                        ? 'Unpersisted Plan'
                        : planVersion && validationResult && planVersion.schedule_identity !== validationResult.schedule_identity
                          ? 'Identity Mismatch'
                          : 'Approve'}
                </span>
              </Button>
            </div>

            {/* Analytical Tools Toolbar (Tier 2) */}
            <div className="inline-flex items-center bg-[#070D18] border border-[#1A263D] rounded-lg p-0.5">
              <button
                type="button"
                onClick={() => setActiveViewMode('VALIDATION')}
                className="px-2.5 py-1 text-xs font-medium text-[#CBD5E1] hover:text-white hover:bg-[#162238] rounded-md transition-colors flex items-center gap-1.5 cursor-pointer"
                title="Jump to Independent Feasibility Validation Matrix"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Validate</span>
              </button>

              <button
                type="button"
                onClick={() => setIsBenchmarkOpen(true)}
                className="px-2.5 py-1 text-xs font-medium text-[#CBD5E1] hover:text-white hover:bg-[#162238] rounded-md transition-colors flex items-center gap-1.5 cursor-pointer"
                title="Compare plan versions, baselines, and benchmarks"
              >
                <GitCompare className="w-3.5 h-3.5 text-[#38BDF8]" />
                <span>Compare</span>
              </button>

              <button
                type="button"
                onClick={() => handleOpenDigitalTwin(selectedSectionCode || 'SEC-12')}
                className="px-2.5 py-1 text-xs font-medium text-[#CBD5E1] hover:text-white hover:bg-[#162238] rounded-md transition-colors flex items-center gap-1.5 cursor-pointer"
                title="Launch 3D Digital Twin environment"
              >
                <Box className="w-3.5 h-3.5 text-cyan-400" />
                <span>3D Twin</span>
              </button>
            </div>

            {/* Workspace & Inspection Utilities (Tier 3) */}
            <div className="inline-flex items-center bg-[#070D18] border border-[#1A263D] rounded-lg p-0.5">
              <button
                type="button"
                onClick={() => setIsInspectorOpen((prev) => !prev)}
                className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors flex items-center gap-1.5 cursor-pointer ${
                  isInspectorOpen
                    ? 'bg-[#162238] text-white border border-[#2563EB]/50'
                    : 'text-[#CBD5E1] hover:text-white hover:bg-[#162238] border border-transparent'
                }`}
                title={isInspectorOpen ? 'Close Inspector Drawer' : 'Open Contextual Entity Inspector'}
                aria-label="Inspector"
              >
                <PanelRight className="w-3.5 h-3.5 text-[#38BDF8]" />
                <span className="hidden sm:inline">Inspector</span>
              </button>

              <button
                type="button"
                onClick={() => setIsFullScreen((prev) => !prev)}
                className="px-2.5 py-1 text-xs font-medium text-[#CBD5E1] hover:text-white hover:bg-[#162238] rounded-md transition-colors flex items-center gap-1.5 cursor-pointer"
                title={isFullScreen ? 'Exit Full-Screen (Esc)' : 'Expand to Full-Screen Workspace'}
              >
                {isFullScreen ? (
                  <Minimize2 className="w-3.5 h-3.5 text-[#38BDF8]" />
                ) : (
                  <Maximize2 className="w-3.5 h-3.5 text-[#38BDF8]" />
                )}
                <span className="hidden sm:inline">{isFullScreen ? 'Exit' : 'Expand'}</span>
              </button>
            </div>
          </div>
        </div>

        {/* ============================================================== */}
        {/* WORKSPACE VIEW MODE SELECTOR (3-Panel Layout, Map, Timeline...)*/}
        {/* ============================================================== */}
        <div className="flex items-center gap-1 bg-[#0B1120] border border-[#1A263D] rounded-xl p-1 overflow-x-auto shrink-0 text-xs scrollbar-none">
          {/* 0. 3-Panel Integrated Workstation (Masterpiece Default) */}
          <button
            onClick={() => handleSelectViewMode('INTEGRATED')}
            className={`px-3 py-1 rounded-lg transition-colors flex items-center gap-1.5 whitespace-nowrap h-7.5 text-xs cursor-pointer ${
              activeViewMode === 'INTEGRATED'
                ? 'bg-[#162238] text-[#F8FAFC] border border-[#2563EB]/40 font-semibold shadow-xs'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#162238]/50 border border-transparent font-medium'
            }`}
          >
            <LayoutGrid className={`w-3.5 h-3.5 ${activeViewMode === 'INTEGRATED' ? 'text-[#38BDF8]' : 'text-[#64748B]'}`} />
            <span>3-Panel Workstation</span>
            <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">
              DEFAULT
            </span>
          </button>

          {/* 1. Railway Map */}
          <button
            onClick={() => handleSelectViewMode('MAP')}
            className={`px-3 py-1 rounded-lg transition-colors flex items-center gap-1.5 whitespace-nowrap h-7.5 text-xs cursor-pointer ${
              activeViewMode === 'MAP'
                ? 'bg-[#162238] text-[#F8FAFC] border border-[#2563EB]/40 font-semibold shadow-xs'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#162238]/50 border border-transparent font-medium'
            }`}
          >
            <MapIcon className={`w-3.5 h-3.5 ${activeViewMode === 'MAP' ? 'text-[#38BDF8]' : 'text-[#64748B]'}`} />
            <span>Railway Map</span>
          </button>

          {/* 2. Time-Space Diagram */}
          <button
            onClick={() => handleSelectViewMode('TIMESPACE')}
            className={`px-3 py-1 rounded-lg transition-colors flex items-center gap-1.5 whitespace-nowrap h-7.5 text-xs cursor-pointer ${
              activeViewMode === 'TIMESPACE'
                ? 'bg-[#162238] text-[#F8FAFC] border border-[#2563EB]/40 font-semibold shadow-xs'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#162238]/50 border border-transparent font-medium'
            }`}
          >
            <Clock className={`w-3.5 h-3.5 ${activeViewMode === 'TIMESPACE' ? 'text-[#38BDF8]' : 'text-[#64748B]'}`} />
            <span>Time-Space</span>
          </button>

          {/* 3. Corridor Timeline */}
          <button
            onClick={() => handleSelectViewMode('TIMELINE')}
            className={`px-3 py-1 rounded-lg transition-colors flex items-center gap-1.5 whitespace-nowrap h-7.5 text-xs cursor-pointer ${
              activeViewMode === 'TIMELINE'
                ? 'bg-[#162238] text-[#F8FAFC] border border-[#2563EB]/40 font-semibold shadow-xs'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#162238]/50 border border-transparent font-medium'
            }`}
          >
            <Layers className={`w-3.5 h-3.5 ${activeViewMode === 'TIMELINE' ? 'text-[#38BDF8]' : 'text-[#64748B]'}`} />
            <span>Corridor Timeline</span>
          </button>

          {/* 4. Tasks Queue */}
          <button
            onClick={() => handleSelectViewMode('TASKS')}
            className={`px-3 py-1 rounded-lg transition-colors flex items-center gap-1.5 whitespace-nowrap h-7.5 text-xs cursor-pointer ${
              activeViewMode === 'TASKS'
                ? 'bg-[#162238] text-[#F8FAFC] border border-[#2563EB]/40 font-semibold shadow-xs'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#162238]/50 border border-transparent font-medium'
            }`}
          >
            <GitBranch className={`w-3.5 h-3.5 ${activeViewMode === 'TASKS' ? 'text-[#38BDF8]' : 'text-[#64748B]'}`} />
            <span>Tasks Queue</span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#162238] text-[#93C5FD] border border-[#233556]">
              {tasks.length}
            </span>
          </button>

          {/* 5. Conflicts */}
          <button
            onClick={() => handleSelectViewMode('CONFLICTS')}
            className={`px-3 py-1 rounded-lg transition-colors flex items-center gap-1.5 whitespace-nowrap h-7.5 text-xs cursor-pointer ${
              activeViewMode === 'CONFLICTS'
                ? 'bg-[#162238] text-[#F8FAFC] border border-[#2563EB]/40 font-semibold shadow-xs'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#162238]/50 border border-transparent font-medium'
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            <span>Conflicts</span>
            <span className="text-[9.5px] font-mono px-1.5 py-0.2 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 font-bold ml-0.5">
              3
            </span>
          </button>

          {/* 6. Validation */}
          <button
            onClick={() => handleSelectViewMode('VALIDATION')}
            className={`px-3 py-1 rounded-lg transition-colors flex items-center gap-1.5 whitespace-nowrap h-7.5 text-xs cursor-pointer ${
              activeViewMode === 'VALIDATION'
                ? 'bg-[#162238] text-[#F8FAFC] border border-[#2563EB]/40 font-semibold shadow-xs'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#162238]/50 border border-transparent font-medium'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Validation</span>
            <span
              className={`w-1.5 h-1.5 rounded-full ml-0.5 ${
                validationResult?.status === 'VALID' ? 'bg-emerald-400' : 'bg-zinc-600'
              }`}
            />
          </button>

          {/* 7. Diagnostics */}
          <button
            onClick={() => handleSelectViewMode('DIAGNOSTICS')}
            className={`px-3 py-1 rounded-lg transition-colors flex items-center gap-1.5 whitespace-nowrap h-7.5 text-xs cursor-pointer ${
              activeViewMode === 'DIAGNOSTICS'
                ? 'bg-[#162238] text-[#F8FAFC] border border-[#2563EB]/40 font-semibold shadow-xs'
                : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#162238]/50 border border-transparent font-medium'
            }`}
          >
            <Activity className={`w-3.5 h-3.5 ${activeViewMode === 'DIAGNOSTICS' ? 'text-[#38BDF8]' : 'text-[#64748B]'}`} />
            <span>Diagnostics</span>
          </button>

          {/* 8. Copilot Explainer */}
          <button
            onClick={() => handleSelectViewMode('COPILOT')}
            className={`px-3 py-1 rounded-lg transition-colors flex items-center gap-1.5 whitespace-nowrap h-7.5 text-xs cursor-pointer ${
              activeViewMode === 'COPILOT'
                ? 'bg-[#162238] text-[#F8FAFC] border border-[#2563EB]/40 font-semibold shadow-xs'
                : 'text-[#93C5FD] hover:text-[#F8FAFC] hover:bg-[#162238]/50 border border-transparent font-medium'
            }`}
          >
            <Bot className="w-3.5 h-3.5 text-[#38BDF8]" />
            <span>Copilot Explainer</span>
            <Sparkles className="w-2.5 h-2.5 text-[#60A5FA]" />
          </button>
        </div>

        {/* Solver Progress Banner */}
        {isSolving && (
          <div className="bg-[#0B1120] border border-[#2563EB]/40 rounded-xl px-3.5 py-2 flex items-center justify-between text-xs text-[#F8FAFC] shrink-0">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-3.5 h-3.5 text-[#38BDF8] animate-spin" />
              <span className="font-semibold">OPTIMIZING POSSESSION SCHEDULE:</span>
              <span className="text-[#94A3B8]">{solvingMessage}</span>
            </div>
            <span className="text-[10px] text-[#64748B] font-mono">Target: &lt; 5.0s</span>
          </div>
        )}

        {/* No-Data / Backend Unavailable Banner */}
        {!isSolving && scheduleResult === null && (
          <div className="bg-amber-950/20 border border-amber-500/30 rounded-xl px-3.5 py-2 flex items-center justify-between gap-2 text-xs text-amber-300 shrink-0">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <span>
                <span className="font-semibold">No schedule computed.</span>
                {' '}Backend unavailable or optimization has not yet run.
                Planning data is unverified — no approval decision can be made.
              </span>
            </div>
            <button
              onClick={handleLoadDemoSchedule}
              className="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 whitespace-nowrap cursor-pointer transition-colors"
              title="Explicitly load synthetic demonstration schedule"
            >
              Load Demo Schedule (Synthetic)
            </button>
          </div>
        )}

        {/* Error Alert */}
        {errorMessage && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl px-3.5 py-2 text-xs text-rose-300 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
            <button onClick={() => setErrorMessage(null)} className="text-[#94A3B8] hover:text-white text-xs cursor-pointer">
              Dismiss
            </button>
          </div>
        )}

        {/* Authoritative Operational Lifecycle Pipeline Bar */}
        <PlanLifecycleBar
          currentStage={
            isSolving
              ? 'OPTIMIZING'
              : planVersion?.status === 'APPROVED'
              ? 'APPROVED'
              : planVersion?.status === 'REJECTED'
              ? 'REJECTED'
              : validationResult?.status === 'VALID'
              ? 'AWAITING_REVIEW'
              : scheduleResult
              ? 'CANDIDATE'
              : 'DRAFT'
          }
          planVersionStatus={planVersion?.status}
          isApprovable={validationResult?.is_approvable ?? false}
          approvedBy={planVersion?.approved_by}
          onOpenApprovalModal={() => setIsApprovalOpen(true)}
        />

        {/* ============================================================== */}
        {/* MAIN OPERATING SURFACE                                         */}
        {/* ============================================================== */}
        <div
          className={
            isFullScreen
              ? 'fixed inset-0 z-50 bg-[#070B14] flex flex-col p-2.5 sm:p-3.5 overflow-hidden select-none'
              : 'flex-1 min-h-0 overflow-hidden flex gap-2.5'
          }
        >
          {isFullScreen && (
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#1E2D4A] shrink-0">
              <div className="flex items-center gap-3">
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[#2563EB]/20 text-[#38BDF8] border border-[#2563EB]/40">
                  FULL-SCREEN WORKSPACE
                </span>
                <h2 className="text-sm font-bold text-[#F8FAFC]">
                  {activeViewMode === 'INTEGRATED' && 'Corridor Railway Map (MapLibre Engine)'}
                  {activeViewMode === 'MAP' && 'Corridor Railway Map (MapLibre Engine)'}
                  {activeViewMode === 'TIMESPACE' && 'Corridor Time-Space Diagram'}
                  {activeViewMode === 'TIMELINE' && 'Corridor Gantt Schedule Timeline'}
                  {activeViewMode === 'TASKS' && 'Full Maintenance Task Queue'}
                  {activeViewMode === 'CONFLICTS' && 'Operational Conflict Resolution Engine'}
                  {activeViewMode === 'VALIDATION' && 'Independent Feasibility Validation Matrix'}
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

          {/* Central Workspace Container */}
          <div className="flex-1 min-w-0 h-full overflow-hidden flex flex-col">
            {/* VIEW MODE 0: INTEGRATED 3-PANEL WORKSTATION (MASTER REFERENCE) */}
            {activeViewMode === 'INTEGRATED' && (
              <div className="flex-1 w-full h-full min-h-0 flex flex-col gap-2.5 overflow-hidden">
                {/* TOP 48%: Railway View Card */}
                <div className="h-[48%] min-h-[280px] w-full bg-[#0B1120] border border-[#1A263D] rounded-xl overflow-hidden flex flex-col relative shrink-0">
                  <div className="h-8.5 px-3 bg-[#070D18] border-b border-[#1A263D] flex items-center justify-between shrink-0 select-none">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-xs text-[#F8FAFC]">Railway View</span>
                      <span className="text-[11px] font-mono text-[#94A3B8] hidden sm:inline">NDLS → CNB (440 km Trunk)</span>
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse ml-0.5" />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#162238] text-[#93C5FD] border border-[#1E2D4A] hidden md:inline">
                        4 STATIONS • 14 SECTIONS • 6 TRAINS
                      </span>
                      <button
                        onClick={() => setActiveViewMode('MAP')}
                        className="p-1 rounded text-[#94A3B8] hover:text-white hover:bg-[#162238] transition-colors cursor-pointer"
                        title="Maximize map view"
                        aria-label="Maximize map view"
                      >
                        <Maximize2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  <div className="flex-1 w-full min-h-0 relative">
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
                </div>

                {/* BOTTOM 52%: Split Tasks (50%) + Timeline/Time-Space (50%) */}
                <div className="flex-1 min-h-[300px] w-full flex flex-col lg:flex-row gap-2.5 overflow-hidden">
                  {/* Bottom-Left 50%: Task Overview */}
                  <div className="w-full lg:w-1/2 h-full bg-[#0B1120] border border-[#1A263D] rounded-xl overflow-hidden flex flex-col">
                    <TaskQueueTable
                      tasks={tasks}
                      scheduleResult={scheduleResult}
                      selectedTaskId={selectedTaskId}
                      onSelectTask={handleSelectTask}
                      isEmbedded={true}
                    />
                  </div>

                  {/* Bottom-Right 50%: Timeline / Time-Space Workspace */}
                  <div className="w-full lg:w-1/2 h-full bg-[#0B1120] border border-[#1A263D] rounded-xl overflow-hidden flex flex-col">
                    <div className="h-8.5 px-3 bg-[#070D18] border-b border-[#1A263D] flex items-center justify-between shrink-0 select-none">
                      <div className="flex items-center gap-1 text-xs">
                        <button
                          onClick={() => setBottomTab('TIMELINE')}
                          className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
                            bottomTab === 'TIMELINE'
                              ? 'bg-[#162238] text-[#38BDF8] border border-[#2563EB]/40'
                              : 'text-[#94A3B8] hover:text-white'
                          }`}
                        >
                          Timeline
                        </button>
                        <button
                          onClick={() => setBottomTab('TIMESPACE')}
                          aria-label="Motion Chart"
                          className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
                            bottomTab === 'TIMESPACE'
                              ? 'bg-[#162238] text-[#38BDF8] border border-[#2563EB]/40'
                              : 'text-[#94A3B8] hover:text-white'
                          }`}
                        >
                          Motion Chart
                        </button>
                        <button
                          onClick={() => setBottomTab('DIAGNOSTICS')}
                          className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
                            bottomTab === 'DIAGNOSTICS'
                              ? 'bg-[#162238] text-[#38BDF8] border border-[#2563EB]/40'
                              : 'text-[#94A3B8] hover:text-white'
                          }`}
                        >
                          Diagnostics
                        </button>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-[#94A3B8] hidden sm:inline">Oct 10, 2026</span>
                        <div className="flex items-center rounded-md bg-[#070D18] border border-[#1A263D] p-0.5 text-[10px] font-mono">
                          <span className="px-1.5 py-0.2 rounded bg-[#162238] text-[#38BDF8] font-bold">24h</span>
                          <span className="px-1.5 py-0.2 text-[#64748B]">48h</span>
                          <span className="px-1.5 py-0.2 text-[#64748B]">72h</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex-1 w-full min-h-0 overflow-hidden">
                      {bottomTab === 'TIMELINE' && (
                        <TimelineScheduleView
                          trains={trains}
                          tasks={tasks}
                          scheduleResult={scheduleResult}
                          selectedTaskId={selectedTaskId}
                          selectedTrainId={selectedTrainId}
                          selectedSectionCode={selectedSectionCode}
                          onSelectTask={handleSelectTask}
                          onSelectTrain={handleSelectTrain}
                          onSwitchToTimeSpace={() => setBottomTab('TIMESPACE')}
                          isEmbedded={true}
                        />
                      )}
                      {bottomTab === 'TIMESPACE' && (
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
                      )}
                      {bottomTab === 'DIAGNOSTICS' && (
                        <DiagnosticsWorkspace
                          task={selectedTask}
                          scheduleResult={scheduleResult}
                          diagnosticsReport={diagnosticsReport}
                          isSolving={isSolving}
                          solvingMessage={solvingMessage}
                          onTriggerSolve={handleTriggerSolve}
                          onSelectTask={handleSelectTask}
                        />
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* VIEW MODE 1: FULL GEOSPATIAL MAP */}
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
              <div className="flex-1 bg-[#0B1120] border border-[#1A263D] rounded-xl overflow-hidden">
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
              <div className="flex-1 bg-[#0B1120] border border-[#1A263D] rounded-xl overflow-hidden p-3">
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
                planVersion={planVersion}
                onOpenGovernance={() => setIsApprovalOpen(true)}
              />
            )}

            {/* VIEW MODE 7: DIAGNOSTICS WORKSPACE */}
            {activeViewMode === 'DIAGNOSTICS' && (
              <DiagnosticsWorkspace
                task={selectedTask}
                scheduleResult={scheduleResult}
                diagnosticsReport={diagnosticsReport}
                isSolving={isSolving}
                solvingMessage={solvingMessage}
                onTriggerSolve={handleTriggerSolve}
                onSelectTask={handleSelectTask}
              />
            )}

            {/* VIEW MODE 8: COPILOT WORKSPACE */}
            {activeViewMode === 'COPILOT' && (
              <CopilotWorkspace
                selectedTaskId={selectedTaskId}
                onSelectTask={handleSelectTask}
              />
            )}
          </div>

          {/* Docked Contextual Entity Inspector (Desktop Only) */}
          {isInspectorOpen && (activeViewMode === 'INTEGRATED' || activeViewMode === 'MAP') && (
            <div className="hidden xl:flex w-[360px] 2xl:w-[400px] shrink-0 h-full bg-[#0B1120] border border-[#1A263D] rounded-xl overflow-hidden shadow-xl flex-col">
              <EntityInspector
                task={selectedTask}
                scheduledInterval={selectedScheduled}
                diagnostic={selectedDiagnostic}
                conflictingTrains={trains.filter((tr) => tr.train_number === '02073')}
                selectedTrain={selectedTrain}
                selectedSection={selectedSection}
                selectedStation={selectedStation}
                selectedConflict={selectedConflict}
                isDrawer={false}
                hideHeader={false}
                onClose={() => setIsInspectorOpen(false)}
                onNavigateToDiagnostics={(tId) => {
                  setSelectedTaskId(tId);
                  setActiveViewMode('DIAGNOSTICS');
                }}
                onNavigateToConflicts={(tId) => {
                  setSelectedTaskId(tId);
                  setActiveViewMode('CONFLICTS');
                }}
                onOpenDigitalTwin={handleOpenDigitalTwin}
              />
            </div>
          )}
        </div>
      </div>

      {/* Contextual Entity Inspector Drawer (Mobile & Tablet, or Desktop when not in docked mode) */}
      <div className={activeViewMode === 'INTEGRATED' || activeViewMode === 'MAP' ? 'xl:hidden' : 'block'}>
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
      </div>

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
        task={selectedTask}
      />

      {/* Plan Comparison & Trade-Off Analysis Modal */}
      <ComparePlansModal
        isOpen={isBenchmarkOpen}
        onClose={() => setIsBenchmarkOpen(false)}
        scenarioId={scenario.scenario_id}
        baselineTasks={tasks}
        candidateSchedule={scheduleResult}
        validationResult={validationResult}
        planVersion={planVersion}
        onTriggerSolve={handleTriggerSolve}
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
    </>
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
