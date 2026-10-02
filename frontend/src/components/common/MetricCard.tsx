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
      className={`bg-[#141418] border border-[#202024] hover:border-[#29292F] transition-colors rounded-md p-4 flex flex-col justify-between ${className}`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-mono uppercase tracking-wider text-[#A1A1AA] flex items-center gap-1.5">
          {icon}
          {label}
        </span>
        {badge}
      </div>

      <div className="flex items-baseline gap-1.5">
        <span className="text-2xl font-bold font-mono text-[#F5F5F5] tracking-tight tabular-nums">
          {value}
        </span>
        {unit && <span className="text-xs font-mono text-[#71717A]">{unit}</span>}
      </div>

      {(subtext || delta) && (
        <div className="mt-2.5 pt-2 border-t border-[#202024]/60 flex items-center justify-between text-xs text-[#71717A]">
          {subtext && <span>{subtext}</span>}
          {delta && (
            <span
              className={`font-mono text-[11px] font-semibold ${
                delta.isNeutral
                  ? 'text-[#A1A1AA]'
                  : delta.isPositive
                  ? 'text-[#35B779]'
                  : 'text-[#F06464]'
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
