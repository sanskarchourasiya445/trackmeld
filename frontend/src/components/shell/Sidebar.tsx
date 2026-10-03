'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  CalendarRange,
  FileCheck,
  GitBranch,
  Train,
  ClipboardList,
  Wrench,
  AlertTriangle,
  ShieldAlert,
  BarChart3,
  ChevronRight,
  X,
} from 'lucide-react';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
  badgeColor?: 'green' | 'red';
  isExternalOrStub?: boolean;
}

const OPERATION_ITEMS: NavItem[] = [
  {
    label: 'Overview',
    href: '/overview',
    icon: <LayoutDashboard className="w-4 h-4" />,
  },
  {
    label: 'Planning Workspace',
    href: '/planning',
    icon: <CalendarRange className="w-4 h-4" />,
    badge: 'LIVE',
    badgeColor: 'green',
  },
  {
    label: 'Audit & Governance',
    href: '/audit',
    icon: <FileCheck className="w-4 h-4" />,
  },
];

const DOMAIN_ITEMS: NavItem[] = [
  {
    label: 'Rail Network',
    href: '/planning?subtab=RAILWAY',
    icon: <GitBranch className="w-4 h-4" />,
  },
  {
    label: 'Rolling Stock',
    href: '/planning?subtab=TRAINS',
    icon: <Train className="w-4 h-4" />,
  },
  {
    label: 'Work Orders',
    href: '/planning?subtab=TASKS',
    icon: <ClipboardList className="w-4 h-4" />,
  },
  {
    label: 'Resources',
    href: '/planning?subtab=RESOURCES',
    icon: <Wrench className="w-4 h-4" />,
  },
];

const INTELLIGENCE_ITEMS: NavItem[] = [
  {
    label: 'Incidents & Alerts',
    href: '/planning?subtab=CONFLICTS',
    icon: <AlertTriangle className="w-4 h-4" />,
    badge: '2',
    badgeColor: 'red',
  },
  {
    label: 'Risk Intelligence',
    href: '/planning?subtab=VALIDATION',
    icon: <ShieldAlert className="w-4 h-4" />,
  },
  {
    label: 'Reports',
    href: '/planning?subtab=DIAGNOSTICS',
    icon: <BarChart3 className="w-4 h-4" />,
  },
];

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen = false, onClose }) => {
  const pathname = usePathname();

  const renderNavGroup = (title: string, items: NavItem[]) => (
    <div className="mb-3 lg:mb-2 xl:mb-4">
      <div className="text-[10px] font-sans uppercase tracking-wider text-[#64748B] px-3 py-1 mb-1 font-bold lg:hidden xl:block">
        {title}
      </div>
      {/* Icon-rail divider for laptop screens */}
      <div className="h-[1px] bg-[#1E2D4A]/60 my-2 mx-2 hidden lg:block xl:hidden" />
      <nav className="space-y-0.5">
        {items.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href.startsWith('/planning') && pathname === '/planning' && item.label === 'Planning Workspace');

          return (
            <Link
              key={item.label}
              href={item.href}
              onClick={onClose}
              title={item.label}
              className={`flex items-center justify-between px-3 py-1.5 rounded-md text-xs font-medium transition-all relative group ${
                isActive
                  ? 'bg-[#141F36] text-[#F8FAFC] border border-[#2D436D] shadow-xs font-semibold'
                  : 'text-[#94A3B8] hover:bg-[#0F172A] hover:text-[#F8FAFC]'
              }`}
            >
              <div className="flex items-center gap-2.5 lg:justify-center xl:justify-start w-full">
                <span className={`relative shrink-0 ${isActive ? 'text-[#3B82F6]' : 'text-[#64748B]'}`}>
                  {item.icon}
                  {/* Laptop icon-rail dot badge */}
                  {item.badge && (
                    <span
                      className={`hidden lg:block xl:hidden absolute -top-1 -right-1 w-2 h-2 rounded-full ${
                        item.badgeColor === 'red' ? 'bg-rose-500' : 'bg-emerald-500'
                      }`}
                    />
                  )}
                </span>
                <span className="lg:hidden xl:inline truncate">{item.label}</span>
              </div>

              {/* Full text badge for mobile and desktop */}
              {item.badge && (
                <span
                  className={`text-[9px] font-mono px-1.5 py-0.2 rounded font-bold border lg:hidden xl:inline shrink-0 ${
                    item.badgeColor === 'red'
                      ? 'bg-rose-500/20 text-rose-400 border-rose-500/30'
                      : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
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
  );

  return (
    <>
      {/* Mobile/Tablet Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 lg:hidden"
        />
      )}

      {/* Sidebar Container: w-64 on mobile drawer, w-16 on lg (icon rail), w-52 on xl, w-56 on 2xl */}
      <aside
        aria-label="Railway Operations Navigation"
        className={`fixed lg:static top-0 bottom-0 left-0 z-50 w-64 lg:w-16 xl:w-52 2xl:w-56 bg-[#0B101C] border-r border-[#1E2D4A] flex flex-col justify-between select-none shrink-0 transition-all duration-200 ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Navigation Content */}
        <div className="p-2 sm:p-3 overflow-y-auto">
          {/* Mobile close button */}
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-[#1E2D4A] lg:hidden">
            <span className="text-xs font-bold text-[#F8FAFC]">TrackMeld System</span>
            <button
              onClick={onClose}
              className="p-1 text-[#94A3B8] hover:text-white rounded"
              title="Close Navigation"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {renderNavGroup('OPERATIONS', OPERATION_ITEMS)}
          {renderNavGroup('DOMAIN SYSTEM', DOMAIN_ITEMS)}
          {renderNavGroup('INTELLIGENCE', INTELLIGENCE_ITEMS)}
        </div>

        {/* Bottom Active Scenario Card (Full on xl/2xl, icon/chip on lg) */}
        <div className="p-2 sm:p-3 border-t border-[#1E2D4A]">
          {/* Desktop/Mobile full card */}
          <Link
            href="/planning"
            onClick={onClose}
            className="block p-2.5 rounded-md bg-[#0F172A] hover:bg-[#141F36] border border-[#1E2D4A] text-xs transition-colors group lg:hidden xl:block"
          >
            <div className="text-[10px] uppercase font-bold text-[#64748B] tracking-wider mb-1 flex items-center justify-between">
              <span>Active Scenario</span>
              <span className="inline-flex items-center gap-1 text-[9px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded border border-emerald-500/30 font-medium">
                <span className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse" />
                ACTIVE
              </span>
            </div>
            <div className="font-mono text-xs font-bold text-[#F8FAFC] flex items-center justify-between">
              <span>SCN-DEMO-001</span>
              <ChevronRight className="w-3.5 h-3.5 text-[#64748B] group-hover:text-[#3B82F6] transition-colors" />
            </div>
            <div className="text-[11px] text-[#94A3B8] mt-0.5 truncate">
              Northern Corridor (440 km)
            </div>
          </Link>

          {/* Laptop icon-rail compact scenario indicator */}
          <Link
            href="/planning"
            onClick={onClose}
            title="Active Scenario: SCN-DEMO-001 (Northern Corridor)"
            className="hidden lg:flex xl:hidden flex-col items-center justify-center p-2 rounded-md bg-[#0F172A] hover:bg-[#141F36] border border-[#1E2D4A] text-[9px] font-mono text-[#F8FAFC] transition-colors text-center"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse mb-1" />
            <span className="font-bold text-[8.5px] text-[#93C5FD]">SCN</span>
          </Link>
        </div>
      </aside>
    </>
  );
};
