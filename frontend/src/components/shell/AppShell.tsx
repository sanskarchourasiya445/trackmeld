'use client';

import React from 'react';
import { ModeBanner } from './ModeBanner';
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
}) => {
  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#0A0A0A] text-[#F5F5F5]">
      {/* 1. Synthetic Prototype Warning Banner */}
      <ModeBanner />

      {/* 2. Top Navigation Bar */}
      <TopBar
        onTriggerSolve={onTriggerSolve}
        onOpenApproval={onOpenApproval}
        isSolving={isSolving}
        canApprove={canApprove}
        activeScenarioId={activeScenarioId}
      />

      {/* 3. Main Workspace Area (Sidebar + Children) */}
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar />
        <main className="flex-1 overflow-y-auto overflow-x-hidden flex flex-col bg-[#0A0A0A]">
          {children}
        </main>
      </div>

      {/* 4. Bottom Telemetry Bar */}
      <StatusBar
        tasksCount={tasksCount}
        trainsCount={trainsCount}
        lastSolveDuration={lastSolveDuration}
      />
    </div>
  );
};
