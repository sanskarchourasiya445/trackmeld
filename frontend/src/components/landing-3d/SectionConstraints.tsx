'use client';

import React, { useState } from 'react';
import { ShieldAlert, CheckCircle2 } from 'lucide-react';

export const SectionConstraints: React.FC = () => {
  const [selectedConstraint, setSelectedConstraint] = useState<number>(0);

  const constraints = [
    {
      id: 'headway',
      title: 'Train Headway Clearance',
      category: 'TEMPORAL SAFETY',
      impact: 'CRITICAL HARD RULE',
      desc: 'Maintenance blocks cannot start until the preceding train has cleared the block section plus mandatory safety setup buffers (10m minimum before work begins).',
      naiveApproach: 'Naïve schedule packs task into 12-minute window between trains.',
      trackmeldSolution: 'TrackMeld enforces half-open interval non-overlap: [start - 10m, end + 10m) must be 100% free of train paths.',
      metric: '0 Traversal Collisions',
    },
    {
      id: 'adjacent',
      title: 'Adjacent-Track Caution Orders',
      category: 'SPATIAL SAFETY',
      impact: 'SPEED RESTRICTIONS',
      desc: 'Demolition or crane slewing on UP MAIN line imposes speed restrictions or full blocks on parallel DOWN MAIN lines to prevent structural fouling.',
      naiveApproach: 'Assumes parallel track can operate at unrestricted 130 km/h during heavy track lifting.',
      trackmeldSolution: 'Encodes AdjacentTrackImpact (NONE, CAUTION_ORDER, FULL_TRAFFIC_BLOCK) directly into CP-SAT disjunctive constraints.',
      metric: 'Physical Clearances Guaranteed',
    },
    {
      id: 'ohe',
      title: 'Traction Power Isolations',
      category: 'ELECTRICAL CLEARANCE',
      impact: 'POWER BLOCK (25 kV)',
      desc: 'OHE overhead wiring maintenance requires complete de-energization and earthing of the feeder sector, immobilizing all electric locomotives in that sector.',
      naiveApproach: 'Schedules diesel and electric trains blindly across de-energized traction sectors.',
      trackmeldSolution: 'Correlates feeder substation boundary joints to train traction types (ELECTRIC vs DIESEL) to prevent stranded rakes.',
      metric: '100% Earthing Compliance',
    },
    {
      id: 'precedence',
      title: 'Task Precedence Dependencies',
      category: 'LOGICAL SEQUENCING',
      impact: 'FINISH-TO-START',
      desc: 'Track renewal follows strict sequential order: Ballast screening must finish before track tamping, which must complete before dynamic track stabilization.',
      naiveApproach: 'Dispatches tamping gang while ballast cleaner is still operating on the section.',
      trackmeldSolution: 'Enforces linear inequalities in CP-SAT: start[successor] >= end[predecessor] with machine transit buffers.',
      metric: 'Zero Sequence Violations',
    },
  ];

  return (
    <section id="constraints" className="py-24 sm:py-32 px-6 sm:px-12 lg:px-20 border-t border-[#1E293B] bg-[#04070D]">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="max-w-3xl">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#38BDF8] font-bold">
            02 / OPERATIONAL REALISM
          </div>
          <h2 className="mt-2 text-3xl sm:text-5xl font-extrabold tracking-tight text-[#F8FAFC]">
            PLAN AROUND
            <br />
            <span className="text-[#38BDF8]">REAL CONSTRAINTS.</span>
          </h2>
          <p className="mt-4 text-base sm:text-lg text-[#94A3B8] leading-relaxed">
            A maintenance possession is not a calendar entry. It is a spatial-temporal reservation bounded by commercial headways, traction power blocks, machine routing, and adjacent-track hazards.
          </p>
        </div>

        {/* Interactive Constraint Matrix */}
        <div className="mt-16 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Constraint Selector */}
          <div className="lg:col-span-5 space-y-3">
            {constraints.map((c, idx) => {
              const isSelected = selectedConstraint === idx;
              return (
                <div
                  key={c.id}
                  onClick={() => setSelectedConstraint(idx)}
                  className={`p-5 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-[#0B1220] border-[#2563EB] shadow-xl shadow-blue-900/20 translate-x-1'
                      : 'bg-[#080D18]/60 border-[#1E293B] hover:border-[#38BDF8]/40 hover:bg-[#0A101C]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-[#38BDF8] font-bold uppercase tracking-wider">
                      {c.category}
                    </span>
                    <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold uppercase">
                      {c.impact}
                    </span>
                  </div>
                  <h3 className="font-bold text-base text-[#F8FAFC] mt-2">
                    {c.title}
                  </h3>
                  <p className="mt-1.5 text-xs text-[#94A3B8] leading-relaxed line-clamp-2">
                    {c.desc}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Right Column: Comparative Problem vs Solution Visualizer */}
          <div className="lg:col-span-7 bg-[#080D1A] border border-[#1E293B] rounded-xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
            {/* Top Bar */}
            <div className="flex items-center justify-between pb-4 border-b border-[#1E293B] text-xs font-mono">
              <span className="text-[#38BDF8] font-bold uppercase">
                {constraints[selectedConstraint].title}
              </span>
              <span className="text-emerald-400 font-bold">
                {constraints[selectedConstraint].metric}
              </span>
            </div>

            {/* Description */}
            <div className="mt-6 text-sm sm:text-base text-[#F1F5F9] font-medium leading-relaxed">
              {constraints[selectedConstraint].desc}
            </div>

            {/* Dual Comparative Box */}
            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Naive Approach Box (Red Alert) */}
              <div className="bg-[#1C0E14] border border-rose-500/30 rounded-lg p-5">
                <div className="flex items-center gap-2 text-rose-400 font-mono text-xs font-bold uppercase">
                  <ShieldAlert className="w-4 h-4" />
                  <span>Heuristic / Naïve Scheduler</span>
                </div>
                <p className="mt-3 text-xs text-[#E2E8F0] leading-relaxed">
                  {constraints[selectedConstraint].naiveApproach}
                </p>
                <div className="mt-4 pt-3 border-t border-rose-500/20 text-[10px] font-mono text-rose-400 font-bold">
                  OUTCOME: Cascading Train Delays & Safety Hazards
                </div>
              </div>

              {/* TrackMeld Approach Box (Electric Blue / Green) */}
              <div className="bg-[#071324] border border-[#2563EB]/40 rounded-lg p-5">
                <div className="flex items-center gap-2 text-[#38BDF8] font-mono text-xs font-bold uppercase">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>TrackMeld Constraint Engine</span>
                </div>
                <p className="mt-3 text-xs text-[#E2E8F0] leading-relaxed">
                  {constraints[selectedConstraint].trackmeldSolution}
                </p>
                <div className="mt-4 pt-3 border-t border-[#2563EB]/30 text-[10px] font-mono text-emerald-400 font-bold">
                  OUTCOME: Mathematically Proven Feasibility
                </div>
              </div>
            </div>

            {/* Bottom Proof Tag */}
            <div className="mt-8 pt-4 border-t border-[#1E293B] flex items-center justify-between text-[11px] font-mono text-[#64748B]">
              <span>ENFORCEMENT: DISCRETE CP-SAT MODEL BUILDER</span>
              <span className="text-[#38BDF8]">ZERO COMBINATORIAL SHORTCUTS</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
