'use client';

import React from 'react';
import Link from 'next/link';
import {
  TrainTrack,
  ArrowRight,
  ShieldCheck,
  Cpu,
  Lock,
  AlertTriangle,
  Sliders,
  Terminal,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SyntheticDataBadge } from '@/components/common/SyntheticDataBadge';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0A] text-[#F5F5F5] flex flex-col font-sans selection:bg-[#4C87E7]/30 selection:text-white">
      {/* 1. Small announcement strip */}
      <div className="bg-[#141418] border-b border-amber-500/30 text-amber-200 px-4 py-1.5 text-xs flex items-center justify-between z-40 select-none">
        <div className="flex items-center gap-2 overflow-hidden mx-auto">
          <span className="flex items-center gap-1.5 font-mono font-bold tracking-wider uppercase text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded border border-amber-500/40 shrink-0">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            Decision-Support Prototype
          </span>
          <span className="text-[#A1A1AA] truncate text-[11px]">
            TrackMeld is a research and decision-support prototype evaluated on synthetic CRIS corridor datasets. Not for direct train dispatch.
          </span>
        </div>
      </div>

      {/* 2. Navbar */}
      <header className="h-16 border-b border-[#202024] px-6 lg:px-12 flex items-center justify-between sticky top-0 bg-[#0A0A0A]/90 backdrop-blur-md z-30">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded bg-[#18181C] border border-[#29292F] flex items-center justify-center">
            <TrainTrack className="w-5 h-5 text-[#4C87E7]" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-bold text-base tracking-tight text-[#F5F5F5]">TrackMeld</span>
              <span className="text-[10px] font-mono uppercase bg-[#18181C] text-[#4C87E7] px-1.5 py-0.2 rounded border border-[#29292F]">
                CRIS Prototype
              </span>
            </div>
            <span className="text-[10px] text-[#71717A] tracking-wider uppercase font-mono">
              Railway Maintenance Possession Platform
            </span>
          </div>
        </div>

        <nav className="hidden md:flex items-center gap-6 text-xs font-mono text-[#A1A1AA]">
          <a href="#problem" className="hover:text-white transition-colors">Problem</a>
          <a href="#architecture" className="hover:text-white transition-colors">Core Boundary</a>
          <a href="#workflow" className="hover:text-white transition-colors">Workflow</a>
          <a href="#governance" className="hover:text-white transition-colors">Governance</a>
        </nav>

        <div className="flex items-center gap-3">
          <Link href="/planning">
            <Button className="bg-[#4C87E7] hover:bg-[#3B82F6] text-white font-mono text-xs shadow-none">
              Launch Workspace
              <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
            </Button>
          </Link>
        </div>
      </header>

      {/* 3. Hero Section */}
      <section className="py-20 px-6 lg:px-12 max-w-6xl mx-auto text-center flex flex-col items-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#18181C] border border-[#29292F] text-xs font-mono text-[#4C87E7] mb-6">
          <Terminal className="w-3.5 h-3.5" />
          <span>Rules Classify • Optimization Schedules • Humans Approve • AI Explains</span>
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-[#F5F5F5] max-w-4xl leading-tight">
          Smarter maintenance planning for a more reliable railway.
        </h1>

        <p className="mt-6 text-base sm:text-lg text-[#A1A1AA] max-w-3xl leading-relaxed">
          Coordinate track tamping, OHE wiring, and bridge inspection around dense passenger corridors.
          Mathematically optimize possession windows with CP-SAT while preserving strict safety rules and human sign-off.
        </p>

        <div className="mt-8 flex flex-col sm:flex-row items-center gap-4">
          <Link href="/planning">
            <Button size="lg" className="bg-[#4C87E7] hover:bg-[#3B82F6] text-white font-mono text-sm px-6 h-11">
              Enter Operations Planning Workspace
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
          <Link href="/overview">
            <Button size="lg" variant="outline" className="border-[#29292F] hover:bg-[#18181C] text-[#F5F5F5] font-mono text-sm px-6 h-11">
              View Corridor KPIs & Audit
            </Button>
          </Link>
        </div>

        {/* Hero Interactive Corridor Preview Graphic */}
        <div className="mt-14 w-full bg-[#141418] border border-[#202024] rounded-lg p-5 text-left relative overflow-hidden shadow-2xl">
          <div className="flex items-center justify-between border-b border-[#202024] pb-3 mb-4">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="font-mono text-xs font-bold text-[#F5F5F5]">
                Northern Trunk Corridor (NDLS–CNB 440km)
              </span>
              <span className="text-[10px] font-mono text-[#71717A] bg-[#0E0E12] px-2 py-0.5 rounded">
                24h CP-SAT Schedule
              </span>
            </div>
            <SyntheticDataBadge size="sm" />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <div className="bg-[#0E0E12] p-3 rounded border border-[#202024] font-mono">
              <span className="text-[#71717A] text-[10px]">SCHEDULE RATE</span>
              <div className="text-xl font-bold text-emerald-400">87.5%</div>
              <div className="text-[10px] text-[#A1A1AA]">7 of 8 scheduled</div>
            </div>
            <div className="bg-[#0E0E12] p-3 rounded border border-[#202024] font-mono">
              <span className="text-[#71717A] text-[10px]">POSSESSION TIME</span>
              <div className="text-xl font-bold text-[#F5F5F5]">18.5h</div>
              <div className="text-[10px] text-[#A1A1AA]">Across 5 sections</div>
            </div>
            <div className="bg-[#0E0E12] p-3 rounded border border-[#202024] font-mono">
              <span className="text-[#71717A] text-[10px]">PASSENGER DELAY</span>
              <div className="text-xl font-bold text-[#4C87E7]">0 min</div>
              <div className="text-[10px] text-[#A1A1AA]">Hard safety constraint</div>
            </div>
            <div className="bg-[#0E0E12] p-3 rounded border border-[#202024] font-mono">
              <span className="text-[#71717A] text-[10px]">SHADOW BUNDLING</span>
              <div className="text-xl font-bold text-amber-300">1 Co-location</div>
              <div className="text-[10px] text-[#A1A1AA]">Tamping + OHE wire</div>
            </div>
          </div>

          <div className="bg-[#0E0E12] rounded p-3 border border-[#202024] flex items-center justify-between text-xs font-mono">
            <span className="text-[#A1A1AA]">
              Independent Validator: <strong className="text-emerald-400">48 Rules Evaluated • Zero Violations</strong>
            </span>
            <Link href="/planning" className="text-[#4C87E7] hover:underline flex items-center gap-1 font-semibold">
              Open Interactive Time-Space Diagram
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </section>

      {/* 4. Core Principle Architecture Section */}
      <section id="architecture" className="py-16 border-t border-[#202024] bg-[#0E0E12] px-6 lg:px-12">
        <div className="max-w-6xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <span className="text-xs font-mono uppercase text-[#4C87E7] tracking-wider font-semibold">
              Design Boundaries
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#F5F5F5] mt-2">
              Four Inviolable Architectural Boundaries
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-[#141418] border border-[#202024] p-5 rounded-md flex flex-col justify-between">
              <div>
                <div className="w-8 h-8 rounded bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 mb-3">
                  <Sliders className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-sm text-[#F5F5F5] font-mono mb-1">1. Rules Classify</h3>
                <p className="text-xs text-[#A1A1AA] leading-relaxed">
                  Deterministic compatibility engine evaluates safety curfews, electrical isolation, and headway rules. Rules never originate in the optimizer.
                </p>
              </div>
            </div>

            <div className="bg-[#141418] border border-[#202024] p-5 rounded-md flex flex-col justify-between">
              <div>
                <div className="w-8 h-8 rounded bg-[#4C87E7]/10 border border-[#4C87E7]/30 flex items-center justify-center text-[#4C87E7] mb-3">
                  <Cpu className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-sm text-[#F5F5F5] font-mono mb-1">2. Solver Schedules</h3>
                <p className="text-xs text-[#A1A1AA] leading-relaxed">
                  Integer interval CP-SAT solver packs maintenance tasks into available traffic gaps with shadow possession bundling and reproducible seeds.
                </p>
              </div>
            </div>

            <div className="bg-[#141418] border border-[#202024] p-5 rounded-md flex flex-col justify-between">
              <div>
                <div className="w-8 h-8 rounded bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 mb-3">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-sm text-[#F5F5F5] font-mono mb-1">3. Validator Verifies</h3>
                <p className="text-xs text-[#A1A1AA] leading-relaxed">
                  The solver never self-certifies. A separate validation layer verifies all hard constraints against raw timetables before declaring plan approvability.
                </p>
              </div>
            </div>

            <div className="bg-[#141418] border border-[#202024] p-5 rounded-md flex flex-col justify-between">
              <div>
                <div className="w-8 h-8 rounded bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-3">
                  <Lock className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-sm text-[#F5F5F5] font-mono mb-1">4. Humans Approve</h3>
                <p className="text-xs text-[#A1A1AA] leading-relaxed">
                  COMPLETED ≠ APPROVED. Divisional Railway Managers explicitly inspect and electronically authorize every possession into an immutable audit ledger.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Workflow Section */}
      <section id="workflow" className="py-16 px-6 lg:px-12 max-w-6xl mx-auto w-full">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <span className="text-xs font-mono uppercase text-[#4C87E7] tracking-wider font-semibold">
            Execution Lifecycle
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#F5F5F5] mt-2">
            The 7-Step Planning Pipeline
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-2 font-mono text-xs text-center">
          {[
            { step: '01', title: 'Ingest', desc: 'Timetables & Work Orders' },
            { step: '02', title: 'Rules', desc: 'Deterministic Filtering' },
            { step: '03', title: 'Baseline', desc: 'Greedy Benchmarking' },
            { step: '04', title: 'CP-SAT', desc: 'Integer Interval Solve' },
            { step: '05', title: 'Validate', desc: 'Independent Audit' },
            { step: '06', title: 'Diagnose', desc: 'Root-Cause Analysis' },
            { step: '07', title: 'Approve', desc: 'Immutable Sign-off' },
          ].map((item) => (
            <div
              key={item.step}
              className="bg-[#141418] border border-[#202024] p-3 rounded flex flex-col items-center justify-center relative"
            >
              <div className="text-[10px] text-[#4C87E7] font-bold">{item.step}</div>
              <div className="font-bold text-[#F5F5F5] mt-1">{item.title}</div>
              <div className="text-[10px] text-[#71717A] mt-0.5">{item.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* 6. Footer */}
      <footer className="mt-auto border-t border-[#202024] bg-[#0E0E12] py-8 px-6 lg:px-12 text-xs font-mono text-[#71717A]">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <TrainTrack className="w-4 h-4 text-[#4C87E7]" />
            <span className="text-[#F5F5F5] font-semibold">TrackMeld Prototype</span>
            <span>• Smart India Hackathon 2026 / CRIS Context</span>
          </div>

          <div className="flex items-center gap-4 text-[11px]">
            <Link href="/overview" className="hover:text-white transition-colors">Overview</Link>
            <Link href="/planning" className="hover:text-white transition-colors">Planning Workspace</Link>
            <Link href="/audit" className="hover:text-white transition-colors">Governance Audit</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
