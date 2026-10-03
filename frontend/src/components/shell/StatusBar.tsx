'use client';

import React from 'react';
import { AlertTriangle, ShieldCheck, Server } from 'lucide-react';

interface StatusBarProps {
  tasksCount?: number;
  totalTasks?: number;
  trainsCount?: number;
  lastSolveDuration?: number;
  workerStatus?: string;
  validatorStatus?: string;
  dbStatus?: string;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  tasksCount = 29,
  totalTasks = 30,
  lastSolveDuration = 1.48,
  workerStatus = 'Idle',
  validatorStatus = 'Active',
  dbStatus = 'Connected (5433)',
}) => {
  return (
    <footer className="h-7 bg-[#070B12] border-t border-[#1E2D4A] px-3.5 flex items-center justify-between text-[11px] font-mono text-[#64748B] select-none z-30 shrink-0">
      {/* Left System Connectivity */}
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5 text-[#94A3B8]">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span>PostgreSQL {dbStatus}</span>
        </span>
        <span className="text-[#1E2D4A]">|</span>
        <span className="flex items-center gap-1.5 text-[#94A3B8]">
          <Server className="w-3 h-3 text-[#3B82F6]" />
          <span>Worker: {workerStatus}</span>
        </span>
        <span className="text-[#1E2D4A]">|</span>
        <span className="hidden sm:inline-flex items-center gap-1.5 text-[#94A3B8]">
          <ShieldCheck className="w-3 h-3 text-emerald-400" />
          <span>Validator: {validatorStatus}</span>
        </span>
      </div>

      {/* Right Metrics & Environment Notice */}
      <div className="flex items-center gap-4">
        <span className="hidden md:inline-flex items-center gap-1 text-[#94A3B8]">
          <span>Tasks: <strong className="text-[#F8FAFC]">{tasksCount}/{totalTasks}</strong></span>
        </span>
        <span className="text-[#1E2D4A] hidden md:inline">|</span>
        <span className="hidden sm:inline-flex items-center gap-1 text-[#94A3B8]">
          <span>Solve Time: <strong className="text-[#F8FAFC]">{lastSolveDuration.toFixed(2)}s</strong> (UTC)</span>
        </span>
        <span className="text-[#1E2D4A] hidden sm:inline">|</span>
        <span className="text-amber-400 flex items-center gap-1 font-sans font-medium text-[10px] bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
          <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0" />
          <span>Synthetic Environment</span>
        </span>
      </div>
    </footer>
  );
};
