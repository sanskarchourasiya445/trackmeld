'use client';

import React, { createContext, useContext, useState, useMemo } from 'react';

export interface WorkspaceTelemetry {
  activeScenarioId: string;
  scenarioName: string;
  planningHorizon: string;
  tasksCount: number | null;
  totalTasks: number | null;
  trainsCount: number | null;
  lastSolveDuration: number | null;
  workerStatus: string;
  validatorStatus: string;
  dbStatus: string;
}

const DEFAULT_TELEMETRY: WorkspaceTelemetry = {
  activeScenarioId: 'SCN-DEMO-001',
  scenarioName: 'Northern Trunk Corridor (NDLS - CNB)',
  planningHorizon: '24-Hour Planning Horizon',
  tasksCount: null,
  totalTasks: 30,
  trainsCount: 50,
  lastSolveDuration: null,
  workerStatus: 'Standby',
  validatorStatus: 'Standby',
  dbStatus: 'Standalone (Demo Data)',
};

interface WorkspaceContextValue {
  telemetry: WorkspaceTelemetry;
  setTelemetry: React.Dispatch<React.SetStateAction<WorkspaceTelemetry>>;
  updateTelemetry: (partial: Partial<WorkspaceTelemetry>) => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined);

export function WorkspaceProvider({
  children,
  initialTelemetry,
}: {
  children: React.ReactNode;
  initialTelemetry?: Partial<WorkspaceTelemetry>;
}) {
  const [telemetry, setTelemetry] = useState<WorkspaceTelemetry>({
    ...DEFAULT_TELEMETRY,
    ...initialTelemetry,
  });

  const updateTelemetry = (partial: Partial<WorkspaceTelemetry>) => {
    setTelemetry((prev) => ({ ...prev, ...partial }));
  };

  const value = useMemo(
    () => ({ telemetry, setTelemetry, updateTelemetry }),
    [telemetry]
  );

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace(): WorkspaceContextValue {
  const context = useContext(WorkspaceContext);
  if (!context) {
    return {
      telemetry: DEFAULT_TELEMETRY,
      setTelemetry: () => {},
      updateTelemetry: () => {},
    };
  }
  return context;
}
