'use client';

import React from 'react';
import { PlanVersionStatus } from '@/types/planning';
import {
  FileCode,
  Cpu,
  FileSearch,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from 'lucide-react';

export type LifecycleStage =
  | 'DRAFT'
  | 'OPTIMIZING'
  | 'CANDIDATE'
  | 'VALIDATED'
  | 'AWAITING_REVIEW'
  | 'APPROVED'
  | 'REJECTED';

interface PlanLifecycleBarProps {
  currentStage: LifecycleStage;
  planVersionStatus?: PlanVersionStatus | null;
  isApprovable?: boolean;
  approvedBy?: string | null;
  onOpenApprovalModal?: () => void;
}

export const PlanLifecycleBar: React.FC<PlanLifecycleBarProps> = ({
  currentStage,
  planVersionStatus,
  isApprovable = true,
  approvedBy,
  onOpenApprovalModal,
}) => {
  // Compute active index for progress bar
  const stages: {
    key: LifecycleStage;
    label: string;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
    actor: 'SYSTEM' | 'HUMAN';
  }[] = [
    {
      key: 'DRAFT',
      label: 'Draft Requisitions',
      description: '30 Maintenance work orders',
      icon: FileCode,
      actor: 'SYSTEM',
    },
    {
      key: 'OPTIMIZING',
      label: 'CP-SAT Solver',
      description: 'Mathematical optimization',
      icon: Cpu,
      actor: 'SYSTEM',
    },
    {
      key: 'CANDIDATE',
      label: 'Candidate Plan',
      description: '29 Placed / 1 Unplaced',
      icon: FileSearch,
      actor: 'SYSTEM',
    },
    {
      key: 'VALIDATED',
      label: 'Independently Certified',
      description: isApprovable ? '12 Hard rules verified (0 errors)' : 'Hard constraint violations present',
      icon: ShieldCheck,
      actor: 'SYSTEM',
    },
    {
      key: 'AWAITING_REVIEW',
      label: 'Awaiting Human Review',
      description: 'COMPLETED ≠ APPROVED',
      icon: AlertTriangle,
      actor: 'HUMAN',
    },
    {
      key: currentStage === 'REJECTED' || planVersionStatus === 'REJECTED' ? 'REJECTED' : 'APPROVED',
      label:
        currentStage === 'REJECTED' || planVersionStatus === 'REJECTED'
          ? 'Plan Rejected'
          : approvedBy
          ? `Approved (${approvedBy})`
          : 'Human Authorized',
      description:
        currentStage === 'REJECTED' || planVersionStatus === 'REJECTED'
          ? 'Formal rejection recorded'
          : approvedBy
          ? 'Legally certified possession'
          : 'Requires DRM / Sr. DOM sign-off',
      icon: currentStage === 'REJECTED' || planVersionStatus === 'REJECTED' ? XCircle : CheckCircle2,
      actor: 'HUMAN',
    },
  ];

  const getStageIndex = (stage: LifecycleStage): number => {
    switch (stage) {
      case 'DRAFT':
        return 0;
      case 'OPTIMIZING':
        return 1;
      case 'CANDIDATE':
        return 2;
      case 'VALIDATED':
        return 3;
      case 'AWAITING_REVIEW':
        return 4;
      case 'APPROVED':
      case 'REJECTED':
        return 5;
      default:
        return 4;
    }
  };

  const activeIndex = getStageIndex(currentStage);

  return (
    <div className="bg-[#141418] border border-[#202024] rounded-md p-2.5 font-mono select-none">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase text-[#71717A] tracking-wider font-semibold">
            Railway Decision Pipeline Lifecycle:
          </span>
          <span className="text-[11px] font-bold text-[#F5F5F5]">
            {stages[activeIndex]?.label}
          </span>
        </div>

        <div className="flex items-center gap-3 text-[10px]">
          <span className="flex items-center gap-1 text-amber-400 font-bold bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
            <AlertTriangle className="w-3 h-3" />
            COMPLETED ≠ APPROVED
          </span>
          {currentStage === 'AWAITING_REVIEW' && onOpenApprovalModal && (
            <button
              onClick={onOpenApprovalModal}
              className="text-emerald-400 hover:text-emerald-300 font-bold underline cursor-pointer"
            >
              Sign Decision Record →
            </button>
          )}
        </div>
      </div>

      {/* Stepper bar */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-1.5">
        {stages.map((st, idx) => {
          const isCurrent = idx === activeIndex;
          const isPassed = idx < activeIndex;
          const Icon = st.icon;

          let borderCol = 'border-[#202024]';
          let bgCol = 'bg-[#0E0E12]';
          let textCol = 'text-[#71717A]';
          let iconCol = 'text-[#71717A]';

          if (isCurrent) {
            if (st.key === 'REJECTED') {
              borderCol = 'border-rose-500/60 ring-1 ring-rose-500/30';
              bgCol = 'bg-rose-950/20';
              textCol = 'text-rose-300';
              iconCol = 'text-rose-400';
            } else if (st.key === 'APPROVED') {
              borderCol = 'border-emerald-500/60 ring-1 ring-emerald-500/30';
              bgCol = 'bg-emerald-950/20';
              textCol = 'text-emerald-300';
              iconCol = 'text-emerald-400';
            } else if (st.key === 'AWAITING_REVIEW') {
              borderCol = 'border-amber-500/60 ring-1 ring-amber-500/30';
              bgCol = 'bg-amber-950/20';
              textCol = 'text-amber-300';
              iconCol = 'text-amber-400';
            } else {
              borderCol = 'border-[#4C87E7]/60 ring-1 ring-[#4C87E7]/30';
              bgCol = 'bg-[#18181C]';
              textCol = 'text-[#F5F5F5]';
              iconCol = 'text-[#4C87E7]';
            }
          } else if (isPassed) {
            borderCol = 'border-emerald-800/40';
            bgCol = 'bg-[#0E0E12]';
            textCol = 'text-[#A1A1AA]';
            iconCol = 'text-emerald-400';
          }

          return (
            <div
              key={st.key}
              className={`p-2 rounded border ${borderCol} ${bgCol} flex flex-col justify-between transition-colors`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[9px] text-[#71717A] font-semibold">
                  0{idx + 1} • {st.actor}
                </span>
                <Icon className={`w-3.5 h-3.5 ${iconCol} ${isCurrent && st.key === 'OPTIMIZING' ? 'animate-spin' : ''}`} />
              </div>
              <div>
                <div className={`text-[10px] font-bold truncate ${textCol}`}>
                  {st.label}
                </div>
                <div className="text-[8.5px] text-[#71717A] truncate font-sans">
                  {st.description}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
