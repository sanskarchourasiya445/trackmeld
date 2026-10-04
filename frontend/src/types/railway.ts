/**
 * Railway Infrastructure & Operations domain types matching TrackMeld backend schemas.
 */

export interface Station {
  id?: string;
  station_id?: string;
  station_code?: string;
  code: string;
  name: string;
  distance_km: number;
  track_count?: number;
  zone?: string;
  division?: string;
}

export interface Track {
  track_id: string;
  section_id: string;
  track_code: string;
  direction: 'UP' | 'DOWN' | 'BIDIRECTIONAL' | string;
  electrified: boolean;
  max_speed_kmh?: number;
  adjacent_track_ids?: string[] | null;
}

export interface BlockSection {
  id?: string;
  section_id?: string;
  section_code?: string;
  code?: string;
  name?: string;
  from_station_id?: string;
  to_station_id?: string;
  from_station_code?: string;
  to_station_code?: string;
  from_station_name?: string;
  to_station_name?: string;
  track_type?: 'UP' | 'DOWN' | 'SINGLE' | string;
  track_count?: number;
  tracks?: Track[];
  length_km: number;
  speed_limit_kmh?: number;
  electrified?: boolean;
  division?: string;
  zone?: string;
  classification?: string;
}


export interface Corridor {
  id: string;
  code: string;
  name: string;
  zone: string;
  division: string;
  total_length_km: number;
  stations: Station[];
  sections: BlockSection[];
}

export interface TrainMovement {
  id?: string;
  movement_id?: string;
  train_id: string;
  train_number: string;
  train_name: string;
  direction?: 'UP' | 'DOWN' | string;
  track_id?: string;
  priority_tier?: number; // 1 (Highest/Vande Bharat/Rajdhani) to 5 (Freight)
  entry_station?: string;
  exit_station?: string;
  station_id?: string;
  station_code?: string;
  stop_sequence?: number;
  distance_km?: number;
  scheduled_arrival?: string;
  scheduled_departure?: string;
  day_offset?: number;
  entry_time?: string; // ISO-8601
  exit_time?: string;
  classification?: string;
  intermediate_stops?: {
    station_code: string;
    arrival: string;
    departure: string;
  }[];
}

export type TraversalResolutionStatus = 'DIRECT_SECTION' | 'EXPANDED_ROUTE' | 'UNRESOLVED' | 'AMBIGUOUS_ROUTE';

export interface TrainTraversal {
  traversal_id: string;
  train_id: string;
  train_number: string;
  source_pass_id: string;
  section_id?: string | null;
  from_station_id: string;
  to_station_id: string;
  sequence_order: number;
  entry_time: string;
  exit_time: string;
  duration_minutes: number;
  traversal_track_id?: string | null;
  resolution_status: TraversalResolutionStatus;
  unresolved_reason?: string | null;
  classification?: string;
}

export interface TaskResourceRequirement {
  requirement_id?: string;
  resource_type: string;
  resource_id: string;
  quantity?: number;
  mandatory?: boolean;
}

export interface MaintenanceTask {
  task_id: string;
  work_order_id?: string;
  task_code?: string;
  title: string;
  description?: string;
  work_type?: string;
  task_type?: string;
  department?: string;
  section_id?: string;
  track_id?: string;
  from_km?: number;
  to_km?: number;
  adjacent_track_impact?: 'NONE' | 'CAUTION_ORDER' | 'FULL_TRAFFIC_BLOCK';
  section_code?: string;

  station_id?: string;
  corridor_id?: string;
  status?: string;
  priority?: string;
  urgency?: 'EMERGENCY' | 'CRITICAL' | 'HIGH' | 'ROUTINE' | string;
  mandatory?: boolean;
  required_duration_minutes?: number;
  estimated_duration_minutes?: number;
  earliest_start?: string; // ISO-8601
  latest_finish?: string;
  window_start?: string;
  window_end?: string;
  crew_id?: string;
  crew_size_required?: number;
  machinery_required?: string[];
  resource_requirements?: TaskResourceRequirement[];
  track_type?: 'UP' | 'DOWN' | 'BOTH' | string;
  isolated_section_required?: boolean;
  requires_traffic_block?: boolean;
  requires_power_block?: boolean;
  requires_ptw?: boolean;
  requires_ohe_isolation?: boolean;
  safety_buffer_before_minutes?: number;
  safety_buffer_after_minutes?: number;
  speed_restriction_kmh?: number;
  classification?: string;
}

export interface Scenario {
  id?: string;
  scenario_id: string;
  scenario_code?: string;
  name: string;
  corridor_id?: string;
  planning_start: string;
  planning_end: string;
  description?: string;
  dataset_version?: string;
  is_synthetic?: boolean;
  total_tasks?: number;
  total_trains?: number;
}

export interface ScenarioPlanningBundle {
  scenario: Scenario;
  work_orders?: Record<string, unknown>[];
  tasks: MaintenanceTask[];
  dependencies?: Record<string, unknown>[];
  resources?: Record<string, unknown>[];
  resource_availabilities?: Record<string, unknown>[];
  sections: BlockSection[];
  train_movements: TrainMovement[];
  applicable_rules?: Record<string, unknown>[];
  tracks?: Track[];
  train_traversals?: TrainTraversal[];
}

/**
 * Truthful spatial display for maintenance tasks:
 * - track assigned + range: "UP_MAIN · 12.4–15.8 km"
 * - track assigned + no range: "UP_MAIN"
 * - no track: "Whole section"
 */
export function formatTrackSpatial(task?: MaintenanceTask | null): string {
  if (!task || !task.track_id) {
    return 'Whole section';
  }
  let trackName = task.track_id;
  if (trackName.endsWith('-UP')) trackName = 'UP_MAIN';
  else if (trackName.endsWith('-DN')) trackName = 'DN_MAIN';
  else if (trackName.endsWith('-SL')) trackName = 'SINGLE_LINE';

  if (task.from_km !== undefined && task.from_km !== null && task.to_km !== undefined && task.to_km !== null) {
    return `${trackName} · ${task.from_km}–${task.to_km} km`;
  }
  return trackName;
}
