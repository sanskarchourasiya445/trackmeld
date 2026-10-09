'use client';

import React, { useState } from 'react';
import { Database, Filter, Cpu, ShieldCheck, UserCheck, Sparkles } from 'lucide-react';

export const SectionArchitecture: React.FC = () => {
  const [activeStep, setActiveStep] = useState<number>(3); // Default: Optimization

  const pipeline = [
    {
      num: '01',
      title: 'Planning Snapshot',
      actor: 'INGESTION ENGINE',
      desc: 'All scenario inputs are assembled into an immutable, frozen in-memory dataclass sealed with a canonical 64-character SHA-256 fingerprint.',
      tech: 'Python Dataclass • Canonical Sorting • Permutation Invariance',
      icon: Database,
    },
    {
      num: '02',
      title: 'Domain Rules',
      actor: 'COMPATIBILITY ENGINE',
      desc: 'Evaluates railway safety curfews, electrical isolation boundaries, and line headway rules into discrete hard and soft constraints.',
      tech: 'Classified: VERIFIED_SOURCE / ASSUMPTION / DEMO_ONLY',
      icon: Filter,
    },
    {
      num: '03',
      title: 'CP-SAT Optimization',
      actor: 'GOOGLE OR-TOOLS SOLVER',
      desc: 'Packs maintenance tasks into continuous traffic gaps using optional interval variables and disjunctive NoOverlap constraints.',
      tech: 'Single-Threaded Determinism • Random Seed: 0 • 72h Horizon',
      icon: Cpu,
    },
    {
      num: '04',
      title: 'Independent Validator',
      actor: 'SAFETY FIREWALL',
      desc: 'Re-evaluates the proposed schedule against raw snapshot timestamps across 13 check categories. If error_count > 0, approval is blocked.',
      tech: 'Decoupled from Solver Variables • Schedule Identity Fingerprint',
      icon: ShieldCheck,
    },
    {
      num: '05',
      title: 'Four-Eyes Approval',
      actor: 'AUTHORIZED OPERATOR',
      desc: 'State machine enforces separation of duties: plan.created_by != actor.username. The engineer who creates the plan cannot approve it.',
      tech: 'PlanVersion State Machine • Append-Only Audit Ledger',
      icon: UserCheck,
    },
  ];

  return (
    <section id="architecture" className="py-24 sm:py-32 px-6 sm:px-12 lg:px-20 border-t border-[#1E293B] bg-[#060A13]">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="max-w-3xl">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#38BDF8] font-bold">
            07 / ARCHITECTURAL INTEGRITY
          </div>
          <h2 className="mt-2 text-3xl sm:text-5xl font-extrabold tracking-tight text-[#F8FAFC]">
            INVIOLABLE
            <br />
            <span className="text-[#38BDF8]">PIPELINE ARCHITECTURE.</span>
          </h2>
          <p className="mt-4 text-base sm:text-lg text-[#94A3B8] leading-relaxed">
            Rules classify. Optimization schedules. Independent Validator verifies. Humans review. Humans approve. AI explains.
          </p>
        </div>

        {/* Linear Horizontal Pipeline Flow */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-5 gap-3">
          {pipeline.map((step, idx) => {
            const Icon = step.icon;
            const isActive = activeStep === idx;
            return (
              <div
                key={idx}
                onClick={() => setActiveStep(idx)}
                className={`p-5 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                  isActive
                    ? 'bg-[#0B1426] border-[#38BDF8] shadow-xl shadow-blue-900/30 -translate-y-1'
                    : 'bg-[#080D1A]/80 border-[#1E293B] hover:border-[#38BDF8]/40 hover:bg-[#0A101F]'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xl font-bold text-[#2563EB]">
                      {step.num}
                    </span>
                    <Icon className={`w-4 h-4 ${isActive ? 'text-[#38BDF8]' : 'text-[#64748B]'}`} />
                  </div>
                  <div className="text-[9px] font-mono uppercase font-bold text-[#38BDF8] tracking-wider mt-3">
                    {step.actor}
                  </div>
                  <h3 className="font-bold text-sm text-[#F8FAFC] mt-0.5">
                    {step.title}
                  </h3>
                </div>

                <div className="mt-6 pt-3 border-t border-[#1E293B]/60 text-[9px] font-mono text-[#64748B]">
                  {isActive ? 'ACTIVE VIEW' : 'INSPECT →'}
                </div>
              </div>
            );
          })}
        </div>

        {/* Detailed Inspector Card */}
        <div className="mt-8 rounded-xl border border-[#1E293B] bg-[#04070D] p-6 sm:p-8 shadow-2xl">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[#1E293B] text-xs font-mono">
            <span className="text-[#38BDF8] font-bold">
              STAGE {pipeline[activeStep].num}: {pipeline[activeStep].title.toUpperCase()}
            </span>
            <span className="text-emerald-400 font-bold">
              ACTOR: {pipeline[activeStep].actor}
            </span>
          </div>

          <div className="mt-6 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            <div className="lg:col-span-8">
              <h4 className="text-lg font-bold text-[#F8FAFC]">
                {pipeline[activeStep].title}
              </h4>
              <p className="mt-2 text-sm text-[#94A3B8] leading-relaxed">
                {pipeline[activeStep].desc}
              </p>
              <div className="mt-4 inline-block font-mono text-xs px-3 py-1.5 rounded bg-[#080D1A] border border-[#1E293B] text-[#38BDF8]">
                {pipeline[activeStep].tech}
              </div>
            </div>

            {/* Read-Only AI Sidecar Box */}
            <div className="lg:col-span-4 bg-[#080D1A] border border-purple-500/30 rounded-lg p-5">
              <div className="flex items-center gap-2 text-purple-400 font-mono text-xs font-bold uppercase">
                <Sparkles className="w-4 h-4" />
                <span>Read-Only AI Copilot</span>
              </div>
              <p className="mt-2 text-xs text-[#94A3B8] leading-relaxed">
                Operates strictly alongside this pipeline. Provides causal explanations and sensitivity queries. Has zero mutation or sign-off authority.
              </p>
              <div className="mt-3 text-[10px] font-mono text-purple-300 font-bold">
                PRINCIPLE: AI Explains, Humans Decide
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
