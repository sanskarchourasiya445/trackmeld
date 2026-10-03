/**
 * Planning, Optimization, Validation, Diagnostics, and Governance domain types.
 * Matches TrackMeld backend schemas exactly.
 */

export type SchedulerType = 'FCFS' | 'PRIORITY_GREEDY' | 'CP_SAT';

export type PlanningRunStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'VALIDATING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCEL_REQUESTED'
  | 'CANCELLED'
  | 'TIMED_OUT';

export type PlanningRunStage =
  | 'QUEUED'
  | 'CLAIMED'
  | 'LOADING_SNAPSHOT'
  | 'SOLVING'
  | 'VALIDATING'
  | 'DIAGNOSING'
  | 'PERSISTING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'TIMED_OUT';

export type PlanVersionStatus =
  | 'PENDING_REVIEW'
  | 'UNDER_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'SUPERSEDED';

export interface TimeInterval {
  start: string; // ISO-8601
  end: string;
}

export interface ScheduledTaskInterval {
  task_id: string;
  task_code?: string;
  interval?: TimeInterval;
  possession_interval?: TimeInterval;
  start_time?: string; // Compatibility with legacy mock
  end_time?: string;
  duration_minutes: number;
  assigned_track?: string;
  affected_sections?: string[];
  section_code?: string;
  assigned_resources?: string[];
  crew_id?: string;
  priority_score?: number;
  priority_breakdown?: {
    mandatory?: number;
    urgency?: number;
    window_tightness?: number;
    dependency_bottleneck?: number;
    operational_impact?: number;
  };
  sequence_order?: number;
  scheduling_reason?: string;
  rule_evidence_ids?: string[];
  shadow_possession_with?: string[];
  is_parallel_compatible?: boolean;
}

export interface UnscheduledTaskReport {
  task_id: string;
  task_code?: string;
  mandatory?: boolean;
  priority_score?: number;
  reason_codes?: string[];
  reason_code?: string;
  primary_constraint?: string;
  details?: string;
  diagnostic_message?: string;
  conflicts?: unknown[];
  attempted_candidates_count?: number;
}

export interface ValidationFinding {
  rule_code: string;
  rule_name?: string;
  severity: 'CRITICAL' | 'ERROR' | 'WARNING' | 'INFO';
  target_type?: 'TASK' | 'SECTION' | 'TRAIN' | 'GLOBAL' | string;
  target_id?: string;
  message: string;
  passed?: boolean;
  timestamp?: string;
}

export interface ScheduleValidationResult {
  status: 'VALID' | 'INVALID' | 'UNKNOWN';
  valid: boolean;
  is_approvable: boolean;
  findings: ValidationFinding[];
  error_count: number;
  warning_count: number;
  info_count: number;
  checked_task_count: number;
  checked_section_count: number;
  checked_resource_count: number;
  checked_train_movement_count: number;
  validator_version?: string;
  input_snapshot_id?: string;
  schedule_identity: string;
  validation_runtime_ms?: number;
  checks_executed: string[];
  approval_gate_message: string;
}

export interface RelaxationFinding {
  scenario_type: string;
  description: string;
  feasible: boolean;
  candidate_start?: string | null;
  candidate_end?: string | null;
  blocking_entities?: string[];
  relaxation_magnitude?: string | null;
  hypothetical: boolean;
  approvable: boolean;
  explanation: string;
}

export interface UnscheduledTaskDiagnostic {
  task_id: string;
  task_code: string;
  mandatory: boolean;
  priority_score?: number | null;
  status: 'DIAGNOSED' | string;
  primary_reason: string;
  reason_codes: string[];
  conflicting_tasks?: string[];
  conflicting_train_movements?: string[];
  conflicting_resources?: string[];
  conflicting_windows?: string[];
  dependency_blockers?: string[];
  affected_sections?: string[];
  rule_blockers?: string[];
  evidence?: Record<string, unknown>;
  relaxation_analyses?: RelaxationFinding[];
}

export interface DiagnosticsReport {
  scenario_id: string;
  snapshot_id: string;
  total_unscheduled_tasks: number;
  diagnostics: UnscheduledTaskDiagnostic[];
  execution_time_ms: number;
}

export interface ScheduleMetrics {
  total_tasks: number;
  scheduled_tasks: number;
  unscheduled_tasks: number;
  completion_rate: number;
  mandatory_tasks?: number;
  mandatory_scheduled?: number;
  mandatory_unscheduled?: number;
  mandatory_completion_rate?: number;
  total_scheduled_duration_minutes?: number;
  total_possession_duration_minutes?: number;
  total_priority_score_available?: number;
  scheduled_priority_score?: number;
  unscheduled_priority_score?: number;
  priority_score_capture_rate?: number;
  earliest_scheduled_start?: string;
  latest_scheduled_end?: string;
  // Legacy compatibility fields:
  total_requested_tasks?: number;
  total_possession_hours?: number;
  total_train_impact_delay_minutes?: number;
  shadow_bundling_count?: number;
  completion_rate_pct?: number;
}

export interface ScheduleResult {
  scenario_id: string;
  scheduler_type: SchedulerType;
  status: 'OPTIMAL' | 'FEASIBLE' | 'INFEASIBLE' | 'UNKNOWN';
  solver_wall_time_seconds: number;
  objective_value?: number;
  best_bound?: number;
  scheduled_tasks: ScheduledTaskInterval[];
  unscheduled_tasks: UnscheduledTaskReport[];
  validation_summary?: ScheduleValidationResult;
  diagnostics?: UnscheduledTaskDiagnostic[];
  metrics: ScheduleMetrics;
}

export interface BenchmarkComparisonRow {
  metric: string;
  FCFS?: string | number;
  'Priority-Greedy'?: string | number;
  'CP-SAT'?: string | number;
  [key: string]: unknown;
}

export interface BenchmarkComparisonResult {
  scenario_id: string;
  snapshot_id: string;
  planning_start: string;
  planning_end: string;
  schedules: Record<string, ScheduleResult>;
  comparison_table: BenchmarkComparisonRow[];
}

export interface PlanningRun {
  run_id: string;
  scenario_id: string;
  status: PlanningRunStatus;
  stage?: PlanningRunStage;
  scheduler_type: SchedulerType;
  scheduler_version?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  execution_duration_ms?: number;
  validation_status?: string;
  is_approvable: boolean;
  random_seed?: number;
  solver_name?: string;
  solver_version?: string;
  dataset_version?: string;
  input_hash?: string;
  schedule_identity?: string;
  error_code?: string;
  error_message?: string;
  progress?: {
    stage: PlanningRunStage;
    message: string;
    percent_complete?: number;
  };
  result_summary?: Record<string, unknown>;
}

export interface PlanVersion {
  id?: string;
  plan_version_id: string;
  planning_run_id: string;
  scenario_id: string;
  version_number: number;
  status: PlanVersionStatus;
  scheduler_type?: SchedulerType;
  schedule_identity: string;
  is_approvable: boolean;
  validation_status?: string;
  result_summary?: Record<string, unknown>;
  created_at: string;
  created_by: string;
  reviewed_at?: string | null;
  reviewed_by?: string | null;
  approved_at?: string | null;
  approved_by?: string | null;
  approval_notes?: string | null;
  rejected_at?: string | null;
  rejected_by?: string | null;
  rejection_reason?: string | null;
  superseded_at?: string | null;
  superseded_by?: string | null;
  // Legacy helpers
  total_scheduled?: number;
  total_unscheduled?: number;
}

export interface AuditLogEntry {
  event_id: string;
  entity_type: string;
  entity_id: string;
  event_type: string;
  actor_id?: string;
  actor_username: string;
  actor_role: string;
  timestamp: string;
  previous_state?: string | null;
  new_state: string;
  reason?: string | null;
  comment?: string | null;
  schedule_identity?: string;
  snapshot_hash?: string;
  input_hash?: string;
  event_metadata?: Record<string, unknown>;
  // Legacy fields
  id?: string;
  action?: string;
  actor_name?: string;
  details?: string;
}
