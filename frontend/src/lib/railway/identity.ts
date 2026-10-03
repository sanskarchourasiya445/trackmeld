import { TrainMovement } from '@/types/railway';

/**
 * Compute a semantically correct, stable React key for a train movement occurrence.
 * 
 * In railway domain modeling:
 * - A train service (e.g. `TRN-12002` Shatabdi Express) represents a scheduled service.
 * - A train movement (e.g. `MOV-12002-NDLS-01`) represents a specific timetable transit or stop event
 *   along the corridor at a given station, sequence, and time window.
 * 
 * When rendering train trajectories on a Time-Space diagram or spatial canvas, multiple movement
 * occurrences of the same train service legitimately share `train_id`.
 * 
 * To ensure deterministic, collision-free React rendering without mutating or deduplicating valid
 * domain records, this function resolves a stable unique key following the domain hierarchy:
 * 1. movement/occurrence primary ID: `train.movement_id` (or `train.id` if distinct from `train_id`)
 * 2. timetable-event ID: `${train.train_id}:${station}:${sequence}`
 * 3. stable composite identity: `${train.train_id}:${direction}:${entry_time || departure_time}`
 * 4. deterministic fallback: `${train.train_id}:occ-${index}`
 */
export function getTrainOccurrenceKey(train: TrainMovement, index?: number): string {
  // 1. Primary occurrence / movement ID
  if (train.movement_id && train.movement_id.trim()) {
    return train.movement_id;
  }
  if (train.id && train.id.trim() && train.id !== train.train_id) {
    return train.id;
  }

  // 2. Timetable-event ID (composite of service + station + stop sequence)
  const stationPart = train.station_code || train.station_id || train.entry_station;
  const seqPart = train.stop_sequence !== undefined ? `seq-${train.stop_sequence}` : null;
  if (stationPart && seqPart) {
    return `${train.train_id}:${stationPart}:${seqPart}`;
  }
  if (stationPart) {
    return `${train.train_id}:${stationPart}`;
  }

  // 3. Stable temporal/directional composite identity
  const timePart = train.entry_time || train.scheduled_departure || train.scheduled_arrival;
  if (timePart) {
    const dirPart = train.direction ? `:${train.direction}` : '';
    return `${train.train_id}${dirPart}:${timePart}`;
  }

  // 4. Deterministic occurrence index fallback (stable within immutable list rendering)
  if (index !== undefined) {
    return `${train.train_id}:occ-${index}`;
  }

  return train.train_id;
}
