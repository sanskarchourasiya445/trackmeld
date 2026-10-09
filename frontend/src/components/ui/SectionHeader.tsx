'use client';

import React from 'react';
import { LucideIcon } from 'lucide-react';

interface SectionHeaderProps {
  icon?: LucideIcon;
  title: string;
  badge?: string;
  badgeVariant?: 'blue' | 'green' | 'amber' | 'red';
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({
  icon: Icon,
  title,
  badge,
  badgeVariant = 'blue',
  subtitle,
  actions,
  className = '',
}) => {
  const getBadgeClass = () => {
    switch (badgeVariant) {
      case 'green':
        return 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40';
      case 'amber':
        return 'bg-amber-950/60 text-amber-400 border-amber-500/40';
      case 'red':
        return 'bg-rose-950/60 text-rose-400 border-rose-500/40';
      case 'blue':
      default:
        return 'bg-[#141F36] text-[#38BDF8] border-[#2D436D]';
    }
  };

  return (
    <div
      className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#0B101C] border border-[#1E2D4A] rounded-xl px-5 py-4 shrink-0 shadow-sm ${className}`}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2.5 flex-wrap">
          {Icon && <Icon className="w-5 h-5 text-[#38BDF8] shrink-0" />}
          <h1 className="text-lg font-bold text-[#F8FAFC] tracking-tight truncate">
            {title}
          </h1>
          {badge && (
            <span
              className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${getBadgeClass()}`}
            >
              {badge}
            </span>
          )}
        </div>
        {subtitle && (
          <p className="text-xs text-[#94A3B8] mt-1 leading-normal font-sans">
            {subtitle}
          </p>
        )}
      </div>

      {actions && (
        <div className="flex items-center gap-2.5 flex-wrap shrink-0">
          {actions}
        </div>
      )}
    </div>
  );
};
