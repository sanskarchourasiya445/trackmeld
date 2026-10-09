'use client';

import React from 'react';
import { Train, AlertTriangle } from 'lucide-react';

/**
 * High-end 2.5D visual canvas fallback when WebGL is unavailable or reduced-motion is active.
 * Renders an architectural schematic view of the dual-track railway digital twin.
 */
export const FallbackRailwayCanvas: React.FC = () => {
  return (
    <div className="w-full h-full min-h-[550px] relative bg-[#04070D] flex flex-col justify-between p-6 sm:p-12 overflow-hidden border border-[#1E293B] rounded-xl shadow-2xl">
      {/* Background Grid Lines & Track Schematic */}
      <div className="absolute inset-0 opacity-15 bg-[radial-gradient(#38BDF8_1px,transparent_1px)] [background-size:24px_24px]"></div>

      {/* Track Schematic Graphic */}
      <div className="absolute inset-0 flex flex-col justify-center pointer-events-none px-6">
        {/* UP MAIN TRACK */}
        <div className="relative py-4 border-y border-[#38BDF8]/30">
          <div className="text-[10px] font-mono text-[#38BDF8] tracking-widest uppercase mb-1">
            LINE 01 — UP MAIN (130 km/h)
          </div>
          <div className="h-0.5 bg-gradient-to-r from-transparent via-[#38BDF8] to-transparent w-full"></div>
          {/* Animated Train Position */}
          <div className="absolute top-1/2 left-1/3 -translate-y-1/2 bg-[#0F172A] border border-[#2563EB] text-[#F1F5F9] px-3 py-1.5 rounded text-xs font-mono flex items-center gap-2 shadow-lg shadow-blue-500/20">
            <Train className="w-3.5 h-3.5 text-[#38BDF8]" />
            <span>EXPRESS-07 • ON TIME • km 14.2</span>
          </div>
        </div>

        {/* DOWN MAIN TRACK WITH POSSESSION */}
        <div className="relative py-8 border-b border-[#F59E0B]/30 mt-6">
          <div className="text-[10px] font-mono text-[#F59E0B] tracking-widest uppercase mb-1">
            LINE 02 — DOWN MAIN (MAINTENANCE POSSESSION S-04)
          </div>
          <div className="h-0.5 bg-gradient-to-r from-transparent via-[#F59E0B] to-transparent w-full"></div>
          {/* Possession Zone Box */}
          <div className="absolute top-1/2 right-1/4 -translate-y-1/2 bg-[#1C1405]/90 border border-[#F59E0B] text-[#FEF3C7] px-4 py-2 rounded text-xs font-mono shadow-xl">
            <div className="flex items-center gap-2 font-bold text-[#F59E0B]">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>POSSESSION WINDOW: 14:20 — 16:10 UTC</span>
            </div>
            <div className="text-[10px] text-[#D97706] mt-0.5">
              P-Way Tamping Machine • Traction Isolated • Validated
            </div>
          </div>
        </div>
      </div>

      {/* Top Status Banner */}
      <div className="relative z-10 flex items-center justify-between">
        <div className="flex items-center gap-2 font-mono text-xs text-[#94A3B8]">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>SCHEMATIC 2.5D TWIN VIEW</span>
          <span className="text-[#64748B] hidden sm:inline">• WebGL High-Performance Fallback</span>
        </div>
        <div className="font-mono text-xs text-[#38BDF8]">
          NDLS–GZB CORRIDOR
        </div>
      </div>

      {/* Bottom KPI Ticker in Fallback */}
      <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 gap-4 pt-6 border-t border-[#1E293B]">
        <div>
          <div className="text-[10px] font-mono text-[#64748B] uppercase">Schedule Status</div>
          <div className="text-sm font-bold text-emerald-400 font-mono">FEASIBLE (CP-SAT)</div>
        </div>
        <div>
          <div className="text-[10px] font-mono text-[#64748B] uppercase">Audit Firewall</div>
          <div className="text-sm font-bold text-[#F1F5F9] font-mono">13 CHECKS PASSED</div>
        </div>
        <div>
          <div className="text-[10px] font-mono text-[#64748B] uppercase">Traction Power</div>
          <div className="text-sm font-bold text-[#F59E0B] font-mono">ISOLATION SECURED</div>
        </div>
        <div>
          <div className="text-[10px] font-mono text-[#64748B] uppercase">Human Approval</div>
          <div className="text-sm font-bold text-[#38BDF8] font-mono">FOUR-EYES ENFORCED</div>
        </div>
      </div>
    </div>
  );
};
