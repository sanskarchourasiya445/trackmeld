export type CameraMode = 'cinematic' | 'cab' | 'drone' | 'orbit';

export type LightingPreset = 'dawn' | 'night' | 'overcast';

export interface TelemetryMarker {
  id: string;
  title: string;
  subtitle: string;
  tag: string;
  tagColor: 'blue' | 'emerald' | 'amber' | 'rose' | 'cyan';
  position: [number, number, number];
  entityType: 'train' | 'possession' | 'conflict' | 'catenary' | 'signal';
  details: {
    label: string;
    value: string;
  }[];
}

export interface SimulationState {
  trainSpeedKmh: number;
  isPlaying: boolean;
  activeCamera: CameraMode;
  lighting: LightingPreset;
  showTelemetry: boolean;
  selectedMarkerId: string | null;
  selectedEntity: string | null;
}
