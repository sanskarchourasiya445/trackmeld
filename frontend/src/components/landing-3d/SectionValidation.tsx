'use client';

import React, { useState } from 'react';
import { CheckCircle2, Lock } from 'lucide-react';

export const SectionValidation: React.FC = () => {
  const [activeCategory, setActiveCategory] = useState<number>(6); // Default: TRAIN_MOVEMENT

  const checkCategories = [
    { id: 'STRUCTURAL', name: 'Structural Integrity', desc: 'Task existence, unique interval assignments, valid section IDs, and interval boundaries.' },
    { id: 'HORIZON', name: 'Planning Horizon Bounds', desc: 'All work intervals and possession envelopes reside strictly within [horizon_start, horizon_end].' },
    { id: 'TASK_WINDOW', name: 'Requested Work Windows', desc: 'Tasks must not violate their allowed window [w_start, w_end] specified by department requisitions.' },
    { id: 'DURATION_AND_BUFFERS', name: 'Buffers & Durations', desc: 'Duration matches estimate; buffer_before (10m) and buffer_after (10m) envelopes are fully intact.' },
    { id: 'SECTION_OCCUPANCY', name: 'Section Non-Overlap', desc: 'Half-open interval non-overlap on single lines: [pos_start, pos_end) has zero concurrent possessions.' },
    { id: 'MULTI_SECTION', name: 'Multi-Section Corridor', desc: 'Multi-block tasks reference valid corridor sections and maintain continuous boundary integrity.' },
    { id: 'TRAIN_MOVEMENT', name: 'Train Traversal Clearance', desc: 'Possession envelopes have zero collision with scheduled passenger and freight train passes.' },
    { id: 'TRACK_SPATIAL_SAFETY', name: 'Spatial & Track Direction', desc: 'Validates line direction alignment (UP vs DOWN) and adjacent-track full block or caution order rules.' },
    { id: 'RESOURCES', name: 'Resource Capacity Limits', desc: 'Specialized track machines (tampers, ballast cleaners) and certified gangs are never committed to multiple tasks simultaneously.' },
    { id: 'DEPENDENCIES', name: 'Task Precedence Chains', desc: 'Predecessor finish-to-start relationships: start[successor] >= end[predecessor].' },
    { id: 'MANDATORY_TASKS', name: 'Mandatory Work Presence', desc: '100% presence check: Critical statutory safety tasks cannot be dropped or left unscheduled.' },
    { id: 'DOMAIN_RULES', name: 'Statutory Railway Rules', desc: 'Adherence to Indian Railways / CRIS P-Way manual clauses and speed restriction mandates.' },
    { id: 'SOLVER_OUTPUT_SANITY', name: 'Solver Sanity Audit', desc: 'Ensures objective values, bound gaps, and returned telemetry match mathematical reality.' },
  ];

  return (
    <section id="validation" className="py-24 sm:py-32 px-6 sm:px-12 lg:px-20 border-t border-[#1E293B] bg-[#04070D]">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="max-w-3xl">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#38BDF8] font-bold">
            04 / INDEPENDENT SAFETY AUDIT
          </div>
          <h2 className="mt-2 text-3xl sm:text-5xl font-extrabold tracking-tight text-[#F8FAFC]">
            VALIDATE
            <br />
            <span className="text-[#38BDF8]">INDEPENDENTLY.</span>
          </h2>
          <p className="mt-4 text-base sm:text-lg text-[#94A3B8] leading-relaxed">
            The optimization engine never self-certifies. TrackMeld enforces a completely decoupled safety firewall that re-evaluates candidate schedules against raw snapshot data across 13 distinct check categories.
          </p>
        </div>

        {/* Optimizer vs Validator Architecture Comparison */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Box 1: The Optimizer (Proposes) */}
          <div className="bg-[#080D1A] border border-[#2563EB]/40 rounded-xl p-6 sm:p-8 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1E293B]">
              <span className="text-xs font-mono text-[#38BDF8] font-bold uppercase">
                THE OPTIMIZER (CP-SAT)
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-[#38BDF8] font-bold">
                PROPOSES
              </span>
            </div>
            <h3 className="font-bold text-lg text-[#F8FAFC] mt-4">
              Maximizes Operational Value
            </h3>
            <p className="mt-2 text-xs sm:text-sm text-[#94A3B8] leading-relaxed">
              Discovers the globally optimal candidate placement across available gaps, maximizing scheduled priority scores subject to modeled constraints.
            </p>
            <div className="mt-4 pt-3 border-t border-[#1E293B] text-[11px] font-mono text-[#64748B]">
              ROLE: Mathematical candidate generation
            </div>
          </div>

          {/* Box 2: The Independent Validator (Certifies) */}
          <div className="bg-[#071318] border border-emerald-500/40 rounded-xl p-6 sm:p-8 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#1E293B]">
              <span className="text-xs font-mono text-emerald-400 font-bold uppercase">
                INDEPENDENT VALIDATOR
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">
                AUDITS & BLOCKS
              </span>
            </div>
            <h3 className="font-bold text-lg text-[#F8FAFC] mt-4">
              Verifies Raw Snapshot Invariants
            </h3>
            <p className="mt-2 text-xs sm:text-sm text-[#94A3B8] leading-relaxed">
              Zero knowledge of solver variables or heuristics. Evaluates raw timetable timestamps and physical track intervals. If ANY check produces an ERROR, approval is blocked.
            </p>
            <div className="mt-4 pt-3 border-t border-[#1E293B] text-[11px] font-mono text-emerald-400 font-bold">
              ROLE: Inviolable safety certification gate
            </div>
          </div>
        </div>

        {/* The 13 Check Categories Matrix */}
        <div className="mt-12 bg-[#080D1A] border border-[#1E293B] rounded-xl p-6 sm:p-8 shadow-2xl">
          <div className="flex items-center justify-between pb-4 border-b border-[#1E293B]">
            <span className="text-xs font-mono text-[#F1F5F9] font-bold">
              13-CATEGORY SAFETY FIREWALL MATRIX
            </span>
            <span className="text-xs font-mono text-emerald-400 font-bold">
              13 / 13 CHECKS PASSING
            </span>
          </div>

          <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            {checkCategories.map((cat, idx) => {
              const isSelected = activeCategory === idx;
              return (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategory(idx)}
                  className={`p-3 rounded-lg text-left border transition-all text-xs font-mono flex items-start justify-between gap-2 ${
                    isSelected
                      ? 'bg-[#102236] border-[#38BDF8] text-[#F1F5F9] shadow-md'
                      : 'bg-[#050811] border-[#1E293B] text-[#94A3B8] hover:border-[#38BDF8]/40 hover:text-[#F1F5F9]'
                  }`}
                >
                  <div>
                    <div className="text-[9px] text-[#38BDF8] font-bold">
                      {(idx + 1).toString().padStart(2, '0')}
                    </div>
                    <div className="font-semibold mt-0.5">{cat.name}</div>
                  </div>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                </button>
              );
            })}
          </div>

          {/* Active Category Detail Card */}
          <div className="mt-6 p-4 rounded-lg bg-[#04070D] border border-[#1E293B] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="text-[10px] font-mono text-[#38BDF8] font-bold uppercase">
                CATEGORY {activeCategory + 1}: {checkCategories[activeCategory].id}
              </div>
              <div className="text-sm font-bold text-[#F8FAFC] mt-0.5">
                {checkCategories[activeCategory].name}
              </div>
              <p className="text-xs text-[#94A3B8] mt-1 leading-relaxed">
                {checkCategories[activeCategory].desc}
              </p>
            </div>
            <div className="shrink-0 font-mono text-xs text-emerald-400 font-bold flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-500/10 border border-emerald-500/30">
              <CheckCircle2 className="w-4 h-4" />
              <span>IS_APPROVABLE = TRUE</span>
            </div>
          </div>
        </div>

        {/* Invariant Banner: VALID != APPROVED */}
        <div className="mt-8 p-4 rounded-xl bg-[#14120A] border border-amber-500/30 flex items-center gap-3 text-xs font-mono text-amber-300">
          <Lock className="w-5 h-5 text-amber-400 shrink-0" />
          <div>
            <strong className="text-amber-400 font-bold">NON-NEGOTIABLE BOUNDARY:</strong>{' '}
            A schedule certified as <span className="text-emerald-400 font-bold">VALID</span> by the independent validator is still{' '}
            <span className="text-rose-400 font-bold">NOT APPROVED</span>. Validation grants eligibility for human review; formal operational sign-off requires independent Four-Eyes authorization.
          </div>
        </div>
      </div>
    </section>
  );
};
