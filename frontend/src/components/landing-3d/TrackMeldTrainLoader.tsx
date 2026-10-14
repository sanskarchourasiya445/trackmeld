'use client';

import React from 'react';
import { VandeBharatTrainModel } from './VandeBharatTrainModel';

interface TrackMeldTrainLoaderProps {
  wheelRotation?: number;
  speedKmh?: number;
  isPlaying?: boolean;
  onSelectTrain?: () => void;
  isSelected?: boolean;
  trackZ?: number;
  showTelemetry?: boolean;
  lighting?: 'dawn' | 'night' | 'overcast';
}

/**
 * Authoritative Broad-Gauge Streamlined Passenger Trainset Renderer.
 * Directly renders the authentic Vande Bharat Express (Orange & Silver livery) matching reference image.
 */
export const TrackMeldTrainLoader: React.FC<TrackMeldTrainLoaderProps> = ({
  wheelRotation = 0,
  isSelected = false,
  showTelemetry = true,
  lighting = 'dawn',
  trackZ = -2.0,
  onSelectTrain,
}) => {
  return (
    <VandeBharatTrainModel
      wheelRotation={wheelRotation}
      isSelected={isSelected}
      showTelemetry={showTelemetry}
      lighting={lighting}
      trackZ={trackZ}
      onSelectTrain={onSelectTrain}
    />
  );
};
