'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  TrainTrack,
  Bell,
  Search,
  ChevronDown,
  Menu,
} from 'lucide-react';
import { ResponsiveDrawer } from '@/components/common/ResponsiveDrawer';
import { AuthWidget } from '@/components/shell/AuthWidget';
import { CommandSearchOverlay } from '@/components/shell/CommandSearchOverlay';
import { NotificationDrawer } from '@/components/shell/NotificationDrawer';

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
  onToggleSidebar,
  isSidebarCollapsed = false,
}) => {
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
      <header className="h-14 bg-[#0A0E17] border-b border-[#1E2D4A] px-4 sm:px-6 flex items-center justify-between z-40 select-none shrink-0 font-sans">
        {/* Left: Sidebar Toggle + Brand + Scenario Context */}
        <div className="flex items-center gap-3 sm:gap-5 min-w-0">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="p-1.5 rounded-lg text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36] border border-transparent hover:border-[#1E2D4A] transition-colors shrink-0 cursor-pointer"
              title={
                isSidebarCollapsed
                  ? 'Expand sidebar navigation (Ctrl+B)'
                  : 'Collapse sidebar navigation (Ctrl+B)'
              }
              aria-label={
                isSidebarCollapsed
                  ? 'Expand sidebar navigation'
                  : 'Collapse sidebar navigation'
              }
              aria-expanded={!isSidebarCollapsed}
              aria-controls="railway-navigation-sidebar"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}

          {/* Logo & Platform Version */}
          <Link href="/" className="flex items-center gap-2.5 group shrink-0">
            <div className="w-8 h-8 rounded-lg bg-[#141F36] border border-[#2D436D] group-hover:border-[#3B82F6] transition-colors flex items-center justify-center shadow-xs">
              <TrainTrack className="w-4 h-4 text-[#38BDF8]" />
            </div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-tight text-[#F8FAFC] text-sm sm:text-base group-hover:text-white transition-colors">
                TrackMeld
              </span>
              <span className="text-[10px] font-mono text-[#64748B] bg-[#141F36] px-1.5 py-0.5 rounded border border-[#1E2D4A] hidden xs:inline">
                v1.0
              </span>
            </div>
          </Link>

          {/* Vertical divider */}
          <div className="hidden md:block h-5 w-[1px] bg-[#1E2D4A] shrink-0" />

          {/* Scenario Selector & Operational Context */}
          <div className="flex items-center gap-2.5 sm:gap-3.5 text-xs min-w-0">
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="text-[#64748B] text-[11px] font-medium hidden sm:inline">Scenario:</span>
              <button
                onClick={() => setIsScenarioDrawerOpen(true)}
                className="flex items-center gap-1.5 bg-[#0F172A] hover:bg-[#141F36] border border-[#1E2D4A] hover:border-[#2D436D] rounded-md px-2.5 py-1 text-xs font-mono font-semibold text-[#F8FAFC] transition-colors"
                title="View Scenario Details"
              >
                <span>{activeScenarioId}</span>
                <ChevronDown className="w-3.5 h-3.5 text-[#64748B] shrink-0" />
              </button>
            </div>

            {/* Desktop Full Context */}
            <div className="hidden xl:flex items-center gap-2.5 text-[#94A3B8] text-xs truncate font-sans">
              <span className="truncate font-medium text-[#CBD5E1]">{scenarioName}</span>
              <span className="text-[#334155]">•</span>
              <span className="shrink-0 font-mono text-[11px]">{planningHorizon}</span>
              <span className="text-[#334155]">•</span>
              <span className="inline-flex items-center gap-1.5 text-amber-400 font-medium shrink-0 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20 text-[11px]">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                Synthetic Demo Dataset
              </span>
            </div>

            {/* Laptop / Medium Screen Condensed Context */}
            <div className="hidden md:flex xl:hidden items-center gap-2 text-[#94A3B8] text-xs">
              <span className="truncate">{scenarioName}</span>
              <span className="text-[#334155]">•</span>
              <span className="text-amber-400 font-mono text-[10px] bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                SYNTHETIC
              </span>
            </div>
          </div>
        </div>

        {/* Right: Search, Notifications & User Profile */}
        <div className="flex items-center gap-2 sm:gap-3 text-xs shrink-0">
          {/* Quick Command / Search Button */}
          <button
            onClick={() => setIsSearchOpen(true)}
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[#0F172A] hover:bg-[#141F36] border border-[#1E2D4A] hover:border-[#2D436D] text-[#94A3B8] hover:text-[#F8FAFC] transition-colors"
            title="Global Search (Ctrl+K)"
            aria-label="Global Search"
          >
            <Search className="w-3.5 h-3.5 text-[#38BDF8]" />
            <span className="hidden sm:inline text-xs">Search corridor...</span>
            <kbd className="hidden md:inline-block px-1.5 py-0.5 text-[9px] font-mono bg-[#141F36] text-[#64748B] rounded border border-[#1E2D4A]">
              Ctrl K
            </kbd>
          </button>

          {/* Notification Bell */}
          <button
            onClick={() => setIsNotificationOpen(true)}
            className="relative text-[#94A3B8] hover:text-[#F8FAFC] p-2 rounded-lg hover:bg-[#141F36] transition-colors cursor-pointer"
            title="Operational Notifications"
            aria-label="Operational Notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-[#3B82F6] rounded-full ring-2 ring-[#0A0E17]" />
          </button>

          {/* Auth Status & Sign-In Widget */}
          <div className="pl-2 border-l border-[#1E2D4A]">
            <AuthWidget />
          </div>
        </div>
      </header>

      {/* Global Command / Search Palette */}
      <CommandSearchOverlay
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
      />

      {/* Operational Notifications Drawer */}
      <NotificationDrawer
        isOpen={isNotificationOpen}
        onClose={() => setIsNotificationOpen(false)}
      />

      {/* Scenario Context Drawer */}
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
        <div className="p-5 space-y-4 text-xs font-sans">
          <div className="bg-[#0A0E17] border border-[#1E2D4A] rounded-lg p-4 space-y-3 font-mono">
            <div>
              <span className="text-[10px] text-[#64748B] uppercase block font-bold">Scenario ID</span>
              <span className="text-sm font-bold text-[#F8FAFC]">{activeScenarioId}</span>
            </div>
            <div>
              <span className="text-[10px] text-[#64748B] uppercase block font-bold">Corridor Network</span>
              <span className="text-xs text-[#CBD5E1]">{scenarioName} (440 km Trunk Line)</span>
            </div>
            <div>
              <span className="text-[10px] text-[#64748B] uppercase block font-bold">Planning Horizon</span>
              <span className="text-xs text-[#CBD5E1]">{planningHorizon} (UTC)</span>
            </div>
            <div>
              <span className="text-[10px] text-[#64748B] uppercase block font-bold">Data Provenance</span>
              <span className="text-xs text-amber-400 flex items-center gap-1.5 pt-0.5">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                Synthetic Operational Seed (Demo Boundary)
              </span>
            </div>
          </div>

          <div className="border-t border-[#1E2D4A] pt-4 flex justify-end">
            <button
              onClick={() => setIsScenarioDrawerOpen(false)}
              className="px-4 py-2 bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-medium rounded-md text-xs transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </ResponsiveDrawer>
    </>
  );
};
