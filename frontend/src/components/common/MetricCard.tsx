import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  subtext?: string;
  delta?: {
    value: string;
    isPositive?: boolean;
    isNeutral?: boolean;
  };
  icon?: React.ReactNode;
  badge?: React.ReactNode;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  subtext,
  delta,
  icon,
  badge,
  className = '',
}) => {
  return (
    <div
      className={`bg-[#0F172A] border border-[#1E2D4A] hover:border-[#2D436D] transition-colors rounded-md p-3.5 flex flex-col justify-between ${className}`}
    >
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <span className="text-xs font-sans font-medium text-[#94A3B8] flex items-center gap-1.5">
          {icon}
          {label}
        </span>
        {badge}
      </div>

      <div className="flex items-baseline gap-1.5 my-0.5">
        <span className="text-2xl font-bold font-mono text-[#F8FAFC] tracking-tight tabular-nums">
          {value}
        </span>
        {unit && <span className="text-xs font-mono text-[#64748B]">{unit}</span>}
      </div>

      {(subtext || delta) && (
        <div className="mt-2 pt-2 border-t border-[#1E2D4A]/60 flex items-center justify-between text-[11px] text-[#64748B]">
          {subtext && <span className="font-sans text-[#94A3B8]">{subtext}</span>}
          {delta && (
            <span
              className={`font-mono text-[11px] font-semibold ${
                delta.isNeutral
                  ? 'text-[#94A3B8]'
                  : delta.isPositive
                  ? 'text-emerald-400'
                  : 'text-rose-400'
              }`}
            >
              {delta.value}
            </span>
          )}
        </div>
      )}
    </div>
  );
};
