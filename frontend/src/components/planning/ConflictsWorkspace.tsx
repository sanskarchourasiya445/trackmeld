'use client';

import React from 'react';
import {
  AlertTriangle,
  Train,
  Wrench,
  Clock,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';

interface ConflictItem {
  id: string;
  category: 'TRAIN_HEADWAY' | 'TRACK_OCCUPANCY' | 'RESOURCE_CONTENTION';
  title: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  section: string;
  window: string;
  entitiesInvolved: string[];
  description: string;
  impactMinutes: number;
  recommendedAction: string;
  taskId: string;
}

const CONFLICTS_DATA: ConflictItem[] = [
  {
    id: 'CNF-2026-001',
    category: 'TRAIN_HEADWAY',
    title: 'Express Headway Buffer Violation: Train 02073 vs TSK-0007',
    severity: 'CRITICAL',
    section: 'SEC-12 (NDLS-GZB Mainline)',
    window: '14:00 – 15:30 UTC',
    entitiesInvolved: ['Train 02073 (Shatabdi Exp)', 'Task TSK-0007 (Track Renewal)'],
    description:
      'Possession window intersects high-priority passenger express train trajectory with an overlap of 18 minutes. Hard headway safety margin (RULE-HEADWAY-01) violated on Track 1.',
    impactMinutes: 18,
    recommendedAction: 'Advance task possession start by 25 minutes or route Train 02073 via Down Relief Line.',
    taskId: 'TSK-0007',
  },
  {
    id: 'CNF-2026-002',
    category: 'TRACK_OCCUPANCY',
    title: 'Concurrent Section Block Contention: SEC-ALJN-TDL',
    severity: 'HIGH',
    section: 'SEC-ALJN-TDL',
    window: '06:00 – 09:30 UTC',
    entitiesInvolved: ['Task TSK-0012', 'Task TSK-0014', 'SEC-ALJN-TDL'],
    description:
      'Two discrete engineering work orders requested non-overlapping possessions on the same single-line section within a shared window exceeding total daylight block capacity.',
    impactMinutes: 45,
    recommendedAction: 'Bundle both works into a single continuous block possession under shadow possession rules.',
    taskId: 'TSK-0012',
  },
  {
    id: 'CNF-2026-003',
    category: 'RESOURCE_CONTENTION',
    title: 'Heavy Machinery Dual Allocation: CSM Tamping Machine TM-04',
    severity: 'MEDIUM',
    section: 'SEC-ETW-CNB',
    window: '11:00 – 14:00 UTC',
    entitiesInvolved: ['RES-TM-CSM-01', 'Task TSK-0001', 'Task TSK-0005'],
    description:
      'Continuous Action Tamping Machine CSM-01 allocated simultaneously to ballast maintenance and switch renewal across adjacent divisions.',
    impactMinutes: 60,
    recommendedAction: 'Shift TSK-0005 to second 12-hour shift or mobilize reserve tamper from Tundla Depot.',
    taskId: 'TSK-0001',
  },
];

interface ConflictsWorkspaceProps {
  onSelectTask: (taskId: string) => void;
  onNavigateToDiagnostics?: (taskId: string) => void;
}

export const ConflictsWorkspace: React.FC<ConflictsWorkspaceProps> = ({
  onSelectTask,
  onNavigateToDiagnostics,
}) => {
  return (
    <div className="flex-1 flex flex-col h-full bg-[#0B1120] p-3 sm:p-4 gap-2.5 overflow-hidden font-sans text-xs">
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#0F172A] border border-[#1A263D] rounded-lg p-3 sm:p-3.5 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400" />
            <h2 className="text-base font-bold text-[#F8FAFC]">Active Conflict Analysis</h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-bold border border-rose-500/30">
              3 Active Conflicts
            </span>
          </div>
          <p className="text-xs text-[#94A3B8] mt-0.5">
            Hard constraint collisions between train movements, block sections, and maintenance resources
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-[#64748B]">Resolution Status:</span>
          <span className="font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30 font-semibold">
            3 UNRESOLVED
          </span>
        </div>
      </div>

      {/* 2. Conflicts List Grid */}
      <div className="flex-1 overflow-y-auto space-y-3">
        {CONFLICTS_DATA.map((cnf) => {
          const isCritical = cnf.severity === 'CRITICAL';
          const isHigh = cnf.severity === 'HIGH';

          return (
            <div
              key={cnf.id}
              className="bg-[#0F172A] border border-[#1A263D] hover:border-[#2D436D] rounded-lg p-3.5 sm:p-4 space-y-3 transition-colors"
            >
              {/* Conflict Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#1A263D] pb-3">
                <div className="flex items-center gap-2.5">
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                      isCritical
                        ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
                        : isHigh
                        ? 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                        : 'bg-blue-500/20 text-blue-400 border-blue-500/40'
                    }`}
                  >
                    {cnf.severity}
                  </span>
                  <span className="font-mono text-xs text-[#8EA3BE]">{cnf.id}</span>
                  <span className="font-semibold text-sm text-[#F8FAFC]">{cnf.title}</span>
                </div>

                <div className="flex items-center gap-3 text-xs text-[#94A3B8] font-mono">
                  <span>{cnf.section}</span>
                  <span>•</span>
                  <span>{cnf.window}</span>
                </div>
              </div>

              {/* Conflict Body */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                {/* Involved Entities */}
                <div className="bg-[#070D18]/80 border border-[#1A263D] rounded-md p-3 space-y-1.5">
                  <span className="text-[10px] uppercase font-bold text-[#64748B] tracking-wider block">
                    Involved Entities
                  </span>
                  <ul className="space-y-1">
                    {cnf.entitiesInvolved.map((entity, idx) => (
                      <li key={idx} className="flex items-center gap-1.5 text-[#F8FAFC]">
                        {entity.includes('Train') ? (
                          <Train className="w-3.5 h-3.5 text-[#38BDF8] shrink-0" />
                        ) : (
                          <Wrench className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        )}
                        <span className="font-mono text-[11px] truncate">{entity}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Conflict Description & Impact */}
                <div className="bg-[#070D18]/80 border border-[#1A263D] rounded-md p-3 space-y-1 md:col-span-2">
                  <span className="text-[10px] uppercase font-bold text-[#64748B] tracking-wider block">
                    Causal Geometry & Rule Violation
                  </span>
                  <p className="text-[#CBD5E1] text-[11px] leading-relaxed">
                    {cnf.description}
                  </p>
                  <div className="text-[10px] text-rose-400 font-mono pt-1">
                    Direct Operational Delay / Contention Buffer: +{cnf.impactMinutes} minutes
                  </div>
                </div>
              </div>

              {/* Recommended Action & Navigations */}
              <div className="bg-[#101A2F]/80 border border-[#1A263D] rounded-md p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-start sm:items-center gap-2">
                  <Clock className="w-4 h-4 text-[#38BDF8] shrink-0 mt-0.5 sm:mt-0" />
                  <div>
                    <span className="font-semibold text-xs text-[#F8FAFC] mr-1">Recommended Path:</span>
                    <span className="text-xs text-[#CBD5E1]">{cnf.recommendedAction}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => onSelectTask(cnf.taskId)}
                    className="px-2.5 py-1 rounded text-xs font-medium bg-[#070D18] hover:bg-[#142038] border border-[#1A263D] text-[#F8FAFC] transition-colors flex items-center gap-1 cursor-pointer"
                  >
                    <span>Inspect Task</span>
                    <ArrowRight className="w-3 h-3 text-[#38BDF8]" />
                  </button>

                  {onNavigateToDiagnostics && (
                    <button
                      onClick={() => onNavigateToDiagnostics(cnf.taskId)}
                      className="px-2.5 py-1 rounded text-xs font-semibold bg-[#2563EB] hover:bg-[#1D4ED8] text-white transition-colors flex items-center gap-1 cursor-pointer shadow-xs"
                    >
                      <span>Root Cause</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
