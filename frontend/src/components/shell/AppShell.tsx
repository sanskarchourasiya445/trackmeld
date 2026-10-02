'use client';

import React from 'react';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { StatusBar } from './StatusBar';

interface AppShellProps {
  children: React.ReactNode;
  onTriggerSolve?: () => void;
  onOpenApproval?: () => void;
  isSolving?: boolean;
  canApprove?: boolean;
  activeScenarioId?: string;
  tasksCount?: number;
  trainsCount?: number;
  lastSolveDuration?: number;
  userRole?: string;
  userName?: string;
  onRefresh?: () => void;
}

export const AppShell: React.FC<AppShellProps> = ({
  children,
  onTriggerSolve,
  onOpenApproval,
  isSolving = false,
  canApprove = true,
  activeScenarioId = 'SCN-DEMO-001',
  tasksCount,
  trainsCount,
  lastSolveDuration,
  userRole = 'Operations Officer',
  userName = 'Operator',
  onRefresh,
}) => {
  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#0A0E17] text-[#F8FAFC] font-sans antialiased">
      {/* 1. Top Navigation Bar */}
      <TopBar
        onTriggerSolve={onTriggerSolve}
        onOpenApproval={onOpenApproval}
        isSolving={isSolving}
        canApprove={canApprove}
        activeScenarioId={activeScenarioId}
        userRole={userRole}
        userName={userName}
        onRefresh={onRefresh}
      />

      {/* 2. Main Workspace Area (Sidebar + Children) */}
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar />
        <main className="flex-1 overflow-y-auto overflow-x-hidden flex flex-col bg-[#0A0E17]">
          {children}
        </main>
      </div>

      {/* 3. Bottom Telemetry Bar */}
      <StatusBar
        tasksCount={tasksCount}
        trainsCount={trainsCount}
        lastSolveDuration={lastSolveDuration}
      />
    </div>
  );
};
