'use client';

import React from 'react';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { StatusBar } from './StatusBar';
import { SidebarProvider, useSidebar } from '@/contexts/SidebarContext';

interface AppShellProps {
  children: React.ReactNode;
  activeScenarioId?: string;
  scenarioName?: string;
  planningHorizon?: string;
  tasksCount?: number;
  totalTasks?: number;
  trainsCount?: number;
  lastSolveDuration?: number;
  workerStatus?: string;
  validatorStatus?: string;
  onRefresh?: () => void;
  // Backward compatibility props
  onTriggerSolve?: () => void;
  onOpenApproval?: () => void;
  isSolving?: boolean;
  canApprove?: boolean;
}

const AppShellContent: React.FC<AppShellProps> = ({
  children,
  activeScenarioId = 'SCN-DEMO-001',
  scenarioName = 'Northern Corridor',
  planningHorizon = '72-Hour Planning Horizon',
  tasksCount = 29,
  totalTasks = 30,
  trainsCount = 14,
  lastSolveDuration = 1.48,
  workerStatus = 'Idle',
  validatorStatus = 'Active',
}) => {
  const { isCollapsed, handleGlobalToggle } = useSidebar();

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
          {children}
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
