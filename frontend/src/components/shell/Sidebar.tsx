'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  CalendarRange,
  Network,
  ClipboardList,
  ShieldCheck,
  Bot,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
  X,
  TrainTrack,
} from 'lucide-react';
import { useSidebar } from '@/contexts/SidebarContext';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
  badgeColor?: 'blue' | 'green' | 'amber' | 'red';
}

const PRIMARY_NAV_ITEMS: NavItem[] = [
  {
    label: 'Overview',
    href: '/overview',
    icon: <LayoutDashboard className="w-4 h-4 shrink-0" />,
  },
  {
    label: 'Planning',
    href: '/planning',
    icon: <CalendarRange className="w-4 h-4 shrink-0" />,
    badge: 'PRIMARY',
    badgeColor: 'blue',
  },
  {
    label: 'Network',
    href: '/network',
    icon: <Network className="w-4 h-4 shrink-0" />,
  },
  {
    label: 'Work Orders',
    href: '/work-orders',
    icon: <ClipboardList className="w-4 h-4 shrink-0" />,
  },
  {
    label: 'Validation & Governance',
    href: '/governance',
    icon: <ShieldCheck className="w-4 h-4 shrink-0" />,
    badge: '13 CHECKS',
    badgeColor: 'green',
  },
  {
    label: 'Copilot',
    href: '/copilot',
    icon: <Bot className="w-4 h-4 shrink-0" />,
    badge: 'READ-ONLY',
    badgeColor: 'blue',
  },
];

export interface SidebarProps {
  // Optional prop overrides (falls back to SidebarContext)
  isOpen?: boolean;
  onClose?: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen: propIsOpen,
  onClose: propOnClose,
  isCollapsed: propIsCollapsed,
  onToggleCollapse: propOnToggleCollapse,
}) => {
  const pathname = usePathname();
  const context = useSidebar();

  // Resolve state from props or context
  const isMobileOpen = propIsOpen !== undefined ? propIsOpen : context.isMobileOpen;
  const onCloseMobile = propOnClose || context.closeMobile;
  const isCollapsed = propIsCollapsed !== undefined ? propIsCollapsed : context.isCollapsed;
  const toggleCollapse = propOnToggleCollapse || context.toggleCollapse;

  // Close mobile drawer on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMobileOpen) {
        onCloseMobile();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMobileOpen, onCloseMobile]);

  return (
    <>
      {/* 1. Mobile/Tablet Backdrop Overlay (<lg screens) */}
      {isMobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/75 backdrop-blur-xs z-40 lg:hidden transition-opacity duration-200"
          aria-hidden="true"
        />
      )}

      {/* 2. Main Collapsible Sidebar Navigation */}
      <aside
        id="railway-navigation-sidebar"
        role="complementary"
        aria-label="Railway Operations Navigation"
        className={`fixed lg:static top-0 bottom-0 left-0 z-50 bg-[#0B101C] border-r border-[#1E2D4A] flex flex-col justify-between select-none shrink-0 transition-[width,transform] duration-200 ease-in-out font-sans ${
          /* Mobile behavior: off-canvas drawer */
          isMobileOpen
            ? 'translate-x-0 w-72 max-w-[85vw] shadow-2xl'
            : '-translate-x-full lg:translate-x-0'
        } ${
          /* Desktop behavior: expanded (w-64) vs collapsed icon rail (w-16) */
          isCollapsed ? 'lg:w-16' : 'lg:w-64'
        }`}
      >
        {/* TOP SECTION: Branding & Navigation */}
        <div className="flex flex-col flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
          {/* ============================================================== */}
          {/* HEADER: EXPANDED VS COLLAPSED                                  */}
          {/* ============================================================== */}
          {isCollapsed ? (
            /* COLLAPSED HEADER (Desktop Icon Rail) */
            <div className="hidden lg:flex flex-col items-center py-3.5 border-b border-[#1E2D4A] gap-2.5 shrink-0">
              <Link
                href="/"
                className="w-9 h-9 rounded-xl bg-[#141F36] border border-[#2D436D] hover:border-[#3B82F6] transition-colors flex items-center justify-center shadow-xs group"
                title="TrackMeld Homepage"
                aria-label="TrackMeld Homepage"
              >
                <TrainTrack className="w-4 h-4 text-[#38BDF8] group-hover:scale-110 transition-transform" />
              </Link>
              <button
                onClick={toggleCollapse}
                className="p-1.5 rounded-lg text-[#94A3B8] hover:text-[#38BDF8] hover:bg-[#141F36] border border-[#1E2D4A] hover:border-[#2D436D] transition-colors cursor-pointer"
                title="Expand sidebar (Ctrl+B)"
                aria-label="Expand sidebar navigation"
                aria-expanded="false"
                aria-controls="railway-navigation-sidebar"
              >
                <PanelLeftOpen className="w-4 h-4" />
              </button>
            </div>
          ) : (
            /* EXPANDED HEADER (Normal Desktop & Mobile Drawer) */
            <div className="p-4 pb-3 border-b border-[#1E2D4A] flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#141F36] border border-[#2D436D] flex items-center justify-center shadow-xs">
                  <TrainTrack className="w-4 h-4 text-[#38BDF8]" />
                </div>
                <div className="flex flex-col">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-bold text-[#F8FAFC] tracking-tight">
                      TrackMeld
                    </span>
                    <span className="text-[9px] font-mono text-[#38BDF8] bg-[#2563EB]/15 px-1 rounded border border-[#2563EB]/30 font-semibold">
                      OPS
                    </span>
                  </div>
                  <span className="text-[10px] text-[#64748B]">Railway Operations</span>
                </div>
              </div>

              {/* Collapse button on desktop / Close button on mobile */}
              <div className="flex items-center gap-1">
                <button
                  onClick={toggleCollapse}
                  className="hidden lg:flex p-1.5 rounded-lg text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#141F36] border border-transparent hover:border-[#1E2D4A] transition-colors cursor-pointer"
                  title="Collapse sidebar (Ctrl+B)"
                  aria-label="Collapse sidebar navigation"
                  aria-expanded="true"
                  aria-controls="railway-navigation-sidebar"
                >
                  <PanelLeftClose className="w-4 h-4" />
                </button>
                <button
                  onClick={onCloseMobile}
                  className="lg:hidden p-1.5 text-[#94A3B8] hover:text-white rounded-lg hover:bg-[#141F36]"
                  title="Close Navigation"
                  aria-label="Close navigation menu"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* ============================================================== */}
          {/* NAVIGATION ITEMS LIST                                          */}
          {/* ============================================================== */}
          <div className={`flex-1 py-3 ${isCollapsed ? 'px-2' : 'px-3'} overflow-y-auto`}>
            {!isCollapsed && (
              <div className="text-[10px] font-sans uppercase tracking-wider text-[#64748B] px-3 py-1 mb-2 font-bold flex items-center justify-between">
                <span>Operational Workspaces</span>
                <kbd className="hidden lg:inline-block text-[9px] font-mono text-[#475569] bg-[#0F172A] px-1 py-0.5 rounded border border-[#1E2D4A]">
                  Ctrl+B
                </kbd>
              </div>
            )}

            <nav className="space-y-1.5" aria-label="Workspaces">
              {PRIMARY_NAV_ITEMS.map((item) => {
                const isActive =
                  pathname === item.href ||
                  (item.href === '/governance' && (pathname === '/governance' || pathname === '/audit')) ||
                  (item.href === '/planning' && pathname.startsWith('/planning'));

                if (isCollapsed) {
                  /* COLLAPSED ICON RAIL ITEM */
                  return (
                    <div key={item.label} className="relative group flex justify-center">
                      <Link
                        href={item.href}
                        onClick={onCloseMobile}
                        title={`${item.label}${item.badge ? ` (${item.badge})` : ''}`}
                        aria-label={item.label}
                        className={`relative flex items-center justify-center w-10 h-10 rounded-xl transition-all ${
                          isActive
                            ? 'bg-[#141F36] text-[#38BDF8] border border-[#2D436D] shadow-xs'
                            : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#0F172A]'
                        }`}
                      >
                        {/* Active vertical accent bar */}
                        {isActive && (
                          <span className="absolute left-0 top-2 bottom-2 w-1 bg-[#38BDF8] rounded-r" />
                        )}

                        {/* Icon */}
                        {item.icon}

                        {/* Badge Indicator Dot */}
                        {item.badge && (
                          <span
                            className={`absolute top-1.5 right-1.5 w-2 h-2 rounded-full ring-2 ring-[#0B101C] ${
                              item.badgeColor === 'green'
                                ? 'bg-emerald-400'
                                : item.badgeColor === 'red'
                                ? 'bg-rose-400'
                                : 'bg-[#38BDF8]'
                            }`}
                          />
                        )}
                      </Link>

                      {/* Accessible Floating Hover Tooltip */}
                      <div
                        role="tooltip"
                        className="absolute left-full top-1/2 -translate-y-1/2 ml-3 px-3 py-1.5 bg-[#0F172A] border border-[#2D436D] text-[#F8FAFC] text-xs font-semibold rounded-lg shadow-2xl whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 flex items-center gap-2"
                      >
                        <span>{item.label}</span>
                        {item.badge && (
                          <span
                            className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold border ${
                              item.badgeColor === 'green'
                                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                                : item.badgeColor === 'red'
                                ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
                                : 'bg-[#2563EB]/20 text-[#38BDF8] border-[#2563EB]/40'
                            }`}
                          >
                            {item.badge}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                }

                /* EXPANDED NAV ITEM */
                return (
                  <Link
                    key={item.label}
                    href={item.href}
                    onClick={onCloseMobile}
                    title={item.label}
                    className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all group ${
                      isActive
                        ? 'bg-[#141F36] text-[#F8FAFC] border border-[#2D436D] shadow-xs font-semibold'
                        : 'text-[#94A3B8] hover:bg-[#0F172A] hover:text-[#F8FAFC]'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span
                        className={`transition-colors ${
                          isActive
                            ? 'text-[#38BDF8]'
                            : 'text-[#64748B] group-hover:text-[#94A3B8]'
                        }`}
                      >
                        {item.icon}
                      </span>
                      <span className="truncate">{item.label}</span>
                    </div>

                    {item.badge && (
                      <span
                        className={`text-[9px] font-mono px-2 py-0.5 rounded font-bold border shrink-0 ${
                          item.badgeColor === 'green'
                            ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                            : item.badgeColor === 'red'
                            ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                            : item.badgeColor === 'amber'
                            ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                            : 'bg-[#2563EB]/15 text-[#93C5FD] border-[#2563EB]/30'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>

        {/* ============================================================== */}
        {/* FOOTER SECTION: ACTIVE CORRIDOR TELEMETRY                      */}
        {/* ============================================================== */}
        <div className={`border-t border-[#1E2D4A] ${isCollapsed ? 'p-2 flex flex-col items-center' : 'p-3'}`}>
          {isCollapsed ? (
            /* COLLAPSED FOOTER (Compact Rail Icon + Tooltip) */
            <div className="relative group flex justify-center">
              <Link
                href="/planning"
                onClick={onCloseMobile}
                title="Active Corridor: NDLS → CNB (440 km Trunk) • OPTIMAL"
                aria-label="Active Corridor: NDLS → CNB (440 km Trunk)"
                className="flex flex-col items-center justify-center w-10 h-10 rounded-xl bg-[#0F172A] hover:bg-[#141F36] border border-[#1E2D4A] hover:border-[#2D436D] text-[#38BDF8] transition-colors"
              >
                <TrainTrack className="w-4 h-4 text-[#38BDF8]" />
                <span className="text-[8px] font-mono font-bold text-emerald-400 mt-0.5">440k</span>
              </Link>

              {/* Floating Tooltip */}
              <div
                role="tooltip"
                className="absolute left-full bottom-0 ml-3 px-3 py-2 bg-[#0F172A] border border-[#2D436D] text-[#F8FAFC] text-xs rounded-lg shadow-2xl whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50"
              >
                <div className="font-bold text-[#F8FAFC] flex items-center gap-2">
                  <span>NDLS → CNB</span>
                  <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/20 px-1 py-0.5 rounded border border-emerald-500/40">
                    OPTIMAL
                  </span>
                </div>
                <div className="text-[10px] text-[#94A3B8] mt-0.5">Northern Trunk (440 km)</div>
              </div>
            </div>
          ) : (
            /* EXPANDED FOOTER (Full Corridor Card) */
            <Link
              href="/planning"
              onClick={onCloseMobile}
              className="block p-3 rounded-lg bg-[#0F172A] hover:bg-[#141F36] border border-[#1E2D4A] hover:border-[#2D436D] text-xs transition-colors group"
            >
              <div className="text-[10px] uppercase font-bold text-[#64748B] tracking-wider mb-1.5 flex items-center justify-between">
                <span>Active Corridor</span>
                <span className="inline-flex items-center gap-1 text-[9px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/30 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  OPTIMAL
                </span>
              </div>
              <div className="font-mono text-xs font-bold text-[#F8FAFC] flex items-center justify-between">
                <span>NDLS → CNB</span>
                <ChevronRight className="w-3.5 h-3.5 text-[#64748B] group-hover:text-[#38BDF8] transition-colors" />
              </div>
              <div className="text-[11px] text-[#94A3B8] mt-0.5 truncate">
                Northern Trunk (440 km)
              </div>
            </Link>
          )}
        </div>
      </aside>
    </>
  );
};
