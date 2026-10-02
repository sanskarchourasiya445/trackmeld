'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  CalendarRange,
  FileCheck,
} from 'lucide-react';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
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
  },
];

const GOVERNANCE_ITEMS: NavItem[] = [
  {
    label: 'Audit & Governance',
    href: '/audit',
    icon: <FileCheck className="w-4 h-4" />,
  },
];

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  return (
    <aside
      aria-label="Operations Navigation"
      className="w-56 bg-[#0B101C] border-r border-[#1E2D4A] flex flex-col justify-between select-none shrink-0"
    >
      <div className="p-3">
        {/* Operations Section */}
        <div className="text-[10px] font-sans uppercase tracking-wider text-[#64748B] px-2.5 py-1 mb-1 font-bold">
          OPERATIONS
        </div>
        <nav className="space-y-1">
          {OPERATION_ITEMS.map((item) => {
            const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-[#141F36] text-[#F8FAFC] border border-[#2D436D] shadow-sm font-semibold'
                    : 'text-[#94A3B8] hover:bg-[#0F172A] hover:text-[#F8FAFC]'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span className={isActive ? 'text-[#3B82F6]' : 'text-[#64748B]'}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Governance Section */}
        <div className="mt-5 text-[10px] font-sans uppercase tracking-wider text-[#64748B] px-2.5 py-1 mb-1 font-bold">
          GOVERNANCE
        </div>
        <nav className="space-y-1">
          {GOVERNANCE_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-[#141F36] text-[#F8FAFC] border border-[#2D436D] shadow-sm font-semibold'
                    : 'text-[#94A3B8] hover:bg-[#0F172A] hover:text-[#F8FAFC]'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span className={isActive ? 'text-[#3B82F6]' : 'text-[#64748B]'}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </div>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Active Scenario Card Footer */}
      <div className="p-3 border-t border-[#1E2D4A]">
        <div className="p-2.5 rounded-md bg-[#0F172A] border border-[#1E2D4A] text-xs">
          <div className="text-[10px] uppercase font-bold text-[#64748B] tracking-wider mb-1 flex items-center justify-between">
            <span>Active Scenario</span>
            <span className="inline-flex items-center gap-1 text-[9px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded border border-emerald-500/30 font-medium">
              <span className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse"></span>
              Active
            </span>
          </div>
          <div className="font-mono text-xs font-bold text-[#F8FAFC]">
            SCN-DEMO-001
          </div>
          <div className="text-[11px] text-[#94A3B8] mt-0.5 truncate">
            Northern Corridor (440 km)
          </div>
        </div>
      </div>
    </aside>
  );
};

