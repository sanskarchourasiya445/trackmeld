'use client';

import React from 'react';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { StatusBar } from './StatusBar';
import { SidebarProvider, useSidebar } from '@/contexts/SidebarContext';
import { useWorkspace } from '@/contexts/WorkspaceContext';

export interface AppShellProps {
  children: React.ReactNode;
  activeScenarioId?: string;
  scenarioName?: string;
  planningHorizon?: string;
  tasksCount?: number | null;
  totalTasks?: number | null;
  trainsCount?: number | null;
  lastSolveDuration?: number | null;
  workerStatus?: string;
  validatorStatus?: string;
  dbStatus?: string;
  onRefresh?: () => void;
  // Backward compatibility props
  onTriggerSolve?: () => void;
  onOpenApproval?: () => void;
  isSolving?: boolean;
  canApprove?: boolean;
}

const AppShellContent: React.FC<AppShellProps> = (props) => {
  const { isCollapsed, handleGlobalToggle } = useSidebar();
  const { telemetry } = useWorkspace();

  const activeScenarioId = props.activeScenarioId ?? telemetry.activeScenarioId;
  const scenarioName = props.scenarioName ?? telemetry.scenarioName;
  const planningHorizon = props.planningHorizon ?? telemetry.planningHorizon;
  const tasksCount = props.tasksCount !== undefined ? props.tasksCount : telemetry.tasksCount;
  const totalTasks = props.totalTasks !== undefined ? props.totalTasks : telemetry.totalTasks;
  const trainsCount = props.trainsCount !== undefined ? props.trainsCount : telemetry.trainsCount;
  const lastSolveDuration = props.lastSolveDuration !== undefined ? props.lastSolveDuration : telemetry.lastSolveDuration;
  const workerStatus = props.workerStatus ?? telemetry.workerStatus;
  const validatorStatus = props.validatorStatus ?? telemetry.validatorStatus;
  const dbStatus = props.dbStatus ?? telemetry.dbStatus;

  return (
    <div className="flex flex-col h-[100dvh] w-full overflow-hidden bg-[#0A0E17] text-[#F8FAFC] font-sans antialiased">
      {/* 1. Global Application Header */}
      <TopBar
        activeScenarioId={activeScenarioId}
        scenarioName={scenarioName}
        planningHorizon={planningHorizon}
        onToggleSidebar={handleGlobalToggle}
        isSidebarCollapsed={isCollapsed}
      />

      {/* 2. Main Workspace Body (Collapsible Sidebar + Expansive Workspace) */}
      <div className="flex flex-1 min-h-0 min-w-0 overflow-hidden relative">
        <Sidebar />
        <main className="flex-1 min-w-0 min-h-0 overflow-hidden flex flex-col bg-[#0A0E17] transition-[width,flex] duration-200 ease-in-out">
          {props.children}
        </main>
      </div>

      {/* 3. Global System Status Bar (Bottom) */}
      <StatusBar
        tasksCount={tasksCount}
        totalTasks={totalTasks}
        trainsCount={trainsCount}
        lastSolveDuration={lastSolveDuration}
        workerStatus={workerStatus}
        validatorStatus={validatorStatus}
        dbStatus={dbStatus}
      />
    </div>
  );
};

export const AppShell: React.FC<AppShellProps> = (props) => {
  return (
    <SidebarProvider>
      <AppShellContent {...props} />
    </SidebarProvider>
  );
};
