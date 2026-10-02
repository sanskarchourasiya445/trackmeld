'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  TrainTrack,
  ArrowRight,
  ShieldCheck,
  Cpu,
  Lock,
  Play,
  Sliders,
  Activity,
  FileCheck,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SyntheticDataBadge } from '@/components/common/SyntheticDataBadge';
import { RailwayCanvas } from '@/components/railway/RailwayCanvas';
import {
  DEMO_CORRIDOR,
  DEMO_TASKS,
  DEMO_TRAINS,
  DEMO_SCHEDULE_RESULT,
} from '@/lib/api/client';

export default function LandingPage() {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>('TSK-0007');
  const [selectedSectionCode, setSelectedSectionCode] = useState<string | null>('SEC-12');
  const [selectedTrainId, setSelectedTrainId] = useState<string | null>('02073');

  return (
    <div className="min-h-screen bg-[#080C14] text-[#F8FAFC] flex flex-col font-sans selection:bg-[#2563EB]/30 selection:text-white antialiased">
      {/* 1. Header Navigation */}
      <header className="h-16 border-b border-[#1E2D4A] px-6 lg:px-12 flex items-center justify-between sticky top-0 bg-[#080C14]/90 backdrop-blur-md z-40">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded bg-[#141F36] border border-[#2D436D] group-hover:border-[#3B82F6] transition-colors flex items-center justify-center">
              <TrainTrack className="w-4 h-4 text-[#3B82F6]" />
            </div>
            <span className="font-bold text-base tracking-tight text-[#F8FAFC]">
              TrackMeld
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-xs text-[#94A3B8]">
            <a href="#home" className="text-white font-medium hover:text-white transition-colors">Home</a>
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#architecture" className="hover:text-white transition-colors">Architecture</a>
            <a href="#governance" className="hover:text-white transition-colors">Governance</a>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <SyntheticDataBadge size="sm" />
          <Link href="/planning">
            <Button size="sm" className="bg-[#141F36] hover:bg-[#1A2846] text-[#F8FAFC] border border-[#2D436D] text-xs h-8 px-3 font-medium">
              Operator Sign-in
            </Button>
          </Link>
        </div>
      </header>

      {/* 2. Hero Section */}
      <section className="pt-12 pb-16 px-6 lg:px-12 max-w-7xl mx-auto w-full flex flex-col items-center text-center">
        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-[#F8FAFC] max-w-4xl leading-tight">
          Smarter Railway Possession Planning
        </h1>

        <p className="mt-4 text-sm sm:text-base text-[#94A3B8] max-w-2xl leading-relaxed">
          AI-powered, validated, and human-governed maintenance planning for a safer, more efficient rail network.
        </p>

        {/* Value Prop Pills */}
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#111C30] border border-[#1E2D4A] text-[#94A3B8]">
            <Cpu className="w-3.5 h-3.5 text-[#3B82F6]" />
            Optimized Scheduling
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#111C30] border border-[#1E2D4A] text-[#94A3B8]">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Independent Validation
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#111C30] border border-[#1E2D4A] text-[#94A3B8]">
            <Lock className="w-3.5 h-3.5 text-amber-400" />
            Human Approval
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#111C30] border border-[#1E2D4A] text-[#94A3B8]">
            <FileCheck className="w-3.5 h-3.5 text-sky-400" />
            Complete Audit Trail
          </span>
        </div>

        {/* CTA Buttons */}
        <div className="mt-8 flex items-center gap-3">
          <Link href="/planning">
            <Button size="lg" className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs sm:text-sm px-6 h-10 shadow-lg shadow-blue-500/20 font-semibold">
              Launch Application
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
          <Link href="/overview">
            <Button size="lg" variant="outline" className="border-[#1E2D4A] bg-[#111C30]/50 hover:bg-[#141F36] text-[#F8FAFC] text-xs sm:text-sm px-5 h-10 font-medium">
              <Play className="w-3.5 h-3.5 mr-2 fill-current" />
              Explore Corridor
            </Button>
          </Link>
        </div>

        {/* Interactive Corridor Visualizer */}
        <div className="mt-12 w-full bg-[#0F172A] border border-[#1E2D4A] rounded-xl overflow-hidden shadow-2xl relative">
          {/* Top Bar inside visualizer container */}
          <div className="px-4 py-2.5 bg-[#0B101C] border-b border-[#1E2D4A] flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
              <span className="font-semibold text-[#F8FAFC]">Northern Trunk Corridor (NDLS–CNB 440 km)</span>
              <span className="text-[11px] font-mono text-[#64748B] hidden sm:inline">• 24h CP-SAT Feasible Schedule</span>
            </div>
            <div className="text-[11px] text-[#94A3B8] font-mono flex items-center gap-2">
              <span className="text-[#3B82F6]">Live Interactive Simulation</span>
            </div>
          </div>

          {/* Canvas with Overlays */}
          <div className="h-[460px] w-full relative bg-[#080C14]">
            <RailwayCanvas
              corridor={DEMO_CORRIDOR}
              tasks={DEMO_TASKS}
              trains={DEMO_TRAINS}
              scheduleResult={DEMO_SCHEDULE_RESULT}
              selectedTaskId={selectedTaskId}
              selectedSectionCode={selectedSectionCode}
              selectedTrainId={selectedTrainId}
              onSelectTask={(id) => {
                setSelectedTaskId(id);
                setSelectedTrainId(null);
                const t = DEMO_TASKS.find((x) => x.task_id === id);
                if (t) setSelectedSectionCode(t.section_code || t.section_id || null);
              }}
              onSelectSection={(code) => {
                setSelectedSectionCode(code);
                const t = DEMO_TASKS.find((x) => x.section_code === code || x.section_id === code);
                if (t) setSelectedTaskId(t.task_id);
              }}
              onSelectTrain={(id) => {
                setSelectedTrainId(id);
                setSelectedTaskId(null);
              }}
            />

            {/* Contextual In-Scene Callout Overlays */}
            <div className="absolute top-12 left-6 z-20 pointer-events-none hidden sm:block">
              <div className="bg-[#0B101C]/90 backdrop-blur-md border border-[#2D436D] rounded-lg p-2.5 text-left text-xs shadow-xl min-w-[210px]">
                <div className="text-[10px] uppercase font-bold text-[#3B82F6] flex items-center justify-between">
                  <span>Train Rake 02073</span>
                  <span className="text-emerald-400">On Time</span>
                </div>
                <div className="text-white font-medium mt-0.5">Vande Bharat Express</div>
                <div className="text-[11px] text-[#94A3B8] mt-0.5 font-mono">
                  Scheduled: 14:20 – 16:10 UTC
                </div>
              </div>
            </div>

            <div className="absolute bottom-6 right-6 z-20 pointer-events-none hidden sm:block">
              <div className="bg-[#0B101C]/90 backdrop-blur-md border border-amber-500/40 rounded-lg p-2.5 text-left text-xs shadow-xl min-w-[220px]">
                <div className="text-[10px] uppercase font-bold text-amber-400 flex items-center justify-between">
                  <span>Maintenance Task TSK-0007</span>
                  <span className="text-rose-400 font-mono">Unplaced</span>
                </div>
                <div className="text-white font-medium mt-0.5">Track Regrading & Screening</div>
                <div className="text-[11px] text-[#94A3B8] mt-0.5 font-mono">
                  Section: SEC-12 (km 238.4 – 242.1)
                </div>
                <div className="text-[10px] text-amber-300 mt-1">
                  Blocked: High-density train traffic
                </div>
              </div>
            </div>
          </div>

          {/* Bottom 4 Metric Tiles */}
          <div className="grid grid-cols-2 md:grid-cols-4 border-t border-[#1E2D4A] divide-x divide-y md:divide-y-0 divide-[#1E2D4A] bg-[#0B101C]">
            <div className="p-4 text-left">
              <div className="flex items-center gap-1.5 text-xs text-[#94A3B8]">
                <Activity className="w-3.5 h-3.5 text-[#3B82F6]" />
                <span>Total Tasks (Demo)</span>
              </div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-[#F8FAFC]">82</span>
                <span className="text-[11px] font-semibold text-emerald-400 font-mono">+12%</span>
              </div>
            </div>

            <div className="p-4 text-left">
              <div className="flex items-center gap-1.5 text-xs text-[#94A3B8]">
                <Sliders className="w-3.5 h-3.5 text-[#3B82F6]" />
                <span>Active Scenarios</span>
              </div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-[#F8FAFC]">4</span>
                <span className="text-[11px] text-[#64748B] font-mono">72h Horizon</span>
              </div>
            </div>

            <div className="p-4 text-left">
              <div className="flex items-center gap-1.5 text-xs text-[#94A3B8]">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Plan Feasibility</span>
              </div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-emerald-400">98.6%</span>
                <span className="text-[11px] text-[#94A3B8] font-mono">Hard Rules Passed</span>
              </div>
            </div>

            <div className="p-4 text-left">
              <div className="flex items-center gap-1.5 text-xs text-[#94A3B8]">
                <Cpu className="w-3.5 h-3.5 text-sky-400" />
                <span>Validation Latency</span>
              </div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-bold font-mono text-[#F8FAFC]">&lt; 250ms</span>
                <span className="text-[11px] text-[#64748B] font-mono">12 Check Suite</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Product Architecture Section */}
      <section id="architecture" className="py-16 border-t border-[#1E2D4A] bg-[#0A0E17] px-6 lg:px-12">
        <div className="max-w-6xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <span className="text-xs uppercase text-[#3B82F6] tracking-wider font-bold">
              Engineering Governance
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#F8FAFC] mt-1.5">
              Five Inviolable Architecture Boundaries
            </h2>
            <p className="text-xs text-[#94A3B8] mt-2">
              Rules classify. Optimization schedules. Humans approve. AI explains.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            <div className="bg-[#0F172A] border border-[#1E2D4A] p-4 rounded-lg flex flex-col justify-between">
              <div>
                <div className="w-7 h-7 rounded bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400 mb-2.5">
                  <Sliders className="w-3.5 h-3.5" />
                </div>
                <h3 className="font-bold text-xs text-[#F8FAFC] mb-1">1. Rules Classify</h3>
                <p className="text-[11px] text-[#94A3B8] leading-relaxed">
                  Deterministic compatibility engine evaluates safety curfews, electrical isolation, and headway rules before optimization.
                </p>
              </div>
            </div>

            <div className="bg-[#0F172A] border border-[#1E2D4A] p-4 rounded-lg flex flex-col justify-between">
              <div>
                <div className="w-7 h-7 rounded bg-[#2563EB]/10 border border-[#2563EB]/30 flex items-center justify-center text-[#3B82F6] mb-2.5">
                  <Cpu className="w-3.5 h-3.5" />
                </div>
                <h3 className="font-bold text-xs text-[#F8FAFC] mb-1">2. Solver Schedules</h3>
                <p className="text-[11px] text-[#94A3B8] leading-relaxed">
                  Integer interval CP-SAT solver packs maintenance tasks into available traffic gaps with shadow possession bundling.
                </p>
              </div>
            </div>

            <div className="bg-[#0F172A] border border-[#1E2D4A] p-4 rounded-lg flex flex-col justify-between">
              <div>
                <div className="w-7 h-7 rounded bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-2.5">
                  <ShieldCheck className="w-3.5 h-3.5" />
                </div>
                <h3 className="font-bold text-xs text-[#F8FAFC] mb-1">3. Validator Verifies</h3>
                <p className="text-[11px] text-[#94A3B8] leading-relaxed">
                  The solver never self-certifies. A separate validation layer independently audits every interval against raw timetables.
                </p>
              </div>
            </div>

            <div className="bg-[#0F172A] border border-[#1E2D4A] p-4 rounded-lg flex flex-col justify-between">
              <div>
                <div className="w-7 h-7 rounded bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 mb-2.5">
                  <Lock className="w-3.5 h-3.5" />
                </div>
                <h3 className="font-bold text-xs text-[#F8FAFC] mb-1">4. Humans Approve</h3>
                <p className="text-[11px] text-[#94A3B8] leading-relaxed">
                  COMPLETED ≠ APPROVED. Divisional Railway Managers explicitly inspect and authorize every plan into an immutable audit ledger.
                </p>
              </div>
            </div>

            <div className="bg-[#0F172A] border border-[#1E2D4A] p-4 rounded-lg flex flex-col justify-between">
              <div>
                <div className="w-7 h-7 rounded bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 mb-2.5">
                  <Sparkles className="w-3.5 h-3.5" />
                </div>
                <h3 className="font-bold text-xs text-[#F8FAFC] mb-1">5. AI Explains</h3>
                <p className="text-[11px] text-[#94A3B8] leading-relaxed">
                  Read-only Copilot provides grounded operational explanations from verified diagnostic records without write access.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Footer */}
      <footer className="mt-auto border-t border-[#1E2D4A] bg-[#080C14] py-8 px-6 lg:px-12 text-xs text-[#64748B]">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <TrainTrack className="w-4 h-4 text-[#3B82F6]" />
            <span className="text-[#F8FAFC] font-semibold">TrackMeld Platform</span>
            <span>• Smart India Hackathon 2026 / CRIS Context</span>
          </div>

          <div className="flex items-center gap-5 text-xs text-[#94A3B8]">
            <Link href="/overview" className="hover:text-white transition-colors">Overview</Link>
            <Link href="/planning" className="hover:text-white transition-colors">Planning Workspace</Link>
            <Link href="/audit" className="hover:text-white transition-colors">Audit & Governance</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
