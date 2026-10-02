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

const NAV_ITEMS: NavItem[] = [
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
      aria-label="Main Navigation"
      className="w-56 bg-[#0E0E12] border-r border-[#202024] flex flex-col justify-between select-none shrink-0"
    >
      <div className="p-3">
        <div className="text-[10px] font-mono uppercase tracking-wider text-[#71717A] px-2.5 py-1 mb-1 font-semibold">
          Operations
        </div>
        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-[#18181C] text-[#F5F5F5] border border-[#29292F] shadow-sm'
                    : 'text-[#A1A1AA] hover:bg-[#141418] hover:text-[#F5F5F5]'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span className={isActive ? 'text-[#4C87E7]' : 'text-[#71717A]'}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-[#4C87E7]/20 text-[#4C87E7] font-semibold border border-[#4C87E7]/30">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <div className="mt-6 text-[10px] font-mono uppercase tracking-wider text-[#71717A] px-2.5 py-1 mb-1 font-semibold">
          Domain System
        </div>
        <div className="space-y-1 px-1">
          <div className="px-2 py-1.5 rounded bg-[#141418]/60 border border-[#202024] text-[11px] text-[#A1A1AA] font-mono">
            <div className="text-[#71717A] text-[9px]">SOLVER ENGINE</div>
            <div className="text-[#F5F5F5] font-semibold">CP-SAT v9.9</div>
            <div className="text-[10px] text-emerald-400 mt-0.5">Deterministic (Seed 42)</div>
          </div>
          <div className="px-2 py-1.5 rounded bg-[#141418]/60 border border-[#202024] text-[11px] text-[#A1A1AA] font-mono mt-2">
            <div className="text-[#71717A] text-[9px]">VALIDATION BOUNDARY</div>
            <div className="text-[#F5F5F5] font-semibold">Independent Validator</div>
            <div className="text-[10px] text-blue-400 mt-0.5">Hard Rules Verified</div>
          </div>
        </div>
      </div>

      {/* System Integrity Footer */}
      <div className="p-3 border-t border-[#202024] space-y-2">
        <div className="p-2.5 rounded bg-[#141418] border border-[#202024] text-[10px] font-mono text-[#71717A]">
          <div className="flex items-center justify-between text-[#A1A1AA] mb-1 font-semibold">
            <span>Core Boundary</span>
            <span className="text-amber-400">Strict</span>
          </div>
          <p className="leading-tight">
            Rules classify. Optimization schedules. Humans approve. AI explains.
          </p>
        </div>
      </div>
    </aside>
  );
};
