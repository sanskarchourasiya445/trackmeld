'use client';

import React from 'react';
import Link from 'next/link';
import {
  TrainTrack,
  Play,
  CheckCircle,
  Clock,
  Bell,
  RefreshCw,
  User,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SyntheticDataBadge } from '@/components/common/SyntheticDataBadge';

interface TopBarProps {
  onTriggerSolve?: () => void;
  onOpenApproval?: () => void;
  isSolving?: boolean;
  canApprove?: boolean;
  activeScenarioId?: string;
  userRole?: string;
  userName?: string;
  onRefresh?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  onTriggerSolve,
  onOpenApproval,
  isSolving = false,
  canApprove = true,
  userRole = 'Operations Officer',
  userName = 'Operator',
  onRefresh,
}) => {
  return (
    <header className="h-13 bg-[#0B101C] border-b border-[#1E2D4A] px-4 flex items-center justify-between z-30 select-none shrink-0 font-sans">
      {/* Brand & Context */}
      <div className="flex items-center gap-3">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded bg-[#141F36] border border-[#2D436D] group-hover:border-[#3B82F6] transition-colors flex items-center justify-center">
            <TrainTrack className="w-3.5 h-3.5 text-[#3B82F6]" />
          </div>
          <div className="flex items-center gap-2">
            <span className="font-bold tracking-tight text-[#F8FAFC] text-sm group-hover:text-white transition-colors">
              TrackMeld
            </span>
            <span className="text-[10px] font-mono uppercase bg-[#141F36] text-[#94A3B8] px-1.5 py-0.2 rounded border border-[#1E2D4A]">
              v1.0
            </span>
          </div>
        </Link>
      </div>

      {/* Center Environment Indicator */}
      <div className="flex items-center gap-2">
        <SyntheticDataBadge size="sm" />
      </div>

      {/* Right Controls, User, & Actions */}
      <div className="flex items-center gap-3 text-xs">
        {onTriggerSolve && (
          <Button
            size="sm"
            onClick={onTriggerSolve}
            disabled={isSolving}
            className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs h-7 px-2.5 shadow-none border-0 font-medium"
          >
            {isSolving ? (
              <>
                <Clock className="w-3 h-3 animate-spin mr-1.5" />
                Solving...
              </>
            ) : (
              <>
                <Play className="w-3 h-3 fill-current mr-1.5" />
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
            className="border-emerald-600/40 text-emerald-400 hover:bg-emerald-950/40 text-xs h-7 px-2.5 font-medium"
          >
            <CheckCircle className="w-3 h-3 mr-1.5 text-emerald-400" />
            Governance
          </Button>
        )}

        {/* Notification Bell */}
        <button
          className="relative text-[#94A3B8] hover:text-[#F8FAFC] p-1.5 rounded hover:bg-[#141F36] transition-colors"
          title="Operational Notifications"
        >
          <Bell className="w-3.5 h-3.5" />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-[#3B82F6] rounded-full"></span>
        </button>

        {/* User Profile */}
        <div className="flex items-center gap-2 pl-2 border-l border-[#1E2D4A]">
          <div className="w-6 h-6 rounded-full bg-[#141F36] border border-[#2D436D] flex items-center justify-center text-[#3B82F6]">
            <User className="w-3.5 h-3.5" />
          </div>
          <div className="hidden sm:flex flex-col text-left">
            <span className="text-[11px] font-semibold text-[#F8FAFC] leading-tight">
              {userName}
            </span>
            <span className="text-[10px] text-[#64748B] leading-tight">
              {userRole}
            </span>
          </div>
        </div>

        {/* Refresh Button */}
        {onRefresh && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            className="border-[#1E2D4A] hover:bg-[#141F36] text-[#94A3B8] hover:text-white text-xs h-7 px-2 gap-1.5 font-sans"
          >
            <RefreshCw className="w-3 h-3" />
            <span className="hidden sm:inline">Refresh</span>
          </Button>
        )}
      </div>
    </header>
  );
};
