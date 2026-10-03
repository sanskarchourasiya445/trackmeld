'use client';

import React from 'react';
import Link from 'next/link';
import {
  TrainTrack,
  Bell,
  ChevronDown,
  Menu,
} from 'lucide-react';

interface TopBarProps {
  activeScenarioId?: string;
  scenarioName?: string;
  planningHorizon?: string;
  userRole?: string;
  userName?: string;
  onToggleSidebar?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  activeScenarioId = 'SCN-DEMO-001',
  scenarioName = 'Northern Corridor',
  planningHorizon = '72-Hour Planning Horizon',
  userRole = 'Operations Officer',
  userName = 'Operator',
  onToggleSidebar,
}) => {
  return (
    <header className="h-14 bg-[#0A0E17] border-b border-[#1E2D4A] px-4 flex items-center justify-between z-30 select-none shrink-0 font-sans">
      {/* Left: Mobile Toggle + Brand + Scenario Selector */}
      <div className="flex items-center gap-4">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="lg:hidden p-1.5 rounded text-[#94A3B8] hover:text-white hover:bg-[#141F36] transition-colors"
            title="Toggle Sidebar"
          >
            <Menu className="w-4 h-4" />
          </button>
        )}

        {/* Logo & Version */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded bg-[#141F36] border border-[#2D436D] group-hover:border-[#3B82F6] transition-colors flex items-center justify-center">
            <TrainTrack className="w-4 h-4 text-[#3B82F6]" />
          </div>
          <div className="flex items-center gap-2">
            <span className="font-bold tracking-tight text-[#F8FAFC] text-sm group-hover:text-white transition-colors">
              TrackMeld
            </span>
            <span className="text-[10px] font-mono text-[#64748B] bg-[#141F36] px-1.5 py-0.2 rounded border border-[#1E2D4A]">
              v1.0
            </span>
          </div>
        </Link>

        {/* Vertical divider */}
        <div className="hidden md:block h-5 w-[1px] bg-[#1E2D4A]" />

        {/* Scenario Selector & Context (Desktop & Tablet) */}
        <div className="hidden sm:flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="text-[#64748B] text-[11px]">Scenario</span>
            <button className="flex items-center gap-1.5 bg-[#0F172A] hover:bg-[#141F36] border border-[#1E2D4A] rounded px-2.5 py-1 text-xs font-mono font-semibold text-[#F8FAFC] transition-colors">
              <span>{activeScenarioId}</span>
              <ChevronDown className="w-3 h-3 text-[#64748B]" />
            </button>
          </div>

          <div className="hidden lg:flex items-center gap-2 text-[#94A3B8] text-xs">
            <span>{scenarioName}</span>
            <span className="text-[#334155]">•</span>
            <span>{planningHorizon}</span>
            <span className="text-[#334155]">•</span>
            <span className="inline-flex items-center gap-1 text-emerald-400 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live Data (Synthetic)
            </span>
          </div>
        </div>
      </div>

      {/* Right: Notifications & User Profile */}
      <div className="flex items-center gap-3 text-xs">
        {/* Notification Bell */}
        <button
          className="relative text-[#94A3B8] hover:text-[#F8FAFC] p-1.5 rounded hover:bg-[#141F36] transition-colors"
          title="Operational Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-[#3B82F6] rounded-full" />
        </button>

        {/* User Profile Badge */}
        <div className="flex items-center gap-2 pl-2 border-l border-[#1E2D4A]">
          <div className="w-7 h-7 rounded bg-[#141F36] border border-[#2D436D] flex items-center justify-center text-[#F8FAFC] font-semibold text-[11px] font-mono">
            OP
          </div>
          <div className="hidden sm:flex flex-col text-left">
            <span className="text-xs font-semibold text-[#F8FAFC] leading-tight">
              {userName}
            </span>
            <span className="text-[10px] text-[#64748B] leading-tight">
              {userRole}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
