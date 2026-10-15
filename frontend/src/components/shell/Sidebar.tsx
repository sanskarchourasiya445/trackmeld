'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  CalendarRange,
  FileCheck2,
  Network,
  ClipboardList,
  ShieldCheck,
  Bot,
  X,
  TrainTrack,
} from 'lucide-react';
import { useSidebar } from '@/contexts/SidebarContext';

/**
 * Purpose-built directional toggle icon for railway sidebar navigation.
 * Renders an outline panel with internal navigation rail boundary (1.75px stroke)
 * and a directional chevron communicating collapsing or expanding.
 */
interface SidebarToggleIconProps {
  isCollapsed: boolean;
  className?: string;
}

const SidebarToggleIcon: React.FC<SidebarToggleIconProps> = ({
  isCollapsed,
  className = 'w-[18px] h-[18px]',
}) => {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <rect
        x="2"
        y="3"
        width="16"
        height="14"
        rx="2"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <line
        x1="7"
        y1="3"
        x2="7"
        y2="17"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      {isCollapsed ? (
        <path
          d="M11 7.5L13.5 10L11 12.5"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ) : (
        <path
          d="M13.5 7.5L11 10L13.5 12.5"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
};

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
  badgeVariant?: 'green' | 'red' | 'blue' | 'amber';
}

interface NavGroup {
  groupTitle: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    groupTitle: 'Operational Workspaces',
    items: [
      {
        label: 'Overview',
        href: '/overview',
        icon: <LayoutDashboard className="w-4 h-4 shrink-0" />,
      },
      {
        label: 'Planning Workspace',
        href: '/planning',
        icon: <CalendarRange className="w-4 h-4 shrink-0" />,
      },
      {
        label: 'Rail Network',
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
      },
      {
        label: 'Audit & Governance',
        href: '/audit',
        icon: <FileCheck2 className="w-4 h-4 shrink-0" />,
      },
      {
        label: 'Copilot',
        href: '/copilot',
        icon: <Bot className="w-4 h-4 shrink-0" />,
        badge: 'AI',
        badgeVariant: 'blue',
      },
    ],
  },
];

export interface SidebarProps {
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

  const checkIsActive = (href: string) => {
    const [path] = href.split('?');
    if (path === '/planning') {
      return pathname.startsWith('/planning');
    }
    return pathname === path;
  };

  const getBadgeClasses = (variant?: 'green' | 'red' | 'blue' | 'amber') => {
    switch (variant) {
      case 'green':
        return 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30';
      case 'red':
        return 'bg-rose-500/15 text-rose-400 border border-rose-500/30';
      case 'blue':
        return 'bg-blue-500/15 text-blue-400 border border-blue-500/30';
      case 'amber':
        return 'bg-amber-500/15 text-amber-400 border border-amber-500/30';
      default:
        return 'bg-slate-800 text-slate-300 border border-slate-700';
    }
  };

  return (
    <>
      {/* 1. Mobile/Tablet Backdrop Overlay (<lg screens) */}
      {isMobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/80 backdrop-blur-xs z-40 lg:hidden transition-opacity duration-200"
          aria-hidden="true"
        />
      )}

      {/* 2. Main Collapsible Sidebar Navigation */}
      <aside
        id="railway-navigation-sidebar"
        role="complementary"
        aria-label="Railway Operations Navigation"
        className={`fixed lg:static top-0 bottom-0 left-0 z-50 bg-[#070D18] border-r border-[#152238] flex flex-col justify-between select-none shrink-0 transition-[width,transform] duration-200 ease-in-out font-sans ${
          isMobileOpen
            ? 'translate-x-0 w-64 max-w-[85vw] shadow-2xl'
            : '-translate-x-full lg:translate-x-0'
        } ${
          isCollapsed ? 'lg:w-16' : 'lg:w-64'
        }`}
      >
        {/* TOP SECTION: Grouped Navigation Items */}
        <div className={`flex flex-col flex-1 min-h-0 ${isCollapsed ? 'overflow-visible' : 'overflow-y-auto overflow-x-hidden'}`}>
          {/* Mobile Header with close button */}
          <div className="lg:hidden px-3 pt-2.5 pb-1 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <span className="font-bold text-[#F8FAFC] text-sm tracking-tight">TrackMeld</span>
              <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-semibold">
                v1.0
              </span>
            </div>
            <button
              onClick={onCloseMobile}
              className="w-7 h-7 flex items-center justify-center text-[#94A3B8] hover:text-white rounded hover:bg-[#111A2E] transition-colors focus-visible:ring-1 focus-visible:ring-[#38BDF8] outline-none cursor-pointer"
              title="Close Navigation"
              aria-label="Close navigation menu"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className={`flex-1 ${isCollapsed ? 'py-2.5 px-1.5 space-y-3.5 overflow-visible' : 'py-2 px-2 space-y-3 overflow-y-auto'}`}>
            {NAV_GROUPS.map((group) => (
              <div key={group.groupTitle} className="space-y-0.5">
                {/* Section Header */}
                {!isCollapsed ? (
                  <div className="px-2 pt-1 pb-1">
                    <span className="text-[9.5px] font-mono uppercase font-bold text-[#4B6282] tracking-wider select-none">
                      {group.groupTitle}
                    </span>
                  </div>
                ) : (
                  <div className="h-2 w-full flex items-center justify-center">
                    <div className="w-4 h-[1px] bg-[#152238]" />
                  </div>
                )}

                {/* Items in this group */}
                <nav className="space-y-0.5" aria-label={group.groupTitle}>
                  {group.items.map((item) => {
                    const isActive = checkIsActive(item.href);

                    if (isCollapsed) {
                      return (
                        <div key={item.label} className="relative group flex justify-center">
                          <Link
                            href={item.href}
                            onClick={onCloseMobile}
                            title={item.label}
                            aria-label={item.label}
                            aria-current={isActive ? 'page' : undefined}
                            className={`relative flex items-center justify-center w-9 h-9 rounded-md transition-all focus-visible:ring-1 focus-visible:ring-[#38BDF8] outline-none ${
                              isActive
                                ? 'bg-[#101E35] text-[#38BDF8] border border-[#1E3A6B]/60 shadow-xs'
                                : 'text-[#8EA3BE] hover:text-[#F8FAFC] hover:bg-[#0D1627]'
                            }`}
                          >
                            {/* Active indicator dot */}
                            {isActive && (
                              <span className="absolute left-0 top-2 bottom-2 w-0.5 bg-[#38BDF8] rounded-r" />
                            )}

                            {/* Icon */}
                            {item.icon}

                            {/* Badge Indicator Dot */}
                            {item.badge && (
                              <span
                                className={`absolute top-1 right-1 w-1.5 h-1.5 rounded-full ${
                                  item.badgeVariant === 'green'
                                    ? 'bg-emerald-400'
                                    : item.badgeVariant === 'red'
                                    ? 'bg-rose-400'
                                    : 'bg-blue-400'
                                }`}
                              />
                            )}
                          </Link>

                          {/* Floating Tooltip */}
                          <div
                            role="tooltip"
                            className="absolute left-full top-1/2 -translate-y-1/2 ml-2 px-2.5 py-1 bg-[#0B1322] border border-[#1E304E] text-[#F8FAFC] text-[11px] font-medium rounded shadow-xl whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 flex items-center gap-2"
                          >
                            <span>{item.label}</span>
                            {item.badge && (
                              <span className={`text-[9px] font-mono px-1 py-0.2 rounded font-semibold ${getBadgeClasses(item.badgeVariant)}`}>
                                {item.badge}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    }

                    return (
                      <Link
                        key={item.label}
                        href={item.href}
                        onClick={onCloseMobile}
                        title={item.label}
                        aria-current={isActive ? 'page' : undefined}
                        className={`flex items-center justify-between h-8 px-2 rounded-md text-xs font-medium transition-all group focus-visible:ring-1 focus-visible:ring-[#38BDF8] outline-none ${
                          isActive
                            ? 'bg-[#101E35] text-[#38BDF8] border border-[#1E3A6B]/50 font-semibold shadow-xs'
                            : 'text-[#8EA3BE] hover:bg-[#0D1627] hover:text-[#F8FAFC] border border-transparent'
                        }`}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span
                            className={`transition-colors shrink-0 ${
                              isActive ? 'text-[#38BDF8]' : 'text-[#566B85] group-hover:text-[#8EA3BE]'
                            }`}
                          >
                            {item.icon}
                          </span>
                          <span className="truncate leading-none">{item.label}</span>
                        </div>

                        {item.badge && (
                          <span
                            className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold shrink-0 tracking-wider ${getBadgeClasses(
                              item.badgeVariant
                            )}`}
                          >
                            {item.badge}
                          </span>
                        )}
                      </Link>
                    );
                  })}
                </nav>
              </div>
            ))}
          </div>
        </div>

        {/* ============================================================== */}
        {/* FOOTER SECTION: ACTIVE SCENARIO & SIDEBAR TOGGLE               */}
        {/* ============================================================== */}
        <div className="shrink-0 border-t border-[#152238] bg-[#050A13]">
          {/* Active Scenario Card */}
          <div className={isCollapsed ? 'p-1.5 pt-2 pb-1.5 flex justify-center overflow-visible' : 'px-2 pt-2 pb-1.5'}>
            {isCollapsed ? (
              <div className="relative group flex justify-center">
                <Link
                  href="/planning"
                  onClick={onCloseMobile}
                  title="Active Corridor: NDLS → CNB (440 km Trunk)"
                  aria-label="Active Corridor: NDLS → CNB (440 km)"
                  className="flex flex-col items-center justify-center w-9 h-9 rounded-md bg-[#0A101D] hover:bg-[#111A2E] border border-[#152238] hover:border-[#1E304E] text-[#38BDF8] transition-colors focus-visible:ring-1 focus-visible:ring-[#38BDF8] outline-none"
                >
                  <TrainTrack className="w-3.5 h-3.5 text-[#38BDF8]" />
                  <span className="text-[7px] font-mono font-bold text-amber-400 mt-0.5">DEMO</span>
                </Link>

                <div
                  role="tooltip"
                  className="absolute left-full top-1/2 -translate-y-1/2 ml-2.5 px-2.5 py-1.5 bg-[#0B1322] border border-[#1E304E] text-[#F8FAFC] text-[11px] rounded-md shadow-2xl whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 font-mono"
                >
                  <div className="font-bold text-[#F8FAFC] flex items-center gap-2">
                    <span>NDLS → CNB</span>
                    <span className="text-[9px] font-mono text-amber-400 bg-amber-500/20 px-1 py-0.2 rounded border border-amber-500/40">
                      SYNTHETIC
                    </span>
                  </div>
                  <div className="text-[10px] text-[#8EA3BE] font-sans">440 km Trunk (SCN-DEMO-001)</div>
                </div>
              </div>
            ) : (
              <Link
                href="/planning"
                onClick={onCloseMobile}
                className="block p-2 rounded-md bg-[#0A101D] hover:bg-[#0F1728] border border-[#152238] hover:border-[#1E304E] transition-all group focus-visible:ring-1 focus-visible:ring-[#38BDF8] outline-none"
                title="Active Corridor: NDLS → CNB (440 km Trunk) • Synthetic Scenario"
                aria-label="Active Corridor: NDLS → CNB (440 km)"
              >
                <div className="flex items-center justify-between text-[8.5px] font-mono text-[#566B85] mb-1">
                  <span className="uppercase tracking-wider font-semibold text-[#8EA3BE]">Active Corridor</span>
                  <span className="text-amber-400 font-bold flex items-center gap-1 text-[8.5px] bg-amber-500/10 border border-amber-500/30 px-1.5 py-0.2 rounded">
                    SYNTHETIC
                  </span>
                </div>
                <div className="font-mono text-[11px] font-bold text-[#E2E8F0] group-hover:text-white transition-colors">
                  NDLS → CNB
                </div>
                <div className="text-[9.5px] text-[#8EA3BE] mt-0.5 truncate flex items-center justify-between">
                  <span>440 km Trunk (SCN-DEMO-001)</span>
                  <span className="text-[#566B85] font-mono text-xs">›</span>
                </div>
              </Link>
            )}
          </div>

          <div className="hidden lg:block mx-2 my-0.5 border-t border-[#152238]/60" />

          {/* Desktop Collapse / Expand Button */}
          <div className={`hidden lg:flex ${isCollapsed ? 'p-1.5 pt-1 pb-1.5 justify-center overflow-visible relative' : 'px-2 pt-1 pb-1.5'}`}>
            {isCollapsed ? (
              <div className="relative group flex justify-center">
                <button
                  type="button"
                  onClick={toggleCollapse}
                  className="w-9 h-9 rounded-md flex items-center justify-center text-[#8EA3BE] hover:text-[#38BDF8] hover:bg-[#0D1627] active:bg-[#112038] transition-colors focus-visible:ring-1 focus-visible:ring-[#38BDF8] outline-none cursor-pointer"
                  title="Expand sidebar · Ctrl+B"
                  aria-label="Expand sidebar navigation"
                  aria-expanded={false}
                  aria-controls="railway-navigation-sidebar"
                >
                  <SidebarToggleIcon
                    isCollapsed={true}
                    className="w-4 h-4 text-[#38BDF8]"
                  />
                </button>

                <div
                  role="tooltip"
                  className="absolute left-full top-1/2 -translate-y-1/2 ml-2.5 px-2.5 py-1 bg-[#0B1322] border border-[#1E304E] text-[#F8FAFC] text-[11px] font-medium rounded-md shadow-2xl whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 flex items-center gap-2"
                >
                  <span>Expand sidebar</span>
                  <span className="text-[#566B85] text-[10px]">·</span>
                  <kbd className="text-[9px] font-mono text-[#8EA3BE] bg-[#070D18] border border-[#152238] px-1 py-0.2 rounded">
                    Ctrl+B
                  </kbd>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={toggleCollapse}
                className="w-full h-8 px-2 rounded-md flex items-center justify-between text-xs font-medium text-[#8EA3BE] hover:text-[#F8FAFC] hover:bg-[#0D1627] active:bg-[#112038] transition-colors focus-visible:ring-1 focus-visible:ring-[#38BDF8] outline-none cursor-pointer group"
                title="Collapse sidebar (Ctrl+B)"
                aria-label="Collapse sidebar navigation"
                aria-expanded={true}
                aria-controls="railway-navigation-sidebar"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <SidebarToggleIcon
                    isCollapsed={false}
                    className="w-4 h-4 text-[#566B85] group-hover:text-[#38BDF8] transition-colors shrink-0"
                  />
                  <span className="truncate text-[#8EA3BE] group-hover:text-[#F8FAFC] transition-colors text-xs">
                    Collapse sidebar
                  </span>
                </div>
                <kbd className="text-[9px] font-mono text-[#566B85] group-hover:text-[#8EA3BE] bg-[#070D18] border border-[#152238] px-1.5 py-0.5 rounded shrink-0 transition-colors">
                  Ctrl+B
                </kbd>
              </button>
            )}
          </div>
        </div>
      </aside>
    </>
  );
};
