'use client';

import React, { useState } from 'react';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { StatusBar } from './StatusBar';

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
  userRole?: string;
  userName?: string;
  onRefresh?: () => void;
  // Backward compatibility props
  onTriggerSolve?: () => void;
  onOpenApproval?: () => void;
  isSolving?: boolean;
  canApprove?: boolean;
}

export const AppShell: React.FC<AppShellProps> = ({
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
  userRole = 'Operations Officer',
  userName = 'Operator',
}) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#0A0E17] text-[#F8FAFC] font-sans antialiased">
      {/* 1. Global Application Header */}
      <TopBar
        activeScenarioId={activeScenarioId}
        scenarioName={scenarioName}
        planningHorizon={planningHorizon}
        userRole={userRole}
        userName={userName}
        onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
      />

      {/* 2. Main Workspace Body (Sidebar + Children) */}
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
        />
        <main className="flex-1 overflow-y-auto overflow-x-hidden flex flex-col bg-[#0A0E17]">
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
