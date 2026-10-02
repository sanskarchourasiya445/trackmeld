import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface SyntheticDataBadgeProps {
  className?: string;
  size?: 'sm' | 'default';
  showTooltip?: boolean;
}

export const SyntheticDataBadge: React.FC<SyntheticDataBadgeProps> = ({
  className = '',
  size = 'default',
  showTooltip = true,
}) => {
  const content = (
    <span
      className={`inline-flex items-center gap-1.5 font-mono uppercase tracking-wider font-semibold border rounded select-none cursor-help ${
        size === 'sm'
          ? 'text-[10px] px-1.5 py-0.5 border-amber-500/40 bg-amber-500/10 text-amber-300'
          : 'text-xs px-2.5 py-1 border-amber-500/50 bg-amber-500/15 text-amber-200'
      } ${className}`}
    >
      <AlertTriangle className={size === 'sm' ? 'w-3 h-3 text-amber-400' : 'w-3.5 h-3.5 text-amber-400'} />
      <span>Synthetic Demonstration Data</span>
    </span>
  );

  if (!showTooltip) return content;

  return (
    <Tooltip>
      <TooltipTrigger>{content}</TooltipTrigger>
      <TooltipContent className="max-w-xs bg-[#18181C] text-[#F5F5F5] border border-[#29292F] text-xs p-2.5">
        <p className="font-semibold text-amber-300 mb-1">Non-Operational Prototype</p>
        <p className="text-[#A1A1AA] leading-relaxed">
          This scenario contains synthetic timetable passes and maintenance work orders created for prototype verification. Not approved for physical train operations or track access.
        </p>
      </TooltipContent>
    </Tooltip>
  );
};
