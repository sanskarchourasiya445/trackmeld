'use client';

import React, { useState } from 'react';
import { Cpu, CheckCircle, Code, ShieldCheck } from 'lucide-react';

export const SectionOptimization: React.FC = () => {
  const [activeStage, setActiveStage] = useState<number>(2);

  const stages = [
    {
      step: '01',
      title: 'Candidate Windows',
      sub: 'TEMPORAL DISCRETIZATION',
      desc: 'All scenario tasks, durations, and allowed operational windows [w_start, w_end] are discretized to exact integer minutes starting at horizon_start = 0.',
      formula: 'time_offset_min = (dt - horizon_start).total_seconds() // 60',
      icon: ClockIcon,
    },
    {
      step: '02',
      title: 'Hard Invariants',
      sub: 'DISJUNCTIVE INTERVAL ENVELOPES',
      desc: 'Possession envelopes are created by expanding the work duration with mandatory safety buffers [start - buf_before, end + buf_after).',
      formula: 'model.AddNoOverlap(possession_intervals_on_section)',
      icon: ShieldCheck,
    },
    {
      step: '03',
      title: 'CP-SAT Solver',
      sub: 'DISCRETE CONSTRAINT PROGRAMMING',
      desc: 'Google OR-Tools CP-SAT solves the global satisfaction and optimization problem using bounded single-threaded search with fixed random seeds for 100% determinism.',
      formula: 'solver.parameters.num_search_workers = 1\nsolver.parameters.random_seed = 0',
      icon: Cpu,
    },
    {
      step: '04',
      title: 'Optimized Plan',
      sub: 'BIT-FOR-BIT REPRODUCIBILITY',
      desc: 'Yields a certified ScheduleResult with explicit status: OPTIMAL, FEASIBLE, or INFEASIBLE. Zero heuristic guessing.',
      formula: 'schedule_identity = SHA256(canonical_schedule_json)',
      icon: CheckCircle,
    },
  ];

  return (
    <section id="optimization" className="py-24 sm:py-32 px-6 sm:px-12 lg:px-20 border-t border-[#1E293B] bg-[#060A13]">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="max-w-3xl">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#38BDF8] font-bold">
            03 / MATHEMATICAL RIGOR
          </div>
          <h2 className="mt-2 text-3xl sm:text-5xl font-extrabold tracking-tight text-[#F8FAFC]">
            OPTIMIZE,
            <br />
            <span className="text-[#38BDF8]">DON&apos;T GUESS.</span>
          </h2>
          <p className="mt-4 text-base sm:text-lg text-[#94A3B8] leading-relaxed">
            Greedy heuristics make early short-sighted decisions that strand critical work. TrackMeld formulates possession planning as an exact discrete constraint satisfaction and optimization problem using Google OR-Tools CP-SAT.
          </p>
        </div>

        {/* 4-Stage Optimization Pipeline Flow */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-4 gap-4">
          {stages.map((stage, idx) => {
            const isActive = activeStage === idx;
            const Icon = stage.icon;
            return (
              <div
                key={idx}
                onClick={() => setActiveStage(idx)}
                className={`p-6 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                  isActive
                    ? 'bg-[#0B1426] border-[#2563EB] shadow-xl shadow-blue-900/30 -translate-y-1'
                    : 'bg-[#080D1A]/80 border-[#1E293B] hover:border-[#38BDF8]/40 hover:bg-[#0A101F]'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-2xl font-black text-[#2563EB]">
                      {stage.step}
                    </span>
                    <Icon className={`w-5 h-5 ${isActive ? 'text-[#38BDF8]' : 'text-[#64748B]'}`} />
                  </div>
                  <div className="font-mono text-[9px] uppercase font-bold text-[#38BDF8] tracking-wider mt-3">
                    {stage.sub}
                  </div>
                  <h3 className="font-bold text-lg text-[#F8FAFC] mt-0.5">
                    {stage.title}
                  </h3>
                  <p className="mt-2 text-xs text-[#94A3B8] leading-relaxed">
                    {stage.desc}
                  </p>
                </div>

                <div className="mt-6 pt-3 border-t border-[#1E293B]/70 font-mono text-[10px] text-[#38BDF8] flex items-center justify-between">
                  <span>{isActive ? 'INSPECTING FORMULATION' : 'CLICK TO VIEW'}</span>
                  <span>→</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Detailed Formulation Showcase Box */}
        <div className="mt-8 rounded-xl border border-[#1E293B] bg-[#04070D] p-6 sm:p-8 shadow-2xl">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[#1E293B] text-xs font-mono">
            <div className="flex items-center gap-2">
              <Code className="w-4 h-4 text-[#38BDF8]" />
              <span className="text-[#F1F5F9] font-bold">
                CP-SAT MATHEMATICAL FORMULATION (STAGE {stages[activeStage].step}: {stages[activeStage].title.toUpperCase()})
              </span>
            </div>
            <span className="text-emerald-400 font-bold">
              SOLVER: GOOGLE OR-TOOLS CP-SAT
            </span>
          </div>

          <div className="mt-6 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            {/* Left: Code Box */}
            <div className="lg:col-span-7 bg-[#080D1A] border border-[#1E293B] rounded-lg p-5 font-mono text-xs text-[#38BDF8] whitespace-pre leading-relaxed overflow-x-auto shadow-inner">
              {stages[activeStage].formula}
            </div>

            {/* Right: Explanation & Guarantees */}
            <div className="lg:col-span-5 space-y-4">
              <div>
                <div className="text-[10px] font-mono text-[#64748B] uppercase tracking-wider font-bold">
                  Operational Guarantee
                </div>
                <div className="text-sm sm:text-base font-bold text-[#F1F5F9] mt-1">
                  Global Constraint Feasibility
                </div>
                <p className="text-xs text-[#94A3B8] mt-1.5 leading-relaxed">
                  Every scheduled task placement is proven strictly feasible against all overlapping commercial train traversals, adjacent line restrictions, and resource fleet capacities.
                </p>
              </div>

              <div className="pt-3 border-t border-[#1E293B] flex items-center justify-between text-xs font-mono">
                <span className="text-[#64748B]">DETERMINISTIC WORKERS:</span>
                <span className="text-[#F8FAFC] font-bold">1 (Repeatable)</span>
              </div>
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-[#64748B]">TIME HORIZON:</span>
                <span className="text-[#F8FAFC] font-bold">72 Hours (Rolling)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

function ClockIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" {...props}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
}
