'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Bell,
  Search,
  ChevronDown,
  Menu,
} from 'lucide-react';
import { useSidebar } from '@/contexts/SidebarContext';
import { ResponsiveDrawer } from '@/components/common/ResponsiveDrawer';
import { AuthWidget } from '@/components/shell/AuthWidget';
import { CommandSearchOverlay } from '@/components/shell/CommandSearchOverlay';
import { NotificationDrawer } from '@/components/shell/NotificationDrawer';
import { TrackMeldEmblem } from '@/components/landing-3d/TrackMeldEmblem';

interface TopBarProps {
  activeScenarioId?: string;
  scenarioName?: string;
  planningHorizon?: string;
  onToggleSidebar?: () => void;
  isSidebarCollapsed?: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({
  activeScenarioId = 'SCN-DEMO-001',
  scenarioName = 'Northern Corridor',
  planningHorizon = '72-Hour Planning Horizon',
}) => {
  const { openMobile } = useSidebar();
  const [isScenarioDrawerOpen, setIsScenarioDrawerOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);

  // Global Ctrl+K / Cmd+K listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <>
      <header className="h-14 bg-[#070D18] border-b border-[#152238] px-3 sm:px-4 lg:px-5 flex items-center justify-between z-40 select-none shrink-0 font-sans">
        {/* ============================================================== */}
        {/* LEFT SECTION: Brand Identity (Emblem + Wordmark + v1.0 badge)  */}
        {/* ============================================================== */}
        <div className="flex items-center gap-3 shrink-0">
          <Link
            href="/"
            className="flex items-center gap-2.5 group shrink-0 outline-none focus-visible:ring-1 focus-visible:ring-[#38BDF8] rounded"
            title="TrackMeld Home"
          >
            <TrackMeldEmblem className="w-7 h-7 shrink-0 transition-transform group-hover:scale-105" />
            <span className="font-bold tracking-tight text-[#F8FAFC] text-[15px] group-hover:text-white transition-colors">
              TrackMeld
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-semibold hidden sm:inline">
              v1.0
            </span>
          </Link>
        </div>

        {/* ============================================================== */}
        {/* CENTER SECTION: Operational Context (Scenario, Corridor, Info) */}
        {/* ============================================================== */}
        <div className="flex items-center gap-2 sm:gap-3 min-w-0 mx-2 lg:mx-4">
          <div className="hidden sm:block h-4 w-[1px] bg-[#152238] shrink-0" />

          {/* Scenario Selector Trigger */}
          <button
            onClick={() => setIsScenarioDrawerOpen(true)}
            className="flex items-center gap-1.5 bg-[#0B1322] hover:bg-[#111A2E] border border-[#172640] hover:border-[#1E3A6B] rounded px-2.5 py-1 text-xs font-mono font-medium text-[#F8FAFC] transition-colors focus-visible:ring-1 focus-visible:ring-[#38BDF8] outline-none cursor-pointer shrink-0"
            title={`Active Scenario: ${activeScenarioId}`}
            aria-label={`Selected Scenario: ${activeScenarioId}`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0" />
            <span className="text-[#64748B] font-sans text-[11px] hidden md:inline">Scenario:</span>
            <span className="font-semibold text-[#38BDF8]">{activeScenarioId}</span>
            <ChevronDown className="w-3.5 h-3.5 text-[#64748B] shrink-0" />
          </button>

          {/* Secondary Operational Badges & Metadata */}
          <div className="hidden md:flex items-center gap-2 text-xs text-[#8EA3BE] truncate min-w-0 cursor-default">
            <span className="text-[#1E304E] shrink-0">/</span>
            <span className="truncate max-w-[160px] lg:max-w-[220px] text-[#CBD5E1] font-medium">
              {scenarioName}
            </span>
            <span className="text-[#1E304E] shrink-0">•</span>
            <span className="hidden xl:inline text-[11px] font-mono text-[#64748B]">
              {planningHorizon}
            </span>
            <span className="hidden xl:inline text-[#1E304E] shrink-0">•</span>
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] font-medium shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
              <span>Live Data (Synthetic)</span>
            </div>
          </div>
        </div>

        {/* ============================================================== */}
        {/* RIGHT SECTION: Global Actions & User Profile                   */}
        {/* ============================================================== */}
        <div className="flex items-center gap-2 sm:gap-3 text-xs shrink-0">
          {/* Global Search Command (Ctrl+K) */}
          <button
            onClick={() => setIsSearchOpen(true)}
            className="h-8 flex items-center justify-center md:justify-start gap-2 px-2 md:px-2.5 rounded bg-[#0B1322] hover:bg-[#111A2E] border border-[#172640] hover:border-[#1E3A6B] text-[#8EA3BE] hover:text-[#F8FAFC] transition-colors focus-visible:ring-1 focus-visible:ring-[#38BDF8] outline-none cursor-pointer shrink-0"
            title="Global Search (Ctrl+K)"
            aria-label="Global Search"
          >
            <Search className="w-3.5 h-3.5 text-[#38BDF8] shrink-0" />
            <span className="hidden md:inline text-xs">Search...</span>
            <kbd className="hidden lg:inline-block px-1.5 py-0.2 text-[9px] font-mono bg-[#111A2E] text-[#64748B] rounded border border-[#172640]">
              Ctrl K
            </kbd>
          </button>

          {/* Operational Notifications */}
          <button
            onClick={() => setIsNotificationOpen(true)}
            className="relative w-8 h-8 rounded-lg bg-[#0B1322] hover:bg-[#111A2E] border border-[#172640] hover:border-[#1E3A6B] text-[#8EA3BE] hover:text-[#F8FAFC] transition-colors flex items-center justify-center cursor-pointer shrink-0 focus-visible:ring-1 focus-visible:ring-[#38BDF8] outline-none"
            title="Operational Notifications"
            aria-label="Operational Notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-[#3B82F6] rounded-full ring-2 ring-[#070D18]" />
          </button>

          {/* Auth & Operator Profile Widget */}
          <div className="pl-1 sm:pl-2 border-l border-[#152238] flex items-center">
            <AuthWidget />
          </div>

          {/* Mobile Navigation Drawer Trigger */}
          <button
            onClick={openMobile}
            className="lg:hidden w-8 h-8 rounded-lg bg-[#0B1322] hover:bg-[#111A2E] border border-[#172640] text-[#8EA3BE] hover:text-[#F8FAFC] transition-colors flex items-center justify-center cursor-pointer shrink-0 focus-visible:ring-1 focus-visible:ring-[#38BDF8] outline-none"
            title="Open navigation menu"
            aria-label="Open navigation menu"
            aria-controls="railway-navigation-sidebar"
          >
            <Menu className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Scenario Switcher Drawer */}
      <ResponsiveDrawer
        isOpen={isScenarioDrawerOpen}
        onClose={() => setIsScenarioDrawerOpen(false)}
        title="Select Operational Scenario"
        subtitle="Synthetic Railway Corridor Simulations"
      >
        <div className="space-y-3 font-sans">
          <div className="p-3 bg-[#0B1322] rounded-lg border border-[#1E304E] cursor-pointer hover:border-[#38BDF8] transition-all">
            <div className="flex items-center justify-between mb-1">
              <span className="font-mono text-xs font-bold text-[#38BDF8]">SCN-DEMO-001</span>
              <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded font-mono font-bold">
                ACTIVE
              </span>
            </div>
            <div className="text-xs font-semibold text-[#F8FAFC]">Northern Corridor Baseline</div>
            <div className="text-[11px] text-[#8EA3BE] mt-1">
              440 km Trunk • 50 Trains • 30 Maintenance Tasks • 72h Horizon
            </div>
          </div>

          <div className="p-3 bg-[#070D18] rounded-lg border border-[#152238] opacity-60 cursor-not-allowed">
            <div className="flex items-center justify-between mb-1">
              <span className="font-mono text-xs font-semibold text-[#64748B]">SCN-STORM-002</span>
              <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-mono">
                ARCHIVED
              </span>
            </div>
            <div className="text-xs font-semibold text-[#94A3B8]">Severe Weather Disruption</div>
            <div className="text-[11px] text-[#64748B] mt-1">
              High-wind speeds at Yamuna Bridge • Synthetic scenario
            </div>
          </div>
        </div>
      </ResponsiveDrawer>

      <CommandSearchOverlay
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
      />

      <NotificationDrawer
        isOpen={isNotificationOpen}
        onClose={() => setIsNotificationOpen(false)}
      />
    </>
  );
};
