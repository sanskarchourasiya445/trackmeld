/**
 * Unified API Client for TrackMeld Backend
 * Connects to FastAPI backend with explicit configuration-driven authentication.
 * Never embeds administrative secrets in public client bundles.
 */

import { Corridor, Scenario, MaintenanceTask, TrainMovement, BlockSection, Track } from '@/types/railway';

import {
  PlanningRun,
  PlanVersion,
  ScheduleResult,
  ScheduleValidationResult,
  DiagnosticsReport,
  BenchmarkComparisonResult,
  AuditLogEntry,
} from '@/types/planning';

/**
 * Structured API Error conforming to TrackMeld enterprise governance requirements.
 */
export class ApiError extends Error {
  public status: number | null;
  public code: string;
  public requestId?: string;

  constructor(message: string, status: number | null = null, code: string = 'API_ERROR', requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

/**
 * Retrieve authenticated operator token from browser session/local storage.
 * Default is null; does NOT ship or bake an admin token secret in the bundle.
 */
export function getAuthToken(): string | null {
  if (typeof window !== 'undefined') {
    return (
      sessionStorage.getItem('trackmeld_auth_token') ||
      localStorage.getItem('trackmeld_auth_token') ||
      null
    );
  }
  return null;
}

/**
 * Configure operator token for formal governance and review actions.
 */
export function setAuthToken(token: string | null): void {
  if (typeof window !== 'undefined') {
    if (token) {
      sessionStorage.setItem('trackmeld_auth_token', token);
    } else {
      sessionStorage.removeItem('trackmeld_auth_token');
      localStorage.removeItem('trackmeld_auth_token');
    }
  }
}

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options?.headers as Record<string, string>) || {}),
  };

  let res: Response;
  try {
    res = await fetch(url, {
      ...options,
      headers,
    });
  } catch {
    throw new ApiError(
      `Network connection failed when reaching backend at ${endpoint}. Please ensure the TrackMeld backend service is running.`,
      null,
      'NETWORK_UNAVAILABLE'
    );
  }

  const requestId = res.headers.get('X-Request-ID') || undefined;

  if (!res.ok) {
    let errCode = `HTTP_${res.status}`;
    let errMsg = `API request to ${endpoint} failed with status ${res.status}`;

    try {
      const errBody = await res.json();
      if (errBody?.error?.message) {
        errMsg = errBody.error.message;
        errCode = errBody.error.code || errCode;
      } else if (errBody?.detail) {
        if (typeof errBody.detail === 'string') {
          errMsg = errBody.detail;
        } else if (errBody.detail?.error?.message) {
          errMsg = errBody.detail.error.message;
          errCode = errBody.detail.error.code || errCode;
        }
      }
    } catch {
      // Body not JSON
    }

    if (res.status === 401) {
      errCode = 'UNAUTHORIZED';
    } else if (res.status === 403) {
      errCode = 'FORBIDDEN';
    } else if (res.status === 404) {
      errCode = 'NOT_FOUND';
    } else if (res.status === 422) {
      errCode = 'VALIDATION_ERROR';
    }

    throw new ApiError(errMsg, res.status, errCode, requestId);
  }

  return await res.json();
}

// ==========================================
// SEEDED SYNTHETIC DEMONSTRATION DATA FALLBACK
// ==========================================

export const DEMO_CORRIDOR: Corridor = {
  id: 'CORR-NDLS-HWH',
  code: 'NDLS-HWH',
  name: 'Northern Corridor (New Delhi – Howrah Main Line)',
  zone: 'NORTHERN_RAILWAY',
  division: 'DLI',
  total_length_km: 440,
  stations: [
    { code: 'NDLS', name: 'New Delhi', distance_km: 0, track_count: 16 },
    { code: 'GZB', name: 'Ghaziabad Jn', distance_km: 26, track_count: 6 },
    { code: 'ALJN', name: 'Aligarh Jn', distance_km: 131, track_count: 5 },
    { code: 'TDL', name: 'Tundla Jn', distance_km: 209, track_count: 7 },
    { code: 'ETW', name: 'Etawah Jn', distance_km: 301, track_count: 4 },
    { code: 'CNB', name: 'Kanpur Central', distance_km: 440, track_count: 10 },
  ],
  sections: [
    { code: 'SEC-NDLS-GZB', section_id: 'SEC-NDLS-GZB', from_station_code: 'NDLS', to_station_code: 'GZB', track_type: 'UP', length_km: 26, speed_limit_kmh: 130, electrified: true },
    { code: 'SEC-GZB-ALJN', section_id: 'SEC-GZB-ALJN', from_station_code: 'GZB', to_station_code: 'ALJN', track_type: 'UP', length_km: 105, speed_limit_kmh: 130, electrified: true },
    { code: 'SEC-ALJN-TDL', section_id: 'SEC-ALJN-TDL', from_station_code: 'ALJN', to_station_code: 'TDL', track_type: 'UP', length_km: 78, speed_limit_kmh: 130, electrified: true },
    { code: 'SEC-TDL-ETW', section_id: 'SEC-TDL-ETW', from_station_code: 'TDL', to_station_code: 'ETW', track_type: 'UP', length_km: 92, speed_limit_kmh: 130, electrified: true },
    { code: 'SEC-ETW-CNB', section_id: 'SEC-ETW-CNB', from_station_code: 'ETW', to_station_code: 'CNB', track_type: 'UP', length_km: 139, speed_limit_kmh: 130, electrified: true },
  ],
};

export const DEMO_SCENARIO: Scenario = {
  id: 'SCN-DEMO-001',
  scenario_id: 'SCN-DEMO-001',
  name: 'Northern Corridor 24h Maintenance Window Demo',
  corridor_id: 'CORR-NDLS-HWH',
  planning_start: '2026-10-10T00:00:00Z',
  planning_end: '2026-10-12T23:59:59Z',
  description: 'Synthetic baseline corridor with 50 passenger/freight train movements and 30 maintenance requisitions.',
  dataset_version: 'v2026.10-synthetic-demo',
  is_synthetic: true,
  total_tasks: 30,
  total_trains: 50,
};

export const DEMO_TRAINS: TrainMovement[] = [
  { train_id: 'TR-12004', train_number: '12004', train_name: 'Lucknow Swarna Shatabdi', direction: 'UP', priority_tier: 1, entry_station: 'NDLS', exit_station: 'CNB', entry_time: '2026-10-10T06:10:00Z', exit_time: '2026-10-10T11:20:00Z' },
  { train_id: 'TR-12424', train_number: '12424', train_name: 'Dibrugarh Rajdhani Exp', direction: 'UP', priority_tier: 1, entry_station: 'NDLS', exit_station: 'CNB', entry_time: '2026-10-10T16:10:00Z', exit_time: '2026-10-10T21:05:00Z' },
  { train_id: 'TR-22436', train_number: '22436', train_name: 'Vande Bharat Express (VNS)', direction: 'UP', priority_tier: 1, entry_station: 'NDLS', exit_station: 'CNB', entry_time: '2026-10-10T06:00:00Z', exit_time: '2026-10-10T10:08:00Z' },
  { train_id: 'TR-12302', train_number: '12302', train_name: 'Howrah Rajdhani Exp', direction: 'UP', priority_tier: 1, entry_station: 'NDLS', exit_station: 'CNB', entry_time: '2026-10-10T16:50:00Z', exit_time: '2026-10-10T21:35:00Z' },
  { train_id: 'TR-12554', train_number: '12554', train_name: 'Vaishali Superfast Exp', direction: 'UP', priority_tier: 2, entry_station: 'NDLS', exit_station: 'CNB', entry_time: '2026-10-10T20:40:00Z', exit_time: '2026-10-11T02:30:00Z' },
  { train_id: 'TR-FRG-UP1', train_number: 'FRG-UP1', train_name: 'Container Freight Rake 401', direction: 'UP', priority_tier: 4, entry_station: 'NDLS', exit_station: 'CNB', entry_time: '2026-10-10T01:30:00Z', exit_time: '2026-10-10T08:15:00Z' },
];

export const DEMO_TASKS: MaintenanceTask[] = [
  {
    task_id: 'TSK-0001',
    task_code: 'TSK-TRK-001',
    title: 'Plain Track CSM Tamping - Up Main Line',
    work_type: 'TRACK_MACHINE_WORK',
    department: 'ENGINEERING',
    section_code: 'SEC-ETW-CNB',
    section_id: 'SEC-ETW-CNB',
    required_duration_minutes: 180,
    estimated_duration_minutes: 180,
    earliest_start: '2026-10-10T07:00:00Z',
    latest_finish: '2026-10-10T12:00:00Z',
    window_start: '2026-10-10T07:00:00Z',
    window_end: '2026-10-10T12:00:00Z',
    urgency: 'HIGH',
    priority: 'CRITICAL',
    mandatory: true,
    requires_traffic_block: true,
    track_type: 'UP',
  },
  {
    task_id: 'TSK-0007',
    task_code: 'TSK-TRK-007',
    title: 'Switch Expansion Joint Greasing & Tightening',
    work_type: 'ROUTINE_TRACK_MAINTENANCE',
    department: 'ENGINEERING',
    section_code: 'SEC-ALJN-TDL',
    section_id: 'SEC-ALJN-TDL',
    required_duration_minutes: 120,
    estimated_duration_minutes: 120,
    earliest_start: '2026-10-11T06:00:00Z',
    latest_finish: '2026-10-11T10:00:00Z',
    window_start: '2026-10-11T06:00:00Z',
    window_end: '2026-10-11T10:00:00Z',
    urgency: 'ROUTINE',
    priority: 'ROUTINE',
    mandatory: false,
    requires_traffic_block: true,
    track_type: 'UP',
  },
];

export const DEMO_SCHEDULE_RESULT: ScheduleResult = {
  scenario_id: 'SCN-DEMO-001',
  scheduler_type: 'CP_SAT',
  status: 'OPTIMAL',
  solver_wall_time_seconds: 1.48,
  objective_value: 3001.06,
  best_bound: 3001.06,
  scheduled_tasks: [
    {
      task_id: 'TSK-0001',
      task_code: 'TSK-TRK-001',
      interval: { start: '2026-10-10T07:00:00Z', end: '2026-10-10T10:00:00Z' },
      possession_interval: { start: '2026-10-10T06:45:00Z', end: '2026-10-10T10:15:00Z' },
      duration_minutes: 180,
      affected_sections: ['SEC-ETW-CNB'],
      section_code: 'SEC-ETW-CNB',
      assigned_resources: ['RES-TM-CSM-01', 'RES-CREW-ENG-G01'],
      priority_score: 159.5,
      scheduling_reason: 'OPTIMAL',
    },
  ],
  unscheduled_tasks: [
    {
      task_id: 'TSK-0007',
      task_code: 'TSK-TRK-007',
      mandatory: false,
      priority_score: 44.17,
      reason_codes: ['SOLVER_DID_NOT_RETURN_PLACEMENT'],
      diagnostic_message: 'Task unplaced: excluded by global optimization objective or track contention.',
    },
  ],
  metrics: {
    total_tasks: 30,
    scheduled_tasks: 29,
    unscheduled_tasks: 1,
    completion_rate: 0.967,
    mandatory_tasks: 17,
    mandatory_scheduled: 17,
    mandatory_unscheduled: 0,
    mandatory_completion_rate: 1.0,
    total_scheduled_duration_minutes: 3615,
    total_possession_duration_minutes: 4485,
    priority_score_capture_rate: 0.986,
    total_requested_tasks: 30,
    completion_rate_pct: 96.7,
  },
};

export const DEMO_VALIDATION_RESULT: ScheduleValidationResult = {
  status: 'VALID',
  valid: true,
  is_approvable: true,
  findings: [],
  error_count: 0,
  warning_count: 0,
  info_count: 0,
  checked_task_count: 29,
  checked_section_count: 32,
  checked_resource_count: 21,
  checked_train_movement_count: 50,
  validator_version: '1.0.0',
  input_snapshot_id: 'SNAP-297E475AC983',
  schedule_identity: 'bae346ecf37b1fd80608cc5e0b8dae030517a44d5d5305f640d5767ed46999aa',
  validation_runtime_ms: 18.4,
  checks_executed: [
    'STRUCTURAL',
    'HORIZON',
    'TASK_WINDOW',
    'DURATION_AND_BUFFERS',
    'SECTION_OCCUPANCY',
    'MULTI_SECTION',
    'TRAIN_MOVEMENT',
    'RESOURCES',
    'DEPENDENCIES',
    'MANDATORY_TASKS',
    'DOMAIN_RULES',
    'SOLVER_OUTPUT',
  ],
  approval_gate_message: 'Approval ELIGIBLE: Schedule independently certified 100% valid under all modeled hard constraints.',
};

export const DEMO_DIAGNOSTICS: DiagnosticsReport = {
  scenario_id: 'SCN-DEMO-001',
  snapshot_id: 'SNAP-297E475AC983',
  total_unscheduled_tasks: 1,
  diagnostics: [
    {
      task_id: 'TSK-0007',
      task_code: 'TSK-TRK-007',
      mandatory: false,
      priority_score: 44.17,
      status: 'DIAGNOSED',
      primary_reason: 'Excluded by global solver objective or resource competition.',
      reason_codes: ['SOLVER_DID_NOT_RETURN_PLACEMENT'],
      affected_sections: ['SEC-ALJN-TDL'],
      conflicting_tasks: [],
      conflicting_train_movements: [],
      conflicting_resources: [],
      relaxation_analyses: [
        {
          scenario_type: 'IGNORE_RESOURCE_AVAILABILITY',
          description: 'Hypothetically waive resource availability restrictions.',
          feasible: true,
          blocking_entities: ['RES-CREW-ENG-G03'],
          relaxation_magnitude: 'Waives required resources: RES-CREW-ENG-G03',
          hypothetical: true,
          approvable: false,
          explanation: 'Assuming external contract machine or additional gang is mobilized for RES-CREW-ENG-G03, task could proceed.',
        },
        {
          scenario_type: 'IGNORE_DEPENDENCIES',
          description: 'Hypothetically waive predecessor dependencies.',
          feasible: true,
          blocking_entities: ['TSK-0006'],
          relaxation_magnitude: 'Unlinks precedence from predecessors: TSK-0006',
          hypothetical: true,
          approvable: false,
          explanation: 'Waiving finish-to-start precedence from TSK-0006 allows parallel execution.',
        },
        {
          scenario_type: 'WIDEN_TASK_WINDOW',
          description: 'Hypothetically widen allowed task window by up to +/- 4 hours.',
          feasible: true,
          candidate_start: '2026-10-11T09:00:00Z',
          candidate_end: '2026-10-11T11:00:00Z',
          relaxation_magnitude: 'Allowed window expanded by +/- 4 hours',
          hypothetical: true,
          approvable: false,
          explanation: 'Feasible open possession slot found at 2026-10-11T09:00:00Z if department permits widening execution window.',
        },
      ],
    },
  ],
  execution_time_ms: 1.17,
};

export const DEMO_PLAN_VERSION: PlanVersion = {
  plan_version_id: 'PV-20261002-5F8A180A',
  version_number: 1,
  planning_run_id: 'RUN-20261002-FAAAEF76',
  scenario_id: 'SCN-DEMO-001',
  status: 'PENDING_REVIEW',
  scheduler_type: 'CP_SAT',
  schedule_identity: 'bae346ecf37b1fd80608cc5e0b8dae030517a44d5d5305f640d5767ed46999aa',
  is_approvable: true,
  validation_status: 'VALID',
  created_at: '2026-10-02T18:56:37.403807Z',
  created_by: 'chief_operations_admin',
  total_scheduled: 29,
  total_unscheduled: 1,
};

export const DEMO_AUDIT_LOGS: AuditLogEntry[] = [
  {
    event_id: 'AUD-20261002-430F1982',
    entity_type: 'PLAN_VERSION',
    entity_id: 'PV-20261002-5F8A180A',
    event_type: 'PLAN_VERSION_CREATED',
    actor_id: 'USR-ADMIN-01',
    actor_username: 'chief_operations_admin',
    actor_role: 'ADMIN',
    timestamp: '2026-10-02T18:56:37.403807Z',
    previous_state: null,
    new_state: 'PENDING_REVIEW',
    comment: 'Instantiated PlanVersion 1 from certified run RUN-20261002-FAAAEF76.',
    schedule_identity: 'bae346ecf37b1fd80608cc5e0b8dae030517a44d5d5305f640d5767ed46999aa',
  },
];

// ==========================================
// EXPORTED API METHODS
// ==========================================

export async function getScenarios(): Promise<Scenario[]> {
  return await fetchJson<Scenario[]>('/scenarios');
}

export async function getScenarioBundle(scenarioId: string): Promise<{
  scenario: Scenario;
  corridor: Corridor;
  sections: BlockSection[];
  trains: TrainMovement[];
  tasks: MaintenanceTask[];
  tracks: Track[];
}> {
  const raw = await fetchJson<{
    scenario: Scenario;
    corridor?: Corridor;
    sections?: BlockSection[];
    train_movements?: TrainMovement[];
    tasks?: MaintenanceTask[];
    tracks?: Track[];
  }>(`/scenarios/${scenarioId}/bundle`);

  const sections = raw.sections ?? [];
  const trains = raw.train_movements ?? [];
  const tracks = raw.tracks ?? [];
  const tasks = (raw.tasks ?? []).map((t) => ({
    ...t,
    section_code: t.section_id || t.section_code || '',
    required_duration_minutes: t.estimated_duration_minutes ?? t.required_duration_minutes ?? 0,
    earliest_start: t.window_start || t.earliest_start || '',
    latest_finish: t.window_end || t.latest_finish || '',
    work_type: t.task_type || t.work_type || 'MAINTENANCE',
  }));

  const corridor: Corridor = raw.corridor || {
    id: raw.scenario?.corridor_id || 'CORRIDOR',
    code: raw.scenario?.corridor_id || 'CORR',
    name: raw.scenario?.name || 'Corridor',
    zone: 'NORTHERN_RAILWAY',
    division: 'DLI',
    total_length_km: 0,
    stations: [],
    sections,
  };

  return {
    scenario: raw.scenario,
    corridor,
    sections,
    trains,
    tasks,
    tracks,
  };
}

export async function getTracks(sectionId?: string): Promise<Track[]> {
  const query = sectionId ? `?section_id=${encodeURIComponent(sectionId)}` : '';
  return await fetchJson<Track[]>(`/tracks${query}`);
}

export async function getTrack(trackId: string): Promise<Track> {
  return await fetchJson<Track>(`/tracks/${encodeURIComponent(trackId)}`);
}


export async function optimizeSchedule(
  scenarioId: string,
  timeLimitSeconds: number = 5.0
): Promise<ScheduleResult> {
  return await fetchJson<ScheduleResult>('/planning/optimize', {
    method: 'POST',
    body: JSON.stringify({
      scenario_id: scenarioId,
      time_limit_seconds: timeLimitSeconds,
    }),
  });
}

export async function validateSchedule(
  scenarioId: string,
  schedule: ScheduleResult
): Promise<ScheduleValidationResult> {
  return await fetchJson<ScheduleValidationResult>('/planning/validate', {
    method: 'POST',
    body: JSON.stringify({
      scenario_id: scenarioId,
      schedule,
    }),
  });
}

export async function diagnoseSchedule(
  scenarioId: string,
  schedule: ScheduleResult
): Promise<DiagnosticsReport> {
  return await fetchJson<DiagnosticsReport>('/planning/diagnostics', {
    method: 'POST',
    body: JSON.stringify({
      scenario_id: scenarioId,
      schedule,
    }),
  });
}

export async function benchmarkSchedule(
  scenarioId: string,
  includeCpsat: boolean = true,
  cpsatTimeLimit: number = 5.0
): Promise<BenchmarkComparisonResult> {
  return await fetchJson<BenchmarkComparisonResult>('/planning/benchmark', {
    method: 'POST',
    body: JSON.stringify({
      scenario_id: scenarioId,
      include_cpsat: includeCpsat,
      cpsat_time_limit: cpsatTimeLimit,
    }),
  });
}

export async function createPlanningRun(payload: {
  scenario_id: string;
  scheduler_type?: string;
  time_limit_seconds?: number;
  random_seed?: number;
  validate_after_solve?: boolean;
}): Promise<PlanningRun> {
  return await fetchJson<PlanningRun>('/planning-runs', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getPlanningRuns(): Promise<PlanningRun[]> {
  return await fetchJson<PlanningRun[]>('/planning-runs');
}

export async function getPlanningRun(runId: string): Promise<PlanningRun> {
  return await fetchJson<PlanningRun>(`/planning-runs/${runId}`);
}

export async function getPlanningRunResult(runId: string): Promise<ScheduleResult> {
  return await fetchJson<ScheduleResult>(`/planning-runs/${runId}/result`);
}

export async function createPlanVersionFromRun(
  runId: string,
  comment?: string
): Promise<PlanVersion> {
  return await fetchJson<PlanVersion>(`/planning-runs/${runId}/plan-version`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
  });
}

export async function getPlanVersions(scenarioId?: string): Promise<PlanVersion[]> {
  const query = scenarioId ? `?scenario_id=${scenarioId}` : '';
  return await fetchJson<PlanVersion[]>(`/plan-versions${query}`);
}

export async function getPlanVersion(planVersionId: string): Promise<PlanVersion> {
  return await fetchJson<PlanVersion>(`/plan-versions/${planVersionId}`);
}

export async function approvePlanVersion(
  planVersionId: string,
  comment?: string,
  declaredReviewerName?: string,
  declaredReviewerRole?: string
): Promise<PlanVersion> {
  return await fetchJson<PlanVersion>(`/plan-versions/${planVersionId}/approve`, {
    method: 'POST',
    body: JSON.stringify({
      comment,
      declared_reviewer_name: declaredReviewerName,
      declared_reviewer_role: declaredReviewerRole,
    }),
  });
}

export async function rejectPlanVersion(
  planVersionId: string,
  reason: string
): Promise<PlanVersion> {
  return await fetchJson<PlanVersion>(`/plan-versions/${planVersionId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function getPlanVersionAudit(planVersionId: string): Promise<AuditLogEntry[]> {
  return await fetchJson<AuditLogEntry[]>(`/plan-versions/${planVersionId}/audit`);
}

// ==========================================
// COPILOT & DECISION SUPPORT APIS
// ==========================================

export interface CopilotEvidenceItem {
  evidence_id: string;
  evidence_type: string;
  title: string;
  data: Record<string, unknown>;
  source_reference?: string;
}

export interface CopilotQueryRequest {
  prompt: string;
  scenario_id?: string;
  run_id?: string;
  task_id?: string;
  plan_version_id?: string;
}

export interface CopilotQueryResponse {
  query: string;
  answer: string;
  evidence: CopilotEvidenceItem[];
  tool_calls_executed: string[];
  provider_used: string;
  read_only_notice: string;
  timestamp: string;
}

export async function askCopilot(req: CopilotQueryRequest): Promise<CopilotQueryResponse> {
  return await fetchJson<CopilotQueryResponse>('/copilot/explain', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

