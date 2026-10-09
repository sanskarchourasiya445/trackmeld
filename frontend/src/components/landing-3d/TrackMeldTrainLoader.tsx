'use client';

import React from 'react';
import { ProceduralTrainModel } from './ProceduralTrainModel';

interface TrackMeldTrainLoaderProps {
  speedKmh?: number;
  isPlaying?: boolean;
  onSelectTrain?: () => void;
  isSelected?: boolean;
  trackZ?: number;
}

/**
 * Authoritative High-Speed Passenger Train Renderer.
 * Directly renders the procedural train model to avoid unnecessary 404 network requests.
 */
export const TrackMeldTrainLoader: React.FC<TrackMeldTrainLoaderProps> = (props) => {
  return <ProceduralTrainModel {...props} />;
};
