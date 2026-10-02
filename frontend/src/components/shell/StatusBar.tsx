'use client';

import React from 'react';
import { Server, Clock, AlertTriangle, ShieldCheck } from 'lucide-react';

interface StatusBarProps {
  tasksCount?: number;
  trainsCount?: number;
  lastSolveDuration?: number;
  timezone?: string;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  tasksCount = 8,
  trainsCount = 14,
  lastSolveDuration = 1.48,
  timezone = 'UTC',
}) => {
  return (
    <footer className="h-7 bg-[#0E0E12] border-t border-[#202024] px-3 flex items-center justify-between text-[11px] font-mono text-[#71717A] select-none z-30 shrink-0">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5 text-[#A1A1AA]">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span>PostgreSQL: Connected (:5433)</span>
        </span>
        <span className="text-[#202024]">|</span>
        <span className="flex items-center gap-1.5 text-[#A1A1AA]">
          <Server className="w-3 h-3 text-[#4C87E7]" />
          <span>Job Worker: Idle</span>
        </span>
        <span className="text-[#202024]">|</span>
        <span className="hidden sm:inline-flex items-center gap-1 text-[#A1A1AA]">
          <ShieldCheck className="w-3 h-3 text-emerald-400" />
          <span>Independent Validator: Enforcing Hard Rules</span>
        </span>
      </div>

      <div className="flex items-center gap-4">
        <span className="hidden md:inline-flex items-center gap-1 text-[#A1A1AA]">
          <span>Tasks: <strong>{tasksCount}</strong></span>
          <span className="text-[#202024]">/</span>
          <span>Trains: <strong>{trainsCount}</strong></span>
        </span>
        <span className="text-[#202024] hidden md:inline">|</span>
        <span className="hidden sm:inline-flex items-center gap-1 text-[#A1A1AA]">
          <Clock className="w-3 h-3 text-zinc-400" />
          <span>Solve Time: {lastSolveDuration.toFixed(2)}s ({timezone})</span>
        </span>
        <span className="text-[#202024] hidden sm:inline">|</span>
        <span className="text-amber-400/90 flex items-center gap-1 font-semibold">
          <AlertTriangle className="w-3 h-3 text-amber-400" />
          <span>Synthetic Prototype</span>
        </span>
      </div>
    </footer>
  );
};
