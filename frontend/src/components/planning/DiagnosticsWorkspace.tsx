'use client';

import React from 'react';
import { MaintenanceTask } from '@/types/railway';
import { DiagnosticsReport } from '@/types/planning';
import {
  AlertTriangle,
  GitBranch,
  Check,
  X,
  Clock,
  Lightbulb,
  Train,
  Wrench,
  Cpu,
} from 'lucide-react';

interface DiagnosticsWorkspaceProps {
  task: MaintenanceTask | null;
  diagnosticsReport?: DiagnosticsReport | null;
  onSelectTask?: (taskId: string) => void;
}

export const DiagnosticsWorkspace: React.FC<DiagnosticsWorkspaceProps> = ({
  task,
}) => {
  const currentTaskId = task?.task_code || task?.task_id || 'TSK-0007';
  const currentTitle = task?.title || 'Switch Expansion Joint Greasing & Tightening';
  const sectionCode = task?.section_code || task?.section_id || 'SEC-ALJN-TDL';

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0A0E17] p-4 gap-3 overflow-hidden select-none font-sans text-xs">
      {/* 1. Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-3.5 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-[#3B82F6]" />
            <h2 className="text-base font-bold text-[#F8FAFC]">Causal Constraint Diagnostics</h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-bold border border-rose-500/30">
              Task: {currentTaskId}
            </span>
          </div>
          <p className="text-xs text-[#94A3B8] mt-0.5">
            Mathematical reason codes, constraint collisions, and relaxation what-if analyses
          </p>
        </div>

        <div className="text-xs font-mono text-[#CBD5E1] bg-[#141F36] border border-[#1E2D4A] px-3 py-1 rounded">
          Section: <strong className="text-[#F8FAFC]">{sectionCode}</strong>
        </div>
      </div>

      {/* 2. Main Diagnostics Grid */}
      <div className="flex-1 overflow-y-auto space-y-3.5">
        {/* Primary Finding Alert Box */}
        <div className="bg-rose-950/20 border border-rose-500/40 rounded-lg p-4 space-y-2">
          <div className="flex items-center gap-2 text-rose-400 font-bold text-sm">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>PRIMARY CAUSAL FINDING: INFEASIBLE IN REQUESTED WINDOW</span>
          </div>
          <p className="text-xs text-rose-100 leading-relaxed">
            Task <strong>{currentTaskId}</strong> ({currentTitle}) could not be accommodated inside permitted window 07:00–10:00 UTC due to high-density passenger express traffic and gang machine contention.
          </p>
          <div className="flex items-center gap-4 text-[11px] font-mono text-rose-300/80 pt-1">
            <span>Reason Code: SOLVER_DID_NOT_RETURN_PLACEMENT</span>
            <span>•</span>
            <span>Priority Score: 44.17 pts</span>
          </div>
        </div>

        {/* 5-Step Causal Decision Pipeline */}
        <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-[#F8FAFC]">
            <GitBranch className="w-4 h-4 text-[#3B82F6]" />
            <span>Deterministic Causal Decision Pipeline</span>
          </div>

          <div className="space-y-2 border-l-2 border-[#1E2D4A] pl-3 ml-2 text-xs">
            <div className="flex items-center gap-2 text-emerald-400">
              <Check className="w-3.5 h-3.5 shrink-0" />
              <span className="font-semibold">Step 1: Candidate Interval Generated</span>
              <span className="text-[#64748B] font-mono text-[11px]">— Window bounds evaluated (06:00–10:00 UTC)</span>
            </div>
            <div className="flex items-center gap-2 text-emerald-400">
              <Check className="w-3.5 h-3.5 shrink-0" />
              <span className="font-semibold">Step 2: Department Work Duration Confirmed</span>
              <span className="text-[#64748B] font-mono text-[11px]">— 120 minutes required + 30 min buffers</span>
            </div>
            <div className="flex items-center gap-2 text-amber-400">
              <Clock className="w-3.5 h-3.5 shrink-0" />
              <span className="font-semibold">Step 3: Track Occupancy Contention Detected</span>
              <span className="text-[#64748B] font-mono text-[11px]">— Section {sectionCode} shared with TSK-0006</span>
            </div>
            <div className="flex items-center gap-2 text-rose-400 font-bold">
              <X className="w-3.5 h-3.5 shrink-0" />
              <span>Step 4: Express Train Trajectory Collision</span>
              <span className="text-rose-300 font-mono text-[11px]">— Train 02073 overlaps requested slot by 18 min</span>
            </div>
            <div className="flex items-center gap-2 text-rose-400 font-bold">
              <X className="w-3.5 h-3.5 shrink-0" />
              <span>Step 5: Solver Excluded from Global Optimum</span>
              <span className="text-[#64748B] font-mono text-[11px]">— Lower priority weight than passenger train delay penalty</span>
            </div>
          </div>
        </div>

        {/* Colliding Entities */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-3.5 space-y-2">
            <span className="text-[10px] uppercase font-bold text-[#64748B] tracking-wider block">
              Conflicting Train Movement
            </span>
            <div className="flex items-center gap-2.5">
              <Train className="w-4 h-4 text-[#3B82F6]" />
              <div>
                <span className="font-mono font-semibold text-[#F8FAFC]">02073 • Shatabdi Express</span>
                <span className="block text-[11px] text-[#94A3B8]">Entry 13:40 → Exit 18:15 (Protected Tier 1)</span>
              </div>
            </div>
          </div>

          <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-3.5 space-y-2">
            <span className="text-[10px] uppercase font-bold text-[#64748B] tracking-wider block">
              Contending Maintenance Resource
            </span>
            <div className="flex items-center gap-2.5">
              <Wrench className="w-4 h-4 text-amber-400" />
              <div>
                <span className="font-mono font-semibold text-[#F8FAFC]">RES-CREW-ENG-G03</span>
                <span className="block text-[11px] text-[#94A3B8]">Track Renewal Gang occupied on TSK-0006</span>
              </div>
            </div>
          </div>
        </div>

        {/* Hypothetical Relaxation Analyses */}
        <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold text-amber-400">
              <Lightbulb className="w-4 h-4" />
              <span>Hypothetical Relaxation Analyses (What-If Scenarios)</span>
            </div>
            <span className="text-[10px] font-mono text-[#64748B] bg-[#141F36] px-2 py-0.5 rounded">
              DECISION SUPPORT ONLY • NOT AUTO-COMMITTED
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="bg-[#0A0E17]/60 border border-[#1E2D4A] rounded-md p-3 space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="font-bold text-[#F8FAFC]">Widen Time Window</span>
                <span className="text-[9.5px] font-bold text-emerald-400 bg-emerald-950 px-1.5 py-0.5 rounded border border-emerald-800">
                  FEASIBLE
                </span>
              </div>
              <p className="text-[11px] text-[#94A3B8] leading-relaxed">
                Widening permitted window by +90 minutes allows open slot at 11:30–13:30 UTC with zero train headway delays.
              </p>
            </div>

            <div className="bg-[#0A0E17]/60 border border-[#1E2D4A] rounded-md p-3 space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="font-bold text-[#F8FAFC]">Mobilize Reserve Crew</span>
                <span className="text-[9.5px] font-bold text-emerald-400 bg-emerald-950 px-1.5 py-0.5 rounded border border-emerald-800">
                  FEASIBLE
                </span>
              </div>
              <p className="text-[11px] text-[#94A3B8] leading-relaxed">
                If contractor gang mobilized from Ghaziabad Yard, eliminates resource contention on G03.
              </p>
            </div>

            <div className="bg-[#0A0E17]/60 border border-[#1E2D4A] rounded-md p-3 space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="font-bold text-[#F8FAFC]">Route Diversion</span>
                <span className="text-[9.5px] font-bold text-emerald-400 bg-emerald-950 px-1.5 py-0.5 rounded border border-emerald-800">
                  FEASIBLE
                </span>
              </div>
              <p className="text-[11px] text-[#94A3B8] leading-relaxed">
                Diverting Train 02073 to Down Relief Line frees Track 1 for full possession.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
