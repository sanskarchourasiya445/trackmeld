'use client';

import React, { createContext, useContext, useRef, useEffect } from 'react';

export interface SimulationClock {
  trainX: number;
  speedMs: number;
  targetSpeedMs: number;
  distance: number;
  wheelRotation: number;
  isPlaying: boolean;
}

interface SimulationContextValue {
  clockRef: React.MutableRefObject<SimulationClock>;
}

const SimulationContext = createContext<SimulationContextValue | null>(null);

interface SimulationProviderProps {
  children: React.ReactNode;
  speedKmh: number;
  isPlaying: boolean;
  initialX?: number;
}

export const SimulationProvider: React.FC<SimulationProviderProps> = ({
  children,
  speedKmh,
  isPlaying,
  initialX = 0,
}) => {
  const clockRef = useRef<SimulationClock>({
    trainX: initialX,
    speedMs: speedKmh / 3.6, // Exact physical velocity in m/s (130 km/h = 36.11 m/s)
    targetSpeedMs: speedKmh / 3.6,
    distance: initialX,
    wheelRotation: 0,
    isPlaying: isPlaying,
  });

  // Keep target velocity and play/pause synchronized with UI controls
  useEffect(() => {
    clockRef.current.targetSpeedMs = speedKmh / 3.6;
  }, [speedKmh]);

  useEffect(() => {
    clockRef.current.isPlaying = isPlaying;
  }, [isPlaying]);

  if (typeof window !== 'undefined') {
    (window as any).__trackmeld_sim_clock = clockRef.current;
  }

  return (
    <SimulationContext.Provider value={{ clockRef }}>
      {children}
    </SimulationContext.Provider>
  );
};

export const useSimulationClock = (): React.MutableRefObject<SimulationClock> => {
  const ctx = useContext(SimulationContext);
  const fallbackRef = useRef<SimulationClock>({
    trainX: 0,
    speedMs: 15,
    targetSpeedMs: 15,
    distance: 0,
    wheelRotation: 0,
    isPlaying: true,
  });

  // Ensure singleton synchronization across Three.js fiber tree and components
  if (typeof window !== 'undefined' && (window as any).__trackmeld_sim_clock) {
    fallbackRef.current = (window as any).__trackmeld_sim_clock;
    return fallbackRef;
  }

  return ctx ? ctx.clockRef : fallbackRef;
};
