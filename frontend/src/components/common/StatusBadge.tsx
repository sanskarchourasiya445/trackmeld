import React from 'react';
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  XCircle,
  HelpCircle,
  ShieldCheck,
  RotateCw,
} from 'lucide-react';

export type DomainStatus =
  | 'DRAFT'
  | 'QUEUED'
  | 'RUNNING'
  | 'SOLVING'
  | 'VALIDATING'
  | 'VALIDATED'
  | 'READY_FOR_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'SUPERSEDED'
  | 'INFEASIBLE'
  | 'FAILED'
  | 'OPTIMAL'
  | 'FEASIBLE'
  | 'PASSED'
  | string;

interface StatusBadgeProps {
  status: DomainStatus;
  className?: string;
  size?: 'sm' | 'default';
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  className = '',
  size = 'default',
  showIcon = true,
}) => {
  const normStatus = (status || 'UNKNOWN').toUpperCase();

  let styles = 'bg-zinc-800/80 text-zinc-300 border-zinc-700/60';
  let icon = <HelpCircle className="w-3 h-3" />;

  switch (normStatus) {
    case 'APPROVED':
    case 'OPTIMAL':
    case 'PASSED':
      styles = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      icon = <CheckCircle2 className="w-3 h-3 text-emerald-400" />;
      break;

    case 'FEASIBLE':
    case 'VALIDATED':
      styles = 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      icon = <ShieldCheck className="w-3 h-3 text-blue-400" />;
      break;

    case 'READY_FOR_REVIEW':
      styles = 'bg-amber-500/10 text-amber-300 border-amber-500/30';
      icon = <Clock className="w-3 h-3 text-amber-400" />;
      break;

    case 'RUNNING':
    case 'SOLVING':
    case 'VALIDATING':
      styles = 'bg-sky-500/10 text-sky-300 border-sky-500/30';
      icon = <RotateCw className="w-3 h-3 text-sky-400 animate-spin" />;
      break;

    case 'QUEUED':
    case 'PENDING':
    case 'DRAFT':
      styles = 'bg-zinc-800 text-zinc-400 border-zinc-700';
      icon = <Clock className="w-3 h-3 text-zinc-400" />;
      break;

    case 'REJECTED':
    case 'FAILED':
    case 'INFEASIBLE':
      styles = 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      icon = <XCircle className="w-3 h-3 text-rose-400" />;
      break;

    case 'SUPERSEDED':
      styles = 'bg-zinc-900 text-zinc-500 border-zinc-800 line-through';
      icon = <AlertCircle className="w-3 h-3 text-zinc-500" />;
      break;

    default:
      styles = 'bg-zinc-800/80 text-zinc-300 border-zinc-700/60';
      icon = <HelpCircle className="w-3 h-3" />;
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono font-medium tracking-wide uppercase border rounded ${
        size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2.5 py-1'
      } ${styles} ${className}`}
    >
      {showIcon && icon}
      <span>{normStatus.replace(/_/g, ' ')}</span>
    </span>
  );
};
