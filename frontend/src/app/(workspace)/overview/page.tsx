'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { MapLibreRailwayMap } from '@/components/map/MapLibreRailwayMap';
import { DigitalTwinInspectionModal } from '@/components/digital-twin/DigitalTwinInspectionModal';
import {
  getPlanVersions,
} from '@/lib/api/client';
import { PlanVersion, DataProvenance } from '@/types/planning';
import {
  ArrowRight,
  Clock,
  ShieldCheck,
  AlertTriangle,
  Activity,
  FileCheck,
  Eye,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EntityInspector } from '@/components/planning/EntityInspector';
import { ResponsiveDrawer } from '@/components/common/ResponsiveDrawer';

const SAMPLE_CONFLICT = {
  conflict_id: 'CONF-HDW-01',
  severity: 'CRITICAL' as const,
  title: 'Headway Buffer Violation: Express 12004 vs Freight 401',
  location: 'Block Section SEC-12 (Tundla – Etawah UP Mainline, km 242.0)',
  time_window: '14:20 – 16:10 UTC (Window overlap 18 min)',
  reason: 'Planned possession for Track Tamping (TSK-0007) reduces available headway margin to 3.2 min. Operational safety rule RULE-HDW-01 mandates minimum 7.0 min headway for high-speed express corridors.',
  impact_summary: '+14 min projected cumulative delay for trailing Express 12424',
  affected_trains: ['TR-12004 (Swarna Shatabdi)', 'TR-FRG-UP1 (Container Freight)'],
  affected_tasks: ['TSK-0007 (Switch Expansion Greasing)'],
  recommended_action: 'Shift possession window +45 minutes to 15:05–16:55 UTC via CP-SAT discrete optimization, eliminating headway overlap without cancelling work order.',
};

export default function OverviewPage() {
  const [selectedSectionCode, setSelectedSectionCode] = useState<string | null>('SEC-12');
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>('TSK-0007');
  const [isDigitalTwinOpen, setIsDigitalTwinOpen] = useState<boolean>(false);
  const [digitalTwinSection, setDigitalTwinSection] = useState<string>('SEC-12');
  const [isConflictDrawerOpen, setIsConflictDrawerOpen] = useState<boolean>(false);
  const [isMapFullScreen, setIsMapFullScreen] = useState<boolean>(false);
  const [lastUpdated] = useState('18 Oct 2026, 06:00 UTC');
  const [planVersion, setPlanVersion] = useState<PlanVersion | null>(null);
  const [provenance, setProvenance] = useState<DataProvenance>('synthetic');

  useEffect(() => {
    let cancelled = false;
    getPlanVersions('SCN-DEMO-001')
      .then((versions) => {
        if (!cancelled && versions && versions.length > 0) {
          setPlanVersion(versions[0]);
          setProvenance('backend');
        }
      })
      .catch(() => {
        // Retain synthetic demo state
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMapFullScreen) {
        setIsMapFullScreen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMapFullScreen]);

  const handleOpenDigitalTwin = (secCode: string) => {
    setDigitalTwinSection(secCode);
    setIsDigitalTwinOpen(true);
  };

  return (
    <>
      <div className="flex-1 overflow-y-auto p-3 sm:p-4 lg:p-5 space-y-3.5 max-w-[1920px] w-full mx-auto font-sans bg-[#070D18] select-none">
        {/* ============================================================== */}
        {/* 1. OPERATIONAL SITUATION BRIEFING HEADER                       */}
        {/* ============================================================== */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-[#1A263D]">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#162238] border border-[#2563EB]/40 flex items-center justify-center text-[#38BDF8] shadow-xs">
                <Activity className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h1 className="text-xl font-bold tracking-tight text-[#F8FAFC]">
                    Railway Operations Situation Briefing
                  </h1>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded font-medium ${
                      provenance === 'backend'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                    }`}
                  >
                    {provenance === 'backend'
                      ? 'AUTHORITATIVE SCENARIO • BACKEND DATA'
                      : 'DEMO SCENARIO • SYNTHETIC CORRIDOR MODEL'}
                  </span>
                </div>
                <p className="text-[11px] text-[#94A3B8] mt-0.5">
                  Northern Trunk Mainline (New Delhi to Kanpur Central, 440 km) • 24-Hour Planning Horizon
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <div className="bg-[#0B1120] border border-[#1A263D] rounded-md px-2.5 py-1 flex items-center gap-2 text-[11px] font-mono text-[#94A3B8]">
              <Clock className="w-3.5 h-3.5 text-[#38BDF8]" />
              <span>Planning Clock: <strong className="text-[#F8FAFC]">{lastUpdated}</strong></span>
            </div>

            <Link href="/planning">
              <Button size="sm" className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-semibold px-3 h-8 shadow-xs">
                <span>Enter Planning Workspace</span>
                <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
              </Button>
            </Link>
          </div>
        </div>

        {/* ============================================================== */}
        {/* 2. THE 4 CRITICAL SITUATIONAL QUESTIONS (SPACIOUS EXECUTIVE ROW) */}
        {/* ============================================================== */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-2.5">
          {/* Card 1: What is happening? */}
          <div className="bg-[#0B1120] border border-[#1A263D] rounded-lg p-3.5 shadow-xs space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-[10px] font-mono uppercase tracking-wider text-[#64748B] font-bold flex items-center gap-1.5">
                <Activity className="w-3 h-3 text-[#38BDF8]" />
                <span>1. WHAT IS HAPPENING?</span>
              </div>
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold">
                DEMO CORRIDOR
              </span>
            </div>
            <div>
              <div className="text-xl font-bold text-[#F8FAFC] tracking-tight">
                8 Possessions
              </div>
              <div className="text-[11px] font-mono text-[#38BDF8] font-semibold">
                Active on Corridor Today
              </div>
            </div>
            <p className="text-[11px] text-[#94A3B8] leading-relaxed">
              12 work zones mobilized across 440 km; 29 scheduled maintenance tasks executing within approved track windows.
            </p>
          </div>

          {/* Card 2: What needs attention? */}
          <div
            onClick={() => setIsConflictDrawerOpen(true)}
            className="bg-[#0B1120] border border-rose-500/40 hover:border-rose-400 rounded-lg p-3.5 shadow-xs space-y-2 cursor-pointer transition-colors group"
            title="Click to inspect simulated conflict in drawer"
          >
            <div className="flex items-center justify-between">
              <div className="text-[10px] font-mono uppercase tracking-wider text-rose-400 font-bold flex items-center gap-1.5">
                <AlertTriangle className="w-3 h-3 text-rose-400" />
                <span>2. WHAT NEEDS ATTENTION?</span>
              </div>
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/30 font-semibold">
                SIMULATED CONFLICT
              </span>
            </div>
            <div>
              <div className="text-xl font-bold text-rose-400 tracking-tight">
                1 Conflict
              </div>
              <div className="text-[11px] font-mono text-rose-300 font-semibold">
                SEC-12 Headway Compression
              </div>
            </div>
            <p className="text-[11px] text-[#CBD5E1] leading-relaxed">
              Task TSK-0007 requires 45m shift to clear Shatabdi Express 02073 minimum headway safety buffer.
            </p>
          </div>

          {/* Card 3: Is the plan feasible? */}
          <Link
            href="/governance"
            className="bg-[#0B1120] border border-emerald-500/40 hover:border-emerald-400 rounded-lg p-3.5 shadow-xs space-y-2 block transition-colors group"
            title="Click to view independent validation checks in Governance"
          >
            <div className="flex items-center justify-between">
              <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-bold flex items-center gap-1.5">
                <ShieldCheck className="w-3 h-3 text-emerald-400" />
                <span>3. IS THE PLAN SAFE?</span>
              </div>
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold">
                DEMO BASELINE
              </span>
            </div>
            <div>
              <div className="text-xl font-bold text-emerald-400 tracking-tight">
                0 Hard Violations
              </div>
              <div className="text-[11px] font-mono text-emerald-300 font-semibold">
                Candidate Feasibility
              </div>
            </div>
            <p className="text-[11px] text-[#94A3B8] leading-relaxed">
              Audit against modeled hard constraints in Governance view (0 breaches on baseline demo run).
            </p>
          </Link>

          {/* Card 4: What requires my decision? */}
          <Link
            href="/governance"
            className="bg-[#0B1120] border border-[#2563EB]/40 hover:border-[#38BDF8] rounded-lg p-3.5 shadow-xs space-y-2 block transition-colors group"
            title="Navigate to formal Four-Eyes governance workspace"
          >
            <div className="flex items-center justify-between">
              <div className="text-[10px] font-mono uppercase tracking-wider text-[#38BDF8] font-bold flex items-center gap-1.5">
                <FileCheck className="w-3 h-3 text-[#38BDF8]" />
                <span>4. DECISION REQUIRED</span>
              </div>
              <span className="text-[10px] font-mono text-[#38BDF8] opacity-0 group-hover:opacity-100 transition-opacity">
                GOVERNANCE →
              </span>
            </div>
            <div>
              <div className="text-xl font-bold text-[#F8FAFC] tracking-tight">
                Four-Eyes Review
              </div>
              <div className="text-[11px] font-mono text-[#38BDF8] font-semibold">
                {planVersion ? `PlanVersion v${planVersion.version_number} (${planVersion.status})` : 'PlanVersion 1 (Pending Review)'}
              </div>
            </div>
            <p className="text-[11px] text-[#94A3B8] leading-relaxed">
              Candidate schedule requires formal sign-off in the governance workspace by an authorized railway operations officer before track issuance.
            </p>
          </Link>
        </div>

        {/* ============================================================== */}
        {/* 3. CURRENT CORRIDOR STATE: LARGE SPATIAL VISUALIZATION         */}
        {/* ============================================================== */}
        <div
          className={`bg-[#0B1120] border border-[#1A263D] rounded-lg p-3 sm:p-4 flex flex-col shadow-xs space-y-2.5 transition-all ${
            isMapFullScreen ? 'fixed inset-0 z-50 rounded-none border-0 p-3 bg-[#070D18]' : ''
          }`}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-2.5 border-b border-[#1A263D]">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-sm text-[#F8FAFC]">
                  Corridor Topology & Network Map (Synthetic Prototype)
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#162238] text-[#38BDF8] border border-[#2563EB]/30">
                  NDLS → CNB (440 km)
                </span>
              </div>
              <p className="text-[11px] text-[#94A3B8] mt-0.5">
                Simulated timetable tracking: 50 scheduled train runs, 32 block sections, and 8 maintenance possessions
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleOpenDigitalTwin(selectedSectionCode || 'SEC-12')}
                className="text-xs border-[#1A263D] text-[#38BDF8] hover:bg-[#162238] hover:text-white h-7.5 px-2.5"
              >
                <Eye className="w-3.5 h-3.5 mr-1" />
                <span>3D Twin View</span>
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsMapFullScreen(!isMapFullScreen)}
                className="text-xs border-[#1A263D] text-[#94A3B8] hover:bg-[#162238] hover:text-white h-7.5 px-2.5"
                title={isMapFullScreen ? 'Exit Full Screen (Esc)' : 'Expand to Full Screen'}
              >
                {isMapFullScreen ? (
                  <>
                    <Minimize2 className="w-3.5 h-3.5 mr-1" />
                    <span>Exit Full Screen</span>
                  </>
                ) : (
                  <>
                    <Maximize2 className="w-3.5 h-3.5 mr-1" />
                    <span>Full Screen</span>
                  </>
                )}
              </Button>
              {!isMapFullScreen && (
                <Link href="/planning">
                  <Button size="sm" variant="ghost" className="text-xs text-[#38BDF8] hover:text-white h-7.5 px-2.5">
                    <span>Interactive Workspace</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-1" />
                  </Button>
                </Link>
              )}
            </div>
          </div>

          {/* Large Map Workspace */}
          <div
            className={`w-full rounded-md overflow-hidden border border-[#1A263D] relative ${
              isMapFullScreen ? 'flex-1 min-h-0' : 'h-[360px] sm:h-[400px] lg:h-[450px]'
            }`}
          >
            <MapLibreRailwayMap
              selectedSectionCode={selectedSectionCode}
              selectedTaskId={selectedTaskId}
              onSelectSection={setSelectedSectionCode}
              onSelectTask={setSelectedTaskId}
              onOpenDigitalTwin={handleOpenDigitalTwin}
            />
          </div>
        </div>

        {/* ============================================================== */}
        {/* 4. ATTENTION REQUIRED & DECISION ACTION CENTER                 */}
        {/* ============================================================== */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5">
          {/* Left: CP-SAT Optimization vs Baseline Metrics */}
          <div className="lg:col-span-6 bg-[#0B1120] border border-[#1A263D] rounded-lg p-3.5 sm:p-4 shadow-xs space-y-3">
            <div className="flex items-center justify-between pb-2.5 border-b border-[#1A263D]">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-xs text-[#F8FAFC]">
                    CP-SAT Optimization vs Manual Baseline
                  </h3>
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold">
                    SYNTHETIC BENCHMARK
                  </span>
                </div>
                <p className="text-[10px] text-[#94A3B8] mt-0.5">
                  Comparison against priority-greedy dispatch rules
                </p>
              </div>
              <div className="flex items-center gap-2.5 text-xs font-mono">
                <span className="text-[#38BDF8] flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-[#38BDF8]" />
                  CP-SAT
                </span>
                <span className="text-emerald-400 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  Baseline
                </span>
              </div>
            </div>

            <div className="space-y-3 text-xs font-sans">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-[#94A3B8]">Requisition Coverage</span>
                  <span className="font-mono font-bold text-[#F8FAFC]">96.7% vs 80.0%</span>
                </div>
                <div className="grid grid-cols-2 gap-2 h-2">
                  <div className="bg-[#162238] rounded-full overflow-hidden">
                    <div className="bg-[#2563EB] h-full rounded-full" style={{ width: '96.7%' }} />
                  </div>
                  <div className="bg-[#162238] rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full rounded-full" style={{ width: '80%' }} />
                  </div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-[#94A3B8]">Express Train Delay Minutes</span>
                  <span className="font-mono font-bold text-[#F8FAFC]">+11m vs +68m</span>
                </div>
                <div className="grid grid-cols-2 gap-2 h-2">
                  <div className="bg-[#162238] rounded-full overflow-hidden">
                    <div className="bg-[#2563EB] h-full rounded-full" style={{ width: '16%' }} />
                  </div>
                  <div className="bg-[#162238] rounded-full overflow-hidden">
                    <div className="bg-rose-500 h-full rounded-full" style={{ width: '85%' }} />
                  </div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-[#94A3B8]">Headway Margin Violations</span>
                  <span className="font-mono font-bold text-emerald-400">0 vs 4</span>
                </div>
                <div className="grid grid-cols-2 gap-2 h-2">
                  <div className="bg-[#162238] rounded-full overflow-hidden">
                    <div className="bg-emerald-500 h-full rounded-full" style={{ width: '100%' }} />
                  </div>
                  <div className="bg-[#162238] rounded-full overflow-hidden">
                    <div className="bg-rose-500 h-full rounded-full" style={{ width: '30%' }} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Urgent Decisions Required */}
          <div className="lg:col-span-6 bg-[#0B1120] border border-[#1A263D] rounded-lg p-3.5 sm:p-4 shadow-xs space-y-3">
            <div className="flex items-center justify-between pb-2.5 border-b border-[#1A263D]">
              <div>
                <h3 className="font-bold text-xs text-[#F8FAFC]">
                  Pending Operational Decisions
                </h3>
                <p className="text-[10px] text-[#94A3B8] mt-0.5">
                  Actions requiring human approval before issuance
                </p>
              </div>
              <span className="text-[10px] font-mono text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-500/30 font-semibold">
                1 ACTION REQUIRED (SYNTHETIC)
              </span>
            </div>

            <div className="space-y-2.5 font-sans">
              <div className="bg-[#070D18] border border-[#1A263D] hover:border-[#2563EB]/40 rounded-lg p-3 flex items-center justify-between gap-3 transition-colors">
                <div className="space-y-0.5">
                  <span className="font-semibold text-xs text-[#F8FAFC] block">
                    Perform Four-Eyes Sign-Off on {planVersion ? `PlanVersion v${planVersion.version_number}` : 'PlanVersion 1 (Candidate)'}
                  </span>
                  <p className="text-[10.5px] text-[#94A3B8] leading-normal">
                    Candidate schedule • Subject to independent governance verification
                  </p>
                </div>
                <Link href="/governance" className="shrink-0">
                  <Button size="sm" className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs h-7.5 px-3 font-semibold">
                    Sign Off
                  </Button>
                </Link>
              </div>

              <div className="bg-[#070D18] border border-[#1A263D] hover:border-[#2563EB]/40 rounded-lg p-3 flex items-center justify-between gap-3 transition-colors">
                <div className="space-y-0.5">
                  <span className="font-semibold text-xs text-[#F8FAFC] block">
                    Resolve Headway Conflict at SEC-12 (TSK-0007)
                  </span>
                  <p className="text-[10.5px] text-[#94A3B8] leading-normal">
                    Shift possession slot +45m to clear Shatabdi 02073 margin
                  </p>
                </div>
                <Link href="/planning?subtab=CONFLICTS" className="shrink-0">
                  <Button size="sm" variant="outline" className="border-[#1A263D] text-[#38BDF8] hover:bg-[#162238] text-xs h-7.5 px-3 font-semibold">
                    Resolve
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Contextual Conflict Drawer */}
      <ResponsiveDrawer
        isOpen={isConflictDrawerOpen}
        onClose={() => setIsConflictDrawerOpen(false)}
        title="Active Operational Conflict"
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-bold border border-rose-500/40">
            CRITICAL
          </span>
        }
        maxWidth="max-w-md"
      >
        <div className="h-full">
          <EntityInspector
            selectedConflict={SAMPLE_CONFLICT}
            onClose={() => setIsConflictDrawerOpen(false)}
            onOpenDigitalTwin={handleOpenDigitalTwin}
            isDrawer
          />
        </div>
      </ResponsiveDrawer>

      {/* 3D Digital Twin Modal */}
      <DigitalTwinInspectionModal
        isOpen={isDigitalTwinOpen}
        onClose={() => setIsDigitalTwinOpen(false)}
        sectionCode={digitalTwinSection}
        sectionName="Northern Trunk Section"
        kmRange="km 209.0 – 301.0"
        workOrderTitle="Section Track Geometry & Catenary Digital Twin"
      />
    </>
  );
}
