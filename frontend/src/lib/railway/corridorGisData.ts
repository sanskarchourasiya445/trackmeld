/**
 * Northern Railway Trunk Corridor (New Delhi to Kanpur Central) GIS & Spatial Dataset
 * Provides geographic coordinates, station markers, track alignments, signal posts,
 * and OHE sub-stations for MapLibre GL JS and offline synthetic fallback rendering.
 */

export interface StationGisNode {
  code: string;
  name: string;
  distance_km: number;
  coordinates: [number, number]; // [lng, lat]
  track_count: number;
  elevation_m: number;
  division: string;
  facilities: string[];
}

export interface TrackSectionGis {
  section_id: string;
  code: string;
  name: string;
  from_station: string;
  to_station: string;
  length_km: number;
  speed_limit_kmh: number;
  electrified: boolean;
  track_count: number;
  coordinates: [number, number][]; // LineString
  up_line_status: 'CLEAR' | 'POSSESSION' | 'CAUTION' | 'OCCUPIED';
  dn_line_status: 'CLEAR' | 'POSSESSION' | 'CAUTION' | 'OCCUPIED';
}

export interface SignalGisNode {
  signal_id: string;
  code: string;
  type: 'AUTOMATIC_BLOCK' | 'HOME' | 'DISTANT' | 'STARTER';
  km: number;
  aspect: 'PROCEED' | 'CAUTION' | 'ATTENTION' | 'STOP';
  coordinates: [number, number];
  track: 'UP' | 'DOWN';
}

export interface OhePostGisNode {
  post_id: string;
  code: string;
  km: number;
  type: 'FEEDING_POST' | 'SUB_STATION' | 'NEUTRAL_SECTION' | 'SECTIONING_POST';
  voltage_kv: number;
  coordinates: [number, number];
  is_energized: boolean;
}

// Stations along NDLS - CNB trunk corridor (440 km)
export const CORRIDOR_STATIONS_GIS: StationGisNode[] = [
  {
    code: 'NDLS',
    name: 'New Delhi',
    distance_km: 0,
    coordinates: [77.2205, 28.6429],
    track_count: 16,
    elevation_m: 216,
    division: 'DLI',
    facilities: ['Route Relay Interlocking', 'Electric Loco Shed', 'Primary Yard', 'Crew Depot'],
  },
  {
    code: 'GZB',
    name: 'Ghaziabad Jn',
    distance_km: 26,
    coordinates: [77.4326, 28.6679],
    track_count: 6,
    elevation_m: 214,
    division: 'DLI',
    facilities: ['Electronic Interlocking', 'Electric Loco Trip Shed', 'Junction Cabin'],
  },
  {
    code: 'ALJN',
    name: 'Aligarh Jn',
    distance_km: 131,
    coordinates: [78.0847, 27.8974],
    track_count: 5,
    elevation_m: 187,
    division: 'PRYJ',
    facilities: ['Solid State Interlocking', 'Intermediate Block Post', 'Track Machine Base'],
  },
  {
    code: 'TDL',
    name: 'Tundla Jn',
    distance_km: 209,
    coordinates: [78.2435, 27.2084],
    track_count: 7,
    elevation_m: 168,
    division: 'PRYJ',
    facilities: ['Electronic Interlocking', 'Crew Changing Point', 'Freight Bypass Yard'],
  },
  {
    code: 'ETW',
    name: 'Etawah Jn',
    distance_km: 301,
    coordinates: [79.0277, 26.7766],
    track_count: 4,
    elevation_m: 151,
    division: 'PRYJ',
    facilities: ['Relay Interlocking', 'Tamping Machine Stabling', 'Traction Sub-Station'],
  },
  {
    code: 'CNB',
    name: 'Kanpur Central',
    distance_km: 440,
    coordinates: [80.3532, 26.4538],
    track_count: 10,
    elevation_m: 126,
    division: 'PRYJ',
    facilities: ['Electronic Interlocking', 'Electric Loco Shed', 'Major Terminal', 'Crew Base'],
  },
];

// Track Sections with interpolated waypoints between major hubs
export const CORRIDOR_SECTIONS_GIS: TrackSectionGis[] = [
  {
    section_id: 'SEC-NDLS-GZB',
    code: 'SEC-01',
    name: 'New Delhi – Ghaziabad Suburban Section',
    from_station: 'NDLS',
    to_station: 'GZB',
    length_km: 26,
    speed_limit_kmh: 110,
    electrified: true,
    track_count: 4, // Quadruple track suburban corridor
    coordinates: [
      [77.2205, 28.6429],
      [77.2750, 28.6510],
      [77.3400, 28.6590],
      [77.4326, 28.6679],
    ],
    up_line_status: 'CLEAR',
    dn_line_status: 'CLEAR',
  },
  {
    section_id: 'SEC-GZB-ALJN',
    code: 'SEC-04',
    name: 'Ghaziabad – Aligarh High Speed Section',
    from_station: 'GZB',
    to_station: 'ALJN',
    length_km: 105,
    speed_limit_kmh: 130,
    electrified: true,
    track_count: 2,
    coordinates: [
      [77.4326, 28.6679],
      [77.5800, 28.5100],
      [77.7200, 28.3200],
      [77.9100, 28.1100],
      [78.0847, 27.8974],
    ],
    up_line_status: 'CLEAR',
    dn_line_status: 'OCCUPIED',
  },
  {
    section_id: 'SEC-ALJN-TDL',
    code: 'SEC-08',
    name: 'Aligarh – Tundla Trunk Corridor',
    from_station: 'ALJN',
    to_station: 'TDL',
    length_km: 78,
    speed_limit_kmh: 130,
    electrified: true,
    track_count: 2,
    coordinates: [
      [78.0847, 27.8974],
      [78.1400, 27.6500],
      [78.1900, 27.4200],
      [78.2435, 27.2084],
    ],
    up_line_status: 'CAUTION',
    dn_line_status: 'CLEAR',
  },
  {
    section_id: 'SEC-TDL-ETW',
    code: 'SEC-12',
    name: 'Tundla – Etawah Mainline',
    from_station: 'TDL',
    to_station: 'ETW',
    length_km: 92,
    speed_limit_kmh: 130,
    electrified: true,
    track_count: 2,
    coordinates: [
      [78.2435, 27.2084],
      [78.4800, 27.0500],
      [78.7400, 26.9100],
      [79.0277, 26.7766],
    ],
    up_line_status: 'POSSESSION', // Active planned possession
    dn_line_status: 'CLEAR',
  },
  {
    section_id: 'SEC-ETW-CNB',
    code: 'SEC-15',
    name: 'Etawah – Kanpur Central High Capacity Section',
    from_station: 'ETW',
    to_station: 'CNB',
    length_km: 139,
    speed_limit_kmh: 130,
    electrified: true,
    track_count: 2,
    coordinates: [
      [79.0277, 26.7766],
      [79.3500, 26.6800],
      [79.7200, 26.5700],
      [80.0500, 26.4900],
      [80.3532, 26.4538],
    ],
    up_line_status: 'CAUTION',
    dn_line_status: 'CLEAR',
  },
];

// Operational Signalling Nodes
export const CORRIDOR_SIGNALS_GIS: SignalGisNode[] = [
  { signal_id: 'SIG-NDLS-01', code: 'S-NDLS-01', type: 'STARTER', km: 2.1, aspect: 'PROCEED', coordinates: [77.235, 28.645], track: 'UP' },
  { signal_id: 'SIG-GZB-04', code: 'S-GZB-04', type: 'AUTOMATIC_BLOCK', km: 24.8, aspect: 'PROCEED', coordinates: [77.418, 28.666], track: 'UP' },
  { signal_id: 'SIG-ALJN-12', code: 'S-ALJN-12', type: 'HOME', km: 129.5, aspect: 'ATTENTION', coordinates: [78.065, 27.910], track: 'UP' },
  { signal_id: 'SIG-TDL-09', code: 'S-TDL-09', type: 'AUTOMATIC_BLOCK', km: 206.2, aspect: 'CAUTION', coordinates: [78.225, 27.220], track: 'UP' },
  { signal_id: 'SIG-ETW-03', code: 'S-ETW-03', type: 'HOME', km: 298.4, aspect: 'STOP', coordinates: [78.995, 26.785], track: 'UP' }, // Protected possession
  { signal_id: 'SIG-CNB-01', code: 'S-CNB-01', type: 'DISTANT', km: 436.0, aspect: 'PROCEED', coordinates: [80.315, 26.460], track: 'UP' },
];

// OHE / Traction Sub-stations
export const CORRIDOR_OHE_POSTS_GIS: OhePostGisNode[] = [
  { post_id: 'OHE-TSS-01', code: 'TSS-ANVR', km: 12, type: 'SUB_STATION', voltage_kv: 25, coordinates: [77.310, 28.655], is_energized: true },
  { post_id: 'OHE-FP-02', code: 'FP-KRJ', km: 85, type: 'FEEDING_POST', voltage_kv: 25, coordinates: [77.820, 28.210], is_energized: true },
  { post_id: 'OHE-NS-03', code: 'NS-HRS', km: 165, type: 'NEUTRAL_SECTION', voltage_kv: 25, coordinates: [78.160, 27.520], is_energized: true },
  { post_id: 'OHE-TSS-04', code: 'TSS-ETW', km: 300, type: 'SUB_STATION', voltage_kv: 25, coordinates: [79.010, 26.780], is_energized: false }, // Isolated for task
  { post_id: 'OHE-SP-05', code: 'SP-RURA', km: 395, type: 'SECTIONING_POST', voltage_kv: 25, coordinates: [79.910, 26.510], is_energized: true },
];

// Active Train GPS Positions along Corridor
export interface ActiveTrainGis {
  train_id: string;
  train_number: string;
  name: string;
  current_km: number;
  speed_kmh: number;
  status: 'ON_TIME' | 'DELAYED_10M' | 'DELAYED_25M' | 'HELD_AT_SIGNAL';
  direction: 'UP' | 'DOWN';
  track: 'UP_MAIN' | 'DN_MAIN';
  coordinates: [number, number];
  next_station: string;
  destination: string;
  eta_next: string;
}

export const ACTIVE_TRAINS_GIS: ActiveTrainGis[] = [
  {
    train_id: 'TR-12004',
    train_number: '12004',
    name: 'Lucknow Swarna Shatabdi',
    current_km: 74,
    speed_kmh: 125,
    status: 'ON_TIME',
    direction: 'UP',
    track: 'UP_MAIN',
    coordinates: [77.6800, 28.3700],
    next_station: 'ALJN',
    destination: 'LKO (via CNB)',
    eta_next: '07:22 UTC',
  },
  {
    train_id: 'TR-22436',
    train_number: '22436',
    name: 'Vande Bharat Express',
    current_km: 185,
    speed_kmh: 130,
    status: 'ON_TIME',
    direction: 'UP',
    track: 'UP_MAIN',
    coordinates: [78.2100, 27.3100],
    next_station: 'TDL',
    destination: 'VNS (via CNB)',
    eta_next: '08:04 UTC',
  },
  {
    train_id: 'TR-12424',
    train_number: '12424',
    name: 'Dibrugarh Rajdhani Express',
    current_km: 278,
    speed_kmh: 90,
    status: 'DELAYED_10M',
    direction: 'UP',
    track: 'UP_MAIN',
    coordinates: [78.8900, 26.8300],
    next_station: 'ETW',
    destination: 'DBRG (via CNB)',
    eta_next: '09:12 UTC',
  },
  {
    train_id: 'TR-FRG-UP1',
    train_number: 'FRG-UP1',
    name: 'Container Freight Rake 401',
    current_km: 295,
    speed_kmh: 0,
    status: 'HELD_AT_SIGNAL',
    direction: 'UP',
    track: 'UP_MAIN',
    coordinates: [78.9800, 26.7900],
    next_station: 'ETW',
    destination: 'CNB Freight Yard',
    eta_next: 'Holding for TSK-0007 clearance',
  },
];
