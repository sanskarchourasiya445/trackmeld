'use client';

import React, { useState } from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';

export const SectionPlanComparison: React.FC = () => {
  const [selectedPlan, setSelectedPlan] = useState<'A' | 'B' | 'C'>('B');

  const plans = [
    {
      id: 'A' as const,
      name: 'Plan A: Manual Baseline',
      tag: 'LOCAL HEURISTIC',
      highlight: false,
      feasibilityStatus: 'INFEASIBLE (Safety Violations)',
      feasibilityColor: 'text-rose-400 bg-rose-500/10 border-rose-500/30',
      isCertified: false,
      metrics: {
        durationCaptured: '64.2%',
        durationSub: '19 / 30 Tasks Placed',
        conflicts: '8 Contention Points',
        conflictSub: 'Infringes 10m Safety Buffers',
        delayExposure: '+142 min',
        delaySub: 'Cascading Train Delays',
        machineryIdle: '38.5%',
        machinerySub: 'Fleet Stranded by Conflicts',
        validationPassed: '7 / 13 Checks',
      },
      summary:
        'Standard spreadsheet or greedy scheduler. Suffers from global constraint blindness, leaving 11 maintenance tasks unplaced and generating 8 severe train headway conflicts.',
    },
    {
      id: 'B' as const,
      name: 'Plan B: CP-SAT Optimized',
      tag: 'RECOMMENDED OPERATIONAL PLAN',
      highlight: true,
      feasibilityStatus: 'CERTIFIED VALID & APPROVABLE',
      feasibilityColor: 'text-emerald-400 bg-emerald-500/20 border-emerald-500/40',
      isCertified: true,
      metrics: {
        durationCaptured: '96.8%',
        durationSub: '29 / 30 Tasks Scheduled',
        conflicts: '0 Conflicts',
        conflictSub: 'Proven 100% Feasible',
        delayExposure: '+0 min',
        delaySub: 'Zero Commercial Delay Added',
        machineryIdle: '6.2%',
        machinerySub: 'Tightly Packed Gang Shifts',
        validationPassed: '13 / 13 Checks',
      },
      summary:
        'Track-Aware Conservative CP-SAT optimization. Maximizes maintenance duration capture while guaranteeing zero train headway collisions and complete compliance across all 13 safety check categories.',
    },
    {
      id: 'C' as const,
      name: 'Plan C: Conservative Fallback',
      tag: 'WHOLE-SECTION LOCKING',
      highlight: false,
      feasibilityStatus: 'CERTIFIED VALID (Reduced Throughput)',
      feasibilityColor: 'text-sky-400 bg-sky-500/10 border-sky-500/30',
      isCertified: true,
      metrics: {
        durationCaptured: '81.4%',
        durationSub: '24 / 30 Tasks Scheduled',
        conflicts: '0 Conflicts',
        conflictSub: 'Safe Whole-Section Locking',
        delayExposure: '+26 min',
        delaySub: 'Minor Speed Restriction Sinks',
        machineryIdle: '19.4%',
        machinerySub: 'Single Line Blockage Buffers',
        validationPassed: '13 / 13 Checks',
      },
      summary:
        'Whole-section fallback mode. Safe when topology or adjacent line metadata is unverified. Preserves safety by locking both tracks entirely during possession windows at the cost of 5 deferred tasks.',
    },
  ];

  return (
    <section id="comparison" className="py-24 sm:py-32 px-6 sm:px-12 lg:px-20 border-t border-[#1E293B] bg-[#04070D]">
      <span id="plan-comparison" className="sr-only" />
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="max-w-3xl">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#38BDF8] font-bold">
            06 / SCENARIO EVALUATION
          </div>
          <h2 className="mt-2 text-3xl sm:text-5xl font-extrabold tracking-tight text-[#F8FAFC]">
            PRECISION
            <br />
            <span className="text-[#38BDF8]">PLAN COMPARISON.</span>
          </h2>
          <p className="mt-4 text-base sm:text-lg text-[#94A3B8] leading-relaxed">
            Evaluate alternative schedules side-by-side on the exact same snapshot. Compare manual baselines against CP-SAT optimized candidate plans and conservative whole-section alternatives.
          </p>
        </div>

        {/* 3-Column Plan Comparison Cards */}
        <div className="mt-16 grid grid-cols-1 lg:grid-cols-3 gap-6">
          {plans.map((p) => {
            const isSelected = selectedPlan === p.id;
            return (
              <div
                key={p.id}
                onClick={() => setSelectedPlan(p.id)}
                className={`rounded-2xl border p-6 sm:p-8 flex flex-col justify-between transition-all cursor-pointer relative overflow-hidden ${
                  p.highlight
                    ? 'bg-[#0B1528] border-[#2563EB] shadow-2xl shadow-blue-900/40 ring-1 ring-[#38BDF8]/40'
                    : isSelected
                    ? 'bg-[#09101E] border-[#38BDF8]/60 shadow-xl'
                    : 'bg-[#070D18]/80 border-[#1E293B] hover:border-[#38BDF8]/30 hover:bg-[#090F1C]'
                }`}
              >
                {/* Featured Badge on Plan B */}
                {p.highlight && (
                  <div className="absolute top-0 right-0 bg-[#2563EB] text-white text-[9px] font-mono font-bold uppercase tracking-wider px-3 py-1 rounded-bl-lg">
                    OPTIMAL INCUMBENT
                  </div>
                )}

                <div>
                  <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#38BDF8]">
                    {p.tag}
                  </div>
                  <h3 className="font-extrabold text-xl text-[#F8FAFC] mt-1">
                    {p.name}
                  </h3>

                  {/* Feasibility Pill */}
                  <div
                    className={`mt-4 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold border ${p.feasibilityColor}`}
                  >
                    {p.isCertified ? (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5" />
                    )}
                    <span>{p.feasibilityStatus}</span>
                  </div>

                  {/* Summary Text */}
                  <p className="mt-4 text-xs sm:text-sm text-[#94A3B8] leading-relaxed">
                    {p.summary}
                  </p>

                  {/* Key Metrics Breakdown */}
                  <div className="mt-8 space-y-3 pt-6 border-t border-[#1E293B]">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-[#64748B]">Duration Captured:</span>
                      <div className="text-right">
                        <span className="text-sm font-bold font-mono text-[#F1F5F9]">
                          {p.metrics.durationCaptured}
                        </span>
                        <div className="text-[10px] font-mono text-[#64748B]">
                          {p.metrics.durationSub}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-[#64748B]">Train Conflicts:</span>
                      <div className="text-right">
                        <span
                          className={`text-sm font-bold font-mono ${
                            p.metrics.conflicts.startsWith('0') ? 'text-emerald-400' : 'text-rose-400'
                          }`}
                        >
                          {p.metrics.conflicts}
                        </span>
                        <div className="text-[10px] font-mono text-[#64748B]">
                          {p.metrics.conflictSub}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-[#64748B]">Timetable Delay:</span>
                      <div className="text-right">
                        <span
                          className={`text-sm font-bold font-mono ${
                            p.metrics.delayExposure.startsWith('+0') ? 'text-emerald-400' : 'text-amber-400'
                          }`}
                        >
                          {p.metrics.delayExposure}
                        </span>
                        <div className="text-[10px] font-mono text-[#64748B]">
                          {p.metrics.delaySub}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-[#64748B]">Fleet Idle Time:</span>
                      <div className="text-right">
                        <span className="text-sm font-bold font-mono text-[#F1F5F9]">
                          {p.metrics.machineryIdle}
                        </span>
                        <div className="text-[10px] font-mono text-[#64748B]">
                          {p.metrics.machinerySub}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-[#64748B]">Validator Audit:</span>
                      <div className="text-right">
                        <span
                          className={`text-sm font-bold font-mono ${
                            p.metrics.validationPassed.startsWith('13') ? 'text-emerald-400' : 'text-rose-400'
                          }`}
                        >
                          {p.metrics.validationPassed}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  className={`mt-8 w-full py-2.5 rounded-lg text-xs font-mono font-bold tracking-wide transition-all ${
                    p.highlight
                      ? 'bg-[#2563EB] hover:bg-[#1D4ED8] text-white shadow-md'
                      : 'bg-[#0F172A] hover:bg-[#1E293B] text-[#94A3B8] border border-[#1E293B]'
                  }`}
                >
                  {p.highlight ? 'SELECTED FOR REVIEW →' : 'INSPECT PLAN DETAILS'}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
