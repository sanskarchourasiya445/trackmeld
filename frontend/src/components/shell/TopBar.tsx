'use client';

import React from 'react';
import Link from 'next/link';
import {
  TrainTrack,
  Play,
  CheckCircle,
  Clock,
  ShieldCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SyntheticDataBadge } from '@/components/common/SyntheticDataBadge';

interface TopBarProps {
  onTriggerSolve?: () => void;
  onOpenApproval?: () => void;
  isSolving?: boolean;
  canApprove?: boolean;
  activeScenarioId?: string;
}

export const TopBar: React.FC<TopBarProps> = ({
  onTriggerSolve,
  onOpenApproval,
  isSolving = false,
  canApprove = true,
  activeScenarioId = 'SCN-DEMO-001',
}) => {
  return (
    <header className="h-14 bg-[#0A0A0A] border-b border-[#202024] px-4 flex items-center justify-between z-30 select-none">
      {/* Brand & Context */}
      <div className="flex items-center gap-4">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded bg-[#18181C] border border-[#29292F] group-hover:border-[#4C87E7] transition-colors flex items-center justify-center">
            <TrainTrack className="w-4 h-4 text-[#4C87E7]" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-tight text-[#F5F5F5] text-sm group-hover:text-white transition-colors">
                TrackMeld
              </span>
              <span className="text-[10px] font-mono uppercase bg-[#18181C] text-[#4C87E7] px-1.5 py-0.2 rounded border border-[#29292F]">
                v0.10
              </span>
            </div>
            <span className="text-[10px] text-[#71717A] tracking-wider uppercase font-mono">
              Decision Support System
            </span>
          </div>
        </Link>

        <div className="h-4 w-[1px] bg-[#29292F] hidden sm:block" />

        {/* Active Scenario indicator */}
        <div className="hidden sm:flex items-center gap-2 text-xs">
          <span className="text-[#71717A] font-mono">SCENARIO:</span>
          <span className="font-mono text-xs font-semibold text-[#F5F5F5] bg-[#141418] border border-[#202024] px-2 py-0.5 rounded">
            {activeScenarioId}
          </span>
        </div>

        <SyntheticDataBadge size="sm" className="hidden lg:inline-flex" />
      </div>

      {/* Primary Actions & Controls */}
      <div className="flex items-center gap-2.5">
        <div className="hidden md:flex items-center gap-2 mr-2 text-xs font-mono text-[#A1A1AA]">
          <span className="flex items-center gap-1.5 bg-[#141418] px-2 py-1 rounded border border-[#202024]">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Validator: Verified</span>
          </span>
        </div>

        {onTriggerSolve && (
          <Button
            size="sm"
            onClick={onTriggerSolve}
            disabled={isSolving}
            className="bg-[#4C87E7] hover:bg-[#3B82F6] text-white font-mono text-xs shadow-none border-0"
          >
            {isSolving ? (
              <>
                <Clock className="w-3.5 h-3.5 animate-spin mr-1.5" />
                CP-SAT Solving...
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current mr-1.5" />
                Run CP-SAT
              </>
            )}
          </Button>
        )}

        {onOpenApproval && (
          <Button
            size="sm"
            variant="outline"
            onClick={onOpenApproval}
            disabled={!canApprove}
            className="border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10 font-mono text-xs"
          >
            <CheckCircle className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
            Human Review & Approve
          </Button>
        )}
      </div>
    </header>
  );
};
