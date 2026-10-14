import React, { useState } from 'react';
import { AlertTriangle, ShieldCheck, Server, Database, Activity, Clock } from 'lucide-react';
import { ResponsiveDrawer } from '@/components/common/ResponsiveDrawer';

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
  trainsCount = 14,
  lastSolveDuration = 1.48,
  workerStatus = 'Idle',
  validatorStatus = 'Active',
  dbStatus = 'Connected (5433)',
}) => {
  const [isMobileStatusOpen, setIsMobileStatusOpen] = useState(false);

  const isDbConnected = dbStatus.toLowerCase().includes('connected');
  const isWorkerBusy = ['solving', 'active', 'running'].includes(workerStatus.toLowerCase());
  const isWorkerError = ['error', 'failed'].includes(workerStatus.toLowerCase());
  const isValidatorActive = ['active', 'verified', 'passed'].includes(validatorStatus.toLowerCase());
  const isValidatorError = ['failed', 'breached'].includes(validatorStatus.toLowerCase());

  return (
    <>
      {/* 1. Desktop & Tablet Fixed Bottom Status Bar */}
      <footer className="hidden md:flex h-7 bg-[#050A13] border-t border-[#152238] px-3.5 items-center justify-between text-[11px] font-mono text-[#566B85] select-none z-30 shrink-0">
        {/* Left System Connectivity */}
        <div className="flex items-center gap-2.5 lg:gap-3.5 truncate min-w-0">
          <span className="flex items-center gap-1.5 text-[#8EA3BE] shrink-0" title={`PostgreSQL Database Status: ${dbStatus}`}>
            <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isDbConnected ? 'bg-emerald-400' : 'bg-rose-500'}`} />
            <span className="hidden lg:inline text-[#566B85]">PostgreSQL</span>
            <span className={isDbConnected ? 'text-[#CBD5E1]' : 'text-rose-400'}>{dbStatus}</span>
          </span>

          <span className="h-3 w-[1px] bg-[#152238] shrink-0" />

          <span className="flex items-center gap-1.5 text-[#8EA3BE] shrink-0" title={`Optimization Worker Status: ${workerStatus}`}>
            <Server className={`w-3 h-3 shrink-0 ${isWorkerBusy ? 'text-[#38BDF8]' : isWorkerError ? 'text-rose-500' : 'text-[#566B85]'}`} />
            <span className="hidden lg:inline text-[#566B85]">Worker:</span>
            <span className={isWorkerBusy ? 'text-[#38BDF8]' : isWorkerError ? 'text-rose-400' : 'text-[#CBD5E1]'}>
              {workerStatus}
            </span>
          </span>

          <span className="h-3 w-[1px] bg-[#152238] shrink-0" />

          <span className="inline-flex items-center gap-1.5 text-[#8EA3BE] shrink-0" title={`Safety Validator Status: ${validatorStatus}`}>
            <ShieldCheck className={`w-3 h-3 shrink-0 ${isValidatorActive ? 'text-emerald-400' : isValidatorError ? 'text-rose-500' : 'text-[#566B85]'}`} />
            <span className="hidden lg:inline text-[#566B85]">Validator:</span>
            <span className={isValidatorActive ? 'text-emerald-400' : isValidatorError ? 'text-rose-400' : 'text-[#CBD5E1]'}>
              {validatorStatus}
            </span>
          </span>
        </div>

        {/* Right Metrics & Environment Notice */}
        <div className="flex items-center gap-2.5 lg:gap-3 shrink-0">
          <span className="inline-flex items-center gap-1 text-[#94A3B8]">
            <span className="text-[#64748B]">Tasks:</span>
            <span className="text-[#F8FAFC] font-semibold">{tasksCount}/{totalTasks}</span>
          </span>

          <span className="h-3 w-[1px] bg-[#1E2D4A] shrink-0 hidden xl:inline-block" />

          <span className="hidden xl:inline-flex items-center gap-1 text-[#94A3B8]">
            <span className="text-[#64748B]">Solve Time:</span>
            <span className="text-[#F8FAFC] font-semibold">{lastSolveDuration.toFixed(2)}s</span>
            <span className="text-[10px] text-[#64748B]">(UTC)</span>
          </span>

          <span className="h-3 w-[1px] bg-[#1E2D4A] shrink-0" />

          <span className="text-amber-400 flex items-center gap-1 font-sans font-medium text-[10px] bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20 shrink-0">
            <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0" />
            <span>Synthetic Demo</span>
          </span>
        </div>
      </footer>

      {/* 2. Mobile Floating System Status Button (Does NOT eat vertical height) */}
      <div className="md:hidden fixed bottom-3 right-3 z-30">
        <button
          onClick={() => setIsMobileStatusOpen(true)}
          className="flex items-center gap-1.5 bg-[#0C1322] hover:bg-[#141F36] active:bg-[#1E2D4A] border border-[#1E2D4A] hover:border-[#2D436D] text-[#CBD5E1] text-[10px] font-mono px-2.5 py-1 rounded-full shadow-lg transition-colors focus-visible:ring-1 focus-visible:ring-[#38BDF8] outline-none"
          title="Open System Status"
          aria-label="Open System Status"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0" />
          <span>Status</span>
          <span className="text-[#64748B]">({tasksCount}/{totalTasks})</span>
        </button>
      </div>

      {/* 3. Mobile System Status Bottom Sheet */}
      <ResponsiveDrawer
        isOpen={isMobileStatusOpen}
        onClose={() => setIsMobileStatusOpen(false)}
        title="TrackMeld Infrastructure Status"
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">
            ONLINE
          </span>
        }
      >
        <div className="p-4 space-y-3 font-sans text-xs">
          <div className="grid grid-cols-2 gap-2.5">
            <div className="bg-[#0A0E17] border border-[#1E2D4A] rounded-lg p-3 space-y-1">
              <span className="text-[10px] text-[#64748B] flex items-center gap-1 uppercase font-bold font-mono">
                <Database className="w-3 h-3 text-emerald-400" />
                PostgreSQL
              </span>
              <div className="font-mono text-xs font-semibold text-[#F8FAFC]">{dbStatus}</div>
              <div className="text-[10px] text-[#94A3B8]">Port 5433 Cluster</div>
            </div>

            <div className="bg-[#0A0E17] border border-[#1E2D4A] rounded-lg p-3 space-y-1">
              <span className="text-[10px] text-[#64748B] flex items-center gap-1 uppercase font-bold font-mono">
                <Server className="w-3 h-3 text-[#3B82F6]" />
                Worker
              </span>
              <div className="font-mono text-xs font-semibold text-[#F8FAFC]">{workerStatus}</div>
              <div className="text-[10px] text-[#94A3B8]">CP-SAT Daemon</div>
            </div>

            <div className="bg-[#0A0E17] border border-[#1E2D4A] rounded-lg p-3 space-y-1">
              <span className="text-[10px] text-[#64748B] flex items-center gap-1 uppercase font-bold font-mono">
                <ShieldCheck className="w-3 h-3 text-emerald-400" />
                Validator
              </span>
              <div className="font-mono text-xs font-semibold text-emerald-400">{validatorStatus}</div>
              <div className="text-[10px] text-[#94A3B8]">12 Hard Rules</div>
            </div>

            <div className="bg-[#0A0E17] border border-[#1E2D4A] rounded-lg p-3 space-y-1">
              <span className="text-[10px] text-[#64748B] flex items-center gap-1 uppercase font-bold font-mono">
                <Activity className="w-3 h-3 text-[#3B82F6]" />
                Scheduled
              </span>
              <div className="font-mono text-xs font-semibold text-[#F8FAFC]">{tasksCount} / {totalTasks} Tasks</div>
              <div className="text-[10px] text-[#94A3B8]">{trainsCount} Active Trains</div>
            </div>
          </div>

          <div className="bg-[#0A0E17] border border-[#1E2D4A] rounded-lg p-3 space-y-1.5 font-mono text-[11px]">
            <div className="flex items-center justify-between text-[#94A3B8]">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-[#3B82F6]" />
                Last Solve Duration:
              </span>
              <span className="font-bold text-[#F8FAFC]">{lastSolveDuration.toFixed(2)}s (UTC)</span>
            </div>
          </div>

          <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-[11px] text-amber-300 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <p>
              <strong>Synthetic Environment:</strong> Operational train schedules and possession work orders are synthetic seed data for decision-support evaluation.
            </p>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              onClick={() => setIsMobileStatusOpen(false)}
              className="px-3.5 py-1.5 bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-medium rounded text-xs transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      </ResponsiveDrawer>
    </>
  );
};
