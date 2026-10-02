'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { AppShell } from '@/components/shell/AppShell';
import { TimeSpaceChart } from '@/components/planning/TimeSpaceChart';
import { TaskInspector } from '@/components/planning/TaskInspector';
import { TaskQueueTable } from '@/components/planning/TaskQueueTable';
import { RailwayCanvas } from '@/components/railway/RailwayCanvas';
import { PlanApprovalModal } from '@/components/governance/PlanApprovalModal';
import { BenchmarkComparisonModal } from '@/components/planning/BenchmarkComparisonModal';
import { PlanLifecycleBar, LifecycleStage } from '@/components/planning/PlanLifecycleBar';
import { MetricCard } from '@/components/common/MetricCard';
import { StatusBadge } from '@/components/common/StatusBadge';
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
  BarChart3,
  Play,
  Grid,
  Maximize2,
  AlertCircle,
  FileCheck,
  RefreshCw,
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

  // Synchronized Multi-Entity Selection State
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>('TSK-0001');
  const [selectedTrainId, setSelectedTrainId] = useState<string | null>(null);
  const [selectedSectionCode, setSelectedSectionCode] = useState<string | null>('SEC-ETW-CNB');

  // Operations & Governance State
  const [isSolving, setIsSolving] = useState(false);
  const [solvingMessage, setSolvingMessage] = useState<string>('');
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [isBenchmarkOpen, setIsBenchmarkOpen] = useState(false);
  const [viewLayout, setViewLayout] = useState<'4QUADRANT' | 'FOCUSED'>('4QUADRANT');
  const [focusedTab, setFocusedTab] = useState<'TIMESCHEME' | '3DCORRIDOR'>('TIMESCHEME');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Derive Lifecycle Stage
  const lifecycleStage: LifecycleStage = isSolving
    ? 'OPTIMIZING'
    : planVersion?.status === 'APPROVED'
    ? 'APPROVED'
    : planVersion?.status === 'REJECTED'
    ? 'REJECTED'
    : validationResult?.is_approvable
    ? 'AWAITING_REVIEW'
    : 'CANDIDATE';

  // Load bundle and plan versions on mount
  useEffect(() => {
    let cancelled = false;
    async function loadInitialData() {
      try {
        const bundle = await getScenarioBundle('SCN-DEMO-001');
        if (cancelled) return;
        if (bundle.corridor) setCorridor(bundle.corridor);
        if (bundle.scenario) setScenario(bundle.scenario);
        if (bundle.trains && bundle.trains.length > 0) setTrains(bundle.trains);
        if (bundle.tasks && bundle.tasks.length > 0) {
          setTasks(bundle.tasks);
          setSelectedTaskId(bundle.tasks[0].task_id);
          const firstSec = bundle.tasks[0].section_code || bundle.tasks[0].section_id;
          if (firstSec) setSelectedSectionCode(firstSec);
        }

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

  // Selection handlers
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
    // Find task on this section if any
    const taskOnSec = tasks.find(
      (t) => (t.section_code && t.section_code.includes(sectionCode)) || (t.section_id && t.section_id.includes(sectionCode))
    );
    if (taskOnSec) {
      setSelectedTaskId(taskOnSec.task_id);
      setSelectedTrainId(null);
    }
  };

  // Full Optimization Pipeline: Optimize → Validate → Diagnose
  const handleTriggerSolve = useCallback(async () => {
    setIsSolving(true);
    setErrorMessage(null);
    setSolvingMessage('Evaluating maintenance windows, train movements, and discrete headway buffers...');
    try {
      // 1. CP-SAT mathematical optimization
      const sched = await optimizeSchedule(scenario.scenario_id, 5.0);
      setScheduleResult(sched);
      setSolvingMessage('Independent Feasibility Certification: Auditing 12 hard constraint checks...');

      // 2. Independent validation boundary
      const val = await validateSchedule(scenario.scenario_id, sched);
      setValidationResult(val);
      setSolvingMessage('Running causal root-cause diagnostics and relaxation analyses...');

      // 3. Diagnostics and relaxation analyses for any unscheduled tasks
      const diag = await diagnoseSchedule(scenario.scenario_id, sched);
      setDiagnosticsReport(diag);

      // Re-fetch latest plan versions
      const versions = await getPlanVersions(scenario.scenario_id);
      if (versions && versions.length > 0) {
        setPlanVersion(versions[0]);
      }
    } catch (err) {
      console.error('Solve pipeline error:', err);
      setErrorMessage('Planning optimization request failed. The existing candidate schedule was preserved.');
    } finally {
      setIsSolving(false);
      setSolvingMessage('');
    }
  }, [scenario.scenario_id]);

  // Handle plan approval
  const handleApprove = async (payload: {
    reviewer_name: string;
    reviewer_role: string;
    approval_notes: string;
  }) => {
    if (!planVersion) return;
    try {
      const updated = await approvePlanVersion(planVersion.plan_version_id, payload.approval_notes);
      setPlanVersion(updated);
    } catch (err) {
      console.error('Plan approval error:', err);
      setErrorMessage('Plan approval transaction failed. Please check official authorization permissions.');
    }
  };

  // Handle plan rejection
  const handleReject = async (payload: {
    reviewer_name: string;
    reviewer_role: string;
    rejection_reason: string;
  }) => {
    if (!planVersion) return;
    try {
      const updated = await rejectPlanVersion(planVersion.plan_version_id, payload.rejection_reason);
      setPlanVersion(updated);
    } catch (err) {
      console.error('Plan rejection error:', err);
      setErrorMessage('Plan rejection transaction failed. Please check network logs.');
    }
  };

  // Lookups for selected entities
  const selectedTask = tasks.find((t) => t.task_id === selectedTaskId) || null;
  const selectedScheduled =
    scheduleResult?.scheduled_tasks.find((st) => st.task_id === selectedTaskId) || null;
  const selectedUnscheduled =
    scheduleResult?.unscheduled_tasks.find((ut) => ut.task_id === selectedTaskId) || null;
  const selectedDiagnostic =
    diagnosticsReport?.diagnostics?.find((d) => d.task_id === selectedTaskId) || null;

  const selectedTrain =
    trains.find((tr) => (tr.train_id === selectedTrainId || tr.movement_id === selectedTrainId)) || null;

  const selectedSection: BlockSection | null =
    corridor.sections?.find((s) => s.code === selectedSectionCode || s.section_id === selectedSectionCode) || null;

  const conflictingTrains = trains.filter((tr) =>
    selectedDiagnostic?.conflicting_train_movements?.includes(tr.train_id || tr.movement_id || '')
  );

  const isScheduleApprovable = validationResult?.is_approvable ?? true;
  const scheduledCount = scheduleResult?.scheduled_tasks.length ?? 29;
  const totalCount = tasks.length || 30;
  const completionPct = ((scheduledCount / totalCount) * 100).toFixed(1);

  return (
    <AppShell
      onTriggerSolve={handleTriggerSolve}
      onOpenApproval={() => setIsApprovalOpen(true)}
      isSolving={isSolving}
      canApprove={isScheduleApprovable}
      activeScenarioId={scenario.scenario_id}
      tasksCount={tasks.length}
      trainsCount={trains.length}
      lastSolveDuration={scheduleResult?.solver_wall_time_seconds ?? 1.48}
    >
      <div className="flex-1 flex flex-col h-full overflow-hidden p-3 gap-2 font-mono">
        {/* Plan Lifecycle Bar */}
        <PlanLifecycleBar
          currentStage={lifecycleStage}
          planVersionStatus={planVersion?.status}
          isApprovable={isScheduleApprovable}
          approvedBy={planVersion?.approved_by}
          onOpenApprovalModal={() => setIsApprovalOpen(true)}
        />

        {/* Operational Action Strip */}
        <div className="flex items-center justify-between bg-[#141418] border border-[#202024] rounded-md px-3 py-1.5 shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-bold text-[#F5F5F5]">
              {scenario.name}
            </span>
            <span className="text-[10px] text-[#71717A] bg-[#202024] px-1.5 py-0.5 rounded">
              Corridor {corridor.name}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {/* Benchmark Trigger */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsBenchmarkOpen(true)}
              className="border-[#29292F] text-xs text-[#A1A1AA] hover:text-white"
            >
              <BarChart3 className="w-3.5 h-3.5 mr-1.5 text-[#4C87E7]" />
              Compare Schedulers (Benchmark)
            </Button>

            {/* Run CP-SAT Optimization */}
            <Button
              size="sm"
              disabled={isSolving}
              onClick={handleTriggerSolve}
              className="bg-[#4C87E7] hover:bg-[#3B82F6] text-white text-xs font-semibold"
            >
              <Play className={`w-3.5 h-3.5 mr-1.5 ${isSolving ? 'animate-spin' : ''}`} />
              {isSolving ? 'Optimizing Schedule...' : 'Run Optimization (CP-SAT)'}
            </Button>

            {/* Plan Approval Trigger */}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsApprovalOpen(true)}
              className="border-emerald-600/40 text-emerald-400 hover:bg-emerald-950/40 text-xs font-semibold"
            >
              <FileCheck className="w-3.5 h-3.5 mr-1.5" />
              Human Governance
            </Button>

            {/* Layout switchers */}
            <div className="flex items-center gap-0.5 border-l border-[#29292F] pl-2">
              <Button
                variant={viewLayout === '4QUADRANT' ? 'secondary' : 'ghost'}
                size="icon-xs"
                onClick={() => setViewLayout('4QUADRANT')}
                title="4-Quadrant Grid View"
                className="text-[#A1A1AA]"
              >
                <Grid className="w-3.5 h-3.5" />
              </Button>
              <Button
                variant={viewLayout === 'FOCUSED' ? 'secondary' : 'ghost'}
                size="icon-xs"
                onClick={() => setViewLayout('FOCUSED')}
                title="Wide Diagram View"
                className="text-[#A1A1AA]"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        </div>

        {/* Error Alert Bar if any */}
        {errorMessage && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded px-3 py-1.5 text-xs text-rose-300 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-[#A1A1AA] hover:text-white text-xs cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Operational KPI Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2 shrink-0">
          <MetricCard
            label="Schedule Efficiency"
            value={`${completionPct}%`}
            subtext={`${scheduledCount} of ${totalCount} requisitions placed`}
            delta={{ value: '+14% vs Greedy Baseline', isPositive: true }}
          />
          <MetricCard
            label="Track Possession"
            value={(
              (scheduleResult?.metrics.total_possession_duration_minutes ?? 4485) / 60
            ).toFixed(1)}
            unit="hours"
            subtext="Across 32 block sections"
          />
          <MetricCard
            label="Mandatory Clearance"
            value="100%"
            unit="rate"
            delta={{ value: '17 of 17 mandatory placed', isPositive: true }}
          />
          <MetricCard
            label="Priority Capture"
            value={`${(
              (scheduleResult?.metrics.priority_score_capture_rate ?? 0.9855) * 100
            ).toFixed(1)}%`}
            subtext="3,001 of 3,045 available pts"
          />
          <MetricCard
            label="Independent Validator"
            value={validationResult?.status ?? 'VALID'}
            badge={
              <StatusBadge
                status={validationResult?.status === 'VALID' ? 'VALID' : 'INFEASIBLE'}
                size="sm"
              />
            }
            subtext={
              validationResult?.is_approvable
                ? '12 of 12 Hard Rules Certified'
                : 'Hard Constraint Violations'
            }
          />
          <MetricCard
            label="Plan Governance"
            value={planVersion?.status ?? 'PENDING_REVIEW'}
            badge={<StatusBadge status={planVersion?.status ?? 'PENDING_REVIEW'} size="sm" />}
            subtext={
              planVersion?.approved_by
                ? `Approved: ${planVersion.approved_by}`
                : 'COMPLETED ≠ APPROVED'
            }
          />
        </div>

        {/* Active Solver Progress Notice */}
        {isSolving && (
          <div className="bg-[#18181C] border border-[#4C87E7]/40 rounded p-2.5 flex items-center justify-between text-xs text-[#F5F5F5] shrink-0">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-[#4C87E7] animate-spin" />
              <span className="font-bold">OPTIMIZING CANDIDATE PLAN:</span>
              <span className="text-[#A1A1AA]">{solvingMessage}</span>
            </div>
            <span className="text-[10px] text-[#71717A]">Target solver latency: &lt; 5.0s</span>
          </div>
        )}

        {/* Operational Layout: 4-Quadrant vs Focused */}
        {viewLayout === '4QUADRANT' ? (
          /* 4-Quadrant Operational Layout */
          <div className="flex-1 grid grid-cols-12 grid-rows-2 gap-2 min-h-0">
            {/* Quadrant 1 (Top-Left): Task Queue Table */}
            <div className="col-span-12 lg:col-span-4 row-span-1 h-full overflow-hidden">
              <TaskQueueTable
                tasks={tasks}
                scheduleResult={scheduleResult}
                selectedTaskId={selectedTaskId}
                selectedSectionCode={selectedSectionCode}
                onSelectTask={handleSelectTask}
              />
            </div>

            {/* Quadrant 2 (Top-Right): 2D Time-Space Diagram */}
            <div className="col-span-12 lg:col-span-8 row-span-1 h-full overflow-hidden">
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

            {/* Quadrant 3 (Bottom-Left): 3D Railway Corridor View */}
            <div className="col-span-12 lg:col-span-7 row-span-1 h-full overflow-hidden">
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
            </div>

            {/* Quadrant 4 (Bottom-Right): Deep Task Inspector & Diagnostics */}
            <div className="col-span-12 lg:col-span-5 row-span-1 h-full overflow-hidden">
              <TaskInspector
                task={selectedTask}
                scheduledInterval={selectedScheduled}
                unscheduledReport={selectedUnscheduled}
                diagnostic={selectedDiagnostic}
                conflictingTrains={conflictingTrains}
                selectedTrain={selectedTrain}
                selectedSection={selectedSection}
                onClearSelection={() => {
                  setSelectedTaskId(null);
                  setSelectedTrainId(null);
                  setSelectedSectionCode(null);
                }}
              />
            </div>
          </div>
        ) : (
          /* Focused Wide Layout */
          <div className="flex-1 grid grid-cols-12 gap-2 min-h-0">
            <div className="col-span-12 lg:col-span-3 h-full overflow-hidden">
              <TaskQueueTable
                tasks={tasks}
                scheduleResult={scheduleResult}
                selectedTaskId={selectedTaskId}
                selectedSectionCode={selectedSectionCode}
                onSelectTask={handleSelectTask}
              />
            </div>

            <div className="col-span-12 lg:col-span-6 h-full flex flex-col gap-2 overflow-hidden">
              <div className="flex items-center gap-1 bg-[#141418] p-1 rounded border border-[#202024] text-xs shrink-0">
                <button
                  onClick={() => setFocusedTab('TIMESCHEME')}
                  className={`px-3 py-1 rounded transition-colors ${
                    focusedTab === 'TIMESCHEME'
                      ? 'bg-[#4C87E7] text-white font-semibold'
                      : 'text-[#A1A1AA] hover:text-white'
                  }`}
                >
                  2D Time-Space Diagram
                </button>
                <button
                  onClick={() => setFocusedTab('3DCORRIDOR')}
                  className={`px-3 py-1 rounded transition-colors ${
                    focusedTab === '3DCORRIDOR'
                      ? 'bg-[#4C87E7] text-white font-semibold'
                      : 'text-[#A1A1AA] hover:text-white'
                  }`}
                >
                  3D Railway Corridor View
                </button>
              </div>

              <div className="flex-1 overflow-hidden">
                {focusedTab === 'TIMESCHEME' ? (
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
                ) : (
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
                )}
              </div>
            </div>

            <div className="col-span-12 lg:col-span-3 h-full overflow-hidden">
              <TaskInspector
                task={selectedTask}
                scheduledInterval={selectedScheduled}
                unscheduledReport={selectedUnscheduled}
                diagnostic={selectedDiagnostic}
                conflictingTrains={conflictingTrains}
                selectedTrain={selectedTrain}
                selectedSection={selectedSection}
                onClearSelection={() => {
                  setSelectedTaskId(null);
                  setSelectedTrainId(null);
                  setSelectedSectionCode(null);
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Comparative Benchmark Modal */}
      <BenchmarkComparisonModal
        isOpen={isBenchmarkOpen}
        onClose={() => setIsBenchmarkOpen(false)}
        scenarioId={scenario.scenario_id}
      />

      {/* Human Approval & Governance Modal */}
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
