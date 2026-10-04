'use client';

import React from 'react';
import Link from 'next/link';
import {
  TrainTrack,
  Bell,
  ChevronDown,
  Menu,
} from 'lucide-react';
import { ResponsiveDrawer } from '@/components/common/ResponsiveDrawer';
import { AuthWidget } from '@/components/shell/AuthWidget';

interface TopBarProps {
  activeScenarioId?: string;
  scenarioName?: string;
  planningHorizon?: string;
  onToggleSidebar?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  activeScenarioId = 'SCN-DEMO-001',
  scenarioName = 'Northern Corridor',
  planningHorizon = '72-Hour Planning Horizon',
  onToggleSidebar,
}) => {
  const [isScenarioDrawerOpen, setIsScenarioDrawerOpen] = React.useState(false);

  return (
    <>
      <header className="h-14 bg-[#0A0E17] border-b border-[#1E2D4A] px-3 sm:px-4 flex items-center justify-between z-30 select-none shrink-0 font-sans">
        {/* Left: Mobile Toggle + Brand + Scenario Selector */}
        <div className="flex items-center gap-2.5 sm:gap-4 min-w-0">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="lg:hidden p-1.5 rounded text-[#94A3B8] hover:text-white hover:bg-[#141F36] transition-colors shrink-0"
              title="Toggle Navigation Menu"
              aria-label="Toggle navigation menu"
            >
              <Menu className="w-4 h-4" />
            </button>
          )}

          {/* Logo & Version */}
          <Link href="/" className="flex items-center gap-2 group shrink-0">
            <div className="w-7 h-7 rounded bg-[#141F36] border border-[#2D436D] group-hover:border-[#3B82F6] transition-colors flex items-center justify-center">
              <TrainTrack className="w-4 h-4 text-[#3B82F6]" />
            </div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold tracking-tight text-[#F8FAFC] text-sm group-hover:text-white transition-colors">
                TrackMeld
              </span>
              <span className="text-[10px] font-mono text-[#64748B] bg-[#141F36] px-1.5 py-0.2 rounded border border-[#1E2D4A] hidden xs:inline">
                v1.0
              </span>
            </div>
          </Link>

          {/* Vertical divider */}
          <div className="hidden md:block h-5 w-[1px] bg-[#1E2D4A] shrink-0" />

          {/* Scenario Selector & Context (Desktop & Tablet) */}
          <div className="flex items-center gap-2 sm:gap-3 text-xs min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-[#64748B] text-[11px] hidden sm:inline">Scenario</span>
              <button
                onClick={() => setIsScenarioDrawerOpen(true)}
                className="flex items-center gap-1 sm:gap-1.5 bg-[#0F172A] hover:bg-[#141F36] border border-[#1E2D4A] rounded px-2 sm:px-2.5 py-1 text-[11px] sm:text-xs font-mono font-semibold text-[#F8FAFC] transition-colors truncate"
                title="View Scenario Details"
              >
                <span className="truncate">{activeScenarioId}</span>
                <ChevronDown className="w-3 h-3 text-[#64748B] shrink-0" />
              </button>
            </div>

            {/* Desktop Context Details */}
            <div className="hidden xl:flex items-center gap-2 text-[#94A3B8] text-xs truncate">
              <span className="truncate">{scenarioName}</span>
              <span className="text-[#334155]">•</span>
              <span className="shrink-0">{planningHorizon}</span>
              <span className="text-[#334155]">•</span>
              <span className="inline-flex items-center gap-1 text-amber-400 font-medium shrink-0">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                Synthetic Demo Dataset
              </span>
            </div>

            {/* Laptop/Tablet Condensed Corridor */}
            <div className="hidden md:flex xl:hidden items-center gap-1.5 text-[#94A3B8] text-[11px]">
              <span className="truncate">{scenarioName}</span>
              <span className="text-[#334155]">•</span>
              <span className="text-amber-400 font-mono text-[10px]">SYNTHETIC</span>
            </div>
          </div>
        </div>

        {/* Right: Notifications & User Profile */}
        <div className="flex items-center gap-2 sm:gap-3 text-xs shrink-0">
          {/* Notification Bell */}
          <button
            className="relative text-[#94A3B8] hover:text-[#F8FAFC] p-1.5 rounded hover:bg-[#141F36] transition-colors"
            title="Operational Notifications"
            aria-label="Operational Notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-[#3B82F6] rounded-full" />
          </button>

          {/* Auth Status & Sign-In Widget */}
          <div className="pl-2 border-l border-[#1E2D4A]">
            <AuthWidget />
          </div>
        </div>
      </header>

      {/* Scenario Context Drawer (Available on all breakpoints) */}
      <ResponsiveDrawer
        isOpen={isScenarioDrawerOpen}
        onClose={() => setIsScenarioDrawerOpen(false)}
        title="Active Operational Scenario"
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">
            ACTIVE
          </span>
        }
      >
        <div className="p-4 space-y-4 text-xs font-sans">
          <div className="bg-[#0A0E17] border border-[#1E2D4A] rounded-lg p-3.5 space-y-2.5 font-mono">
            <div>
              <span className="text-[10px] text-[#64748B] uppercase block">Scenario ID</span>
              <span className="text-sm font-bold text-[#F8FAFC]">{activeScenarioId}</span>
            </div>
            <div>
              <span className="text-[10px] text-[#64748B] uppercase block">Corridor Network</span>
              <span className="text-xs text-[#CBD5E1]">{scenarioName} (440 km Trunk)</span>
            </div>
            <div>
              <span className="text-[10px] text-[#64748B] uppercase block">Planning Horizon</span>
              <span className="text-xs text-[#CBD5E1]">{planningHorizon} (UTC)</span>
            </div>
            <div>
              <span className="text-[10px] text-[#64748B] uppercase block">Data Provenance</span>
              <span className="text-xs text-amber-400 flex items-center gap-1.5 pt-0.5">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                Synthetic Operational Seed (Demo Boundary)
              </span>
            </div>
          </div>

          <div className="border-t border-[#1E2D4A] pt-3 flex justify-end">
            <button
              onClick={() => setIsScenarioDrawerOpen(false)}
              className="px-3 py-1.5 bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-medium rounded text-xs transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </ResponsiveDrawer>
    </>
  );
};
