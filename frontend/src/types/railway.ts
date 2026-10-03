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
}
