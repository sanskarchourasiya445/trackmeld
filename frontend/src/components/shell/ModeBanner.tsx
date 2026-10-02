import React from 'react';
import { AlertTriangle } from 'lucide-react';

export const ModeBanner: React.FC = () => {
  return (
    <aside
      aria-label="System Mode Notice"
      className="bg-[#141418] border-b border-amber-500/30 text-amber-200 px-4 py-1.5 text-xs flex items-center justify-between z-40 select-none"
    >
      <div className="flex items-center gap-2 overflow-hidden">
        <span className="flex items-center gap-1.5 font-mono font-bold tracking-wider uppercase text-[11px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded border border-amber-500/40 shrink-0">
          <AlertTriangle className="w-3 h-3 text-amber-400" />
          Prototype Verification Environment
        </span>
        <span className="text-[#A1A1AA] truncate text-[11px]">
          All train timetables, track possessions, and network constraints use synthetic CRIS demonstration data. Not connected to active train dispatch.
        </span>
      </div>

      <div className="hidden md:flex items-center gap-3 shrink-0 text-[11px] font-mono text-[#71717A]">
        <span>Corridor: <strong className="text-zinc-300">NDLS–CNB</strong> (440 km)</span>
        <span className="text-[#29292F]">|</span>
        <span className="flex items-center gap-1 text-emerald-400">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          Validator Engine Active
        </span>
      </div>
    </aside>
  );
};
