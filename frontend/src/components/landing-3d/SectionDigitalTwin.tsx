'use client';

import React, { useState } from 'react';
import { Network, Activity, Zap, HardHat, ChevronRight } from 'lucide-react';

export const SectionDigitalTwin: React.FC = () => {
  const [activeLayer, setActiveLayer] = useState<number>(0);

  const layers = [
    {
      title: 'Meso-Topology Graph',
      tag: '132 TRACKS • 264 ENDPOINTS',
      desc: 'Physical track segments mapped down to explicit start/end boundary joints, station throats, and turnout connections. Zero inferred connectivity.',
      code: 'MODEL: Phase 16I-C Explicit Graph\nNODES: Station Throats & Boundary Joints\nTURNOUTS: CONTINUITY / TURNOUT_NORMAL / CROSSOVER\nTRACKS: UP_MAIN, DOWN_MAIN, LOOP',
      icon: Network,
    },
    {
      title: 'Physical Train Traversals',
      tag: 'DETERMINISTIC ROUTING',
      desc: 'Commercial timetable station-to-station movements resolved into explicit physical running line hops. Ambiguous paths fail safe rather than guessing track assignments.',
      code: 'RESOLUTION: EXPANDED_ROUTE\nTRAIN: 12004 (Shatabdi Express)\nSECTION: SEC-NDLS-GZB (km 0.0 — 28.6)\nTRACK_ID: TRK-NDLS-GZB-UP (Broad Gauge 1.676m)',
      icon: Activity,
    },
    {
      title: 'Traction Power & OHE Grid',
      tag: '25 kV AC ELECTRIFICATION',
      desc: 'Overhead electrical equipment sectors, feeder circuit breakers, and earthing isolations directly linked to maintenance possession clearance gates.',
      code: 'SECTOR: OHE-FS-02 (Ghaziabad Feeder)\nVOLTAGE: 25.4 kV AC 50Hz\nISOLATION STATUS: DE-ENERGIZED & EARTHED\nPERMIT: PTW-2026-8819 (Active Clearance)',
      icon: Zap,
    },
    {
      title: 'Maintenance Possession Envelopes',
      tag: 'TEMPORAL & SPATIAL BUFFERS',
      desc: 'Work requisitions parameterized with physical duration, mandatory setup/teardown buffers, and adjacent-track clearance hazard requirements.',
      code: 'TASK: TSK-0007 (Track Regrading)\nWINDOW: 14:20 — 16:10 UTC (Duration: 90m)\nBUFFERS: +10m Before / +10m After\nADJACENT IMPACT: CAUTION_ORDER (45 km/h limit)',
      icon: HardHat,
    },
  ];

  return (
    <section id="digital-twin" className="py-24 sm:py-32 px-6 sm:px-12 lg:px-20 border-t border-[#1E293B] bg-[#060A13]">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="max-w-3xl">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#38BDF8] font-bold">
            01 / INFRASTRUCTURE DIGITIZATION
          </div>
          <h2 className="mt-2 text-3xl sm:text-5xl font-extrabold tracking-tight text-[#F8FAFC]">
            THE RAILWAY,
            <br />
            <span className="text-[#38BDF8]">DIGITIZED.</span>
          </h2>
          <p className="mt-4 text-base sm:text-lg text-[#94A3B8] leading-relaxed">
            TrackMeld turns physical railway infrastructure, train movements, maintenance tasks, and operational constraints into one unified, auditable digital-twin environment.
          </p>
        </div>

        {/* Interactive 4-Layer Architecture Inspector */}
        <div className="mt-16 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Layer Selector Column (Left) */}
          <div className="lg:col-span-6 space-y-3">
            {layers.map((layer, idx) => {
              const Icon = layer.icon;
              const isActive = activeLayer === idx;
              return (
                <div
                  key={idx}
                  onClick={() => setActiveLayer(idx)}
                  className={`p-5 rounded-xl border transition-all cursor-pointer ${
                    isActive
                      ? 'bg-[#0B1220] border-[#2563EB] shadow-xl shadow-blue-900/20 translate-x-1'
                      : 'bg-[#080D18]/70 border-[#1E293B] hover:border-[#38BDF8]/40 hover:bg-[#0A101C]'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${
                          isActive
                            ? 'bg-[#2563EB] text-white shadow-md'
                            : 'bg-[#111A2E] text-[#64748B]'
                        }`}
                      >
                        <Icon className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="font-mono text-[10px] uppercase font-bold text-[#38BDF8] tracking-wider">
                          {layer.tag}
                        </div>
                        <h3 className="font-bold text-base text-[#F1F5F9] mt-0.5">
                          {layer.title}
                        </h3>
                      </div>
                    </div>
                    <ChevronRight
                      className={`w-4 h-4 mt-2 transition-transform text-[#64748B] ${
                        isActive ? 'rotate-90 text-[#38BDF8]' : ''
                      }`}
                    />
                  </div>
                  <p className="mt-3 text-xs sm:text-sm text-[#94A3B8] leading-relaxed pl-12">
                    {layer.desc}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Real-time Telemetry Data Window (Right) */}
          <div className="lg:col-span-6 sticky top-24">
            <div className="rounded-xl border border-[#1E293B] bg-[#04070D] p-6 shadow-2xl overflow-hidden relative">
              {/* Top Terminal Bar */}
              <div className="flex items-center justify-between pb-4 border-b border-[#1E293B] text-xs font-mono text-[#64748B]">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  <span className="text-[#F1F5F9] font-bold">DIGITAL TWIN TELEMETRY STREAM</span>
                </div>
                <span>NODE: NDLS-GZB-CORE</span>
              </div>

              {/* Active Layer Details */}
              <div className="mt-6">
                <div className="text-xs font-mono text-[#38BDF8] uppercase tracking-wider font-bold">
                  {layers[activeLayer].title}
                </div>
                <div className="text-xl font-bold text-[#F8FAFC] mt-1">
                  {layers[activeLayer].tag}
                </div>
                <p className="text-xs sm:text-sm text-[#94A3B8] mt-2 leading-relaxed">
                  {layers[activeLayer].desc}
                </p>
              </div>

              {/* Monospace Telemetry Box */}
              <div className="mt-6 bg-[#080D1A] border border-[#1E293B] rounded-lg p-4 font-mono text-xs text-[#38BDF8] whitespace-pre leading-relaxed shadow-inner">
                {layers[activeLayer].code}
              </div>

              {/* Bottom Verification Status */}
              <div className="mt-6 pt-4 border-t border-[#1E293B] flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono text-[#64748B]">
                <span className="text-emerald-400 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  GRAPH INTEGRITY: 100% EXPLICIT
                </span>
                <span>PROVENANCE: PHASE 16I-C</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
