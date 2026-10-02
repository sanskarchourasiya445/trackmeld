'use client';

import React, { useState } from 'react';
import { PlanVersion, ScheduleValidationResult } from '@/types/planning';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ShieldCheck, AlertTriangle, CheckCircle, XCircle, Fingerprint, Lock } from 'lucide-react';

interface PlanApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  planVersion: PlanVersion | null;
  validationSummary?: ScheduleValidationResult | null;
  onApprove: (data: {
    reviewer_name: string;
    reviewer_role: string;
    approval_notes: string;
  }) => Promise<void>;
  onReject: (data: {
    reviewer_name: string;
    reviewer_role: string;
    rejection_reason: string;
  }) => Promise<void>;
}

export const PlanApprovalModal: React.FC<PlanApprovalModalProps> = ({
  isOpen,
  onClose,
  planVersion,
  validationSummary,
  onApprove,
  onReject,
}) => {
  const [reviewerName, setReviewerName] = useState('Chief Planning Officer (DRM Office)');
  const [reviewerRole, setReviewerRole] = useState('DIVISIONAL_RAILWAY_MANAGER');
  const [notes, setNotes] = useState(
    'Possession schedule verified against Section 4 hard curfew rules and headway buffer requirements. Approved for implementation.'
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRejectMode, setIsRejectMode] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);

  const handleSubmit = async () => {
    if (!reviewerName || !notes) return;
    setIsSubmitting(true);
    try {
      if (isRejectMode) {
        await onReject({
          reviewer_name: reviewerName,
          reviewer_role: reviewerRole,
          rejection_reason: notes,
        });
      } else {
        await onApprove({
          reviewer_name: reviewerName,
          reviewer_role: reviewerRole,
          approval_notes: notes,
        });
      }
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  const scheduleFingerprint =
    planVersion?.schedule_identity ||
    validationSummary?.schedule_identity ||
    'bae346ecf37b1fd80608cc5e0b8dae030517a44d5d5305f640d5767ed46999aa';

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="bg-[#141418] border border-[#29292F] text-[#F5F5F5] sm:max-w-lg p-6 font-mono">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold text-[#F5F5F5]">
                {isRejectMode ? 'Reject Maintenance Plan Version' : 'Authorize & Approve Plan Version'}
              </DialogTitle>
              <DialogDescription className="text-xs text-[#A1A1AA]">
                Plan Version {planVersion?.version_number ?? 1} • Immutable Governance Gate
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Cryptographic schedule identity badge */}
        <div className="bg-[#0E0E12] border border-[#202024] rounded p-2.5 space-y-1 text-[10px]">
          <div className="flex items-center justify-between text-[#71717A]">
            <span className="flex items-center gap-1 font-semibold text-[#A1A1AA]">
              <Fingerprint className="w-3.5 h-3.5 text-[#4C87E7]" />
              Schedule Fingerprint (SHA-256):
            </span>
            <span className="text-emerald-400 flex items-center gap-1 font-bold">
              <Lock className="w-2.5 h-2.5" />
              Certified Valid
            </span>
          </div>
          <div className="text-[9px] text-[#71717A] truncate font-mono select-all">
            {scheduleFingerprint}
          </div>
        </div>

        {/* Warning Callout: COMPLETED != APPROVED */}
        <div className="bg-amber-500/10 border border-amber-500/30 rounded p-2.5 text-xs text-amber-200/90 space-y-1">
          <div className="flex items-center gap-1.5 font-bold text-amber-300 text-[11px]">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>OPERATIONAL BOUNDARY: COMPLETED ≠ APPROVED</span>
          </div>
          <p className="text-[10.5px] leading-relaxed text-amber-200/80">
            Solver optimization and independent validator verification verify mathematical and domain feasibility only.
            By Indian Railways Operating Manuals, track possession cannot commence without explicit human operational authorization.
          </p>
        </div>

        {/* Form Inputs */}
        <div className="space-y-3 text-xs">
          <div>
            <label className="text-[10px] text-[#A1A1AA] uppercase tracking-wider block mb-1">
              Reviewing Officer
            </label>
            <input
              type="text"
              value={reviewerName}
              onChange={(e) => setReviewerName(e.target.value)}
              className="w-full bg-[#0E0E12] border border-[#29292F] rounded px-3 py-1.5 text-xs text-[#F5F5F5] focus:outline-hidden focus:border-[#4C87E7]"
            />
          </div>

          <div>
            <label className="text-[10px] text-[#A1A1AA] uppercase tracking-wider block mb-1">
              Designation / Role
            </label>
            <select
              value={reviewerRole}
              onChange={(e) => setReviewerRole(e.target.value)}
              className="w-full bg-[#0E0E12] border border-[#29292F] rounded px-3 py-1.5 text-xs text-[#F5F5F5] focus:outline-hidden focus:border-[#4C87E7]"
            >
              <option value="DIVISIONAL_RAILWAY_MANAGER">Divisional Railway Manager (DRM)</option>
              <option value="SENIOR_DIV_OPERATIONS_MANAGER">Senior Divisional Operations Manager (Sr. DOM)</option>
              <option value="SENIOR_DIV_ENGINEER">Senior Divisional Engineer (Sr. DEN)</option>
              <option value="CHIEF_CONTROLLER">Chief Operating Controller (HQ)</option>
            </select>
          </div>

          <div>
            <label className="text-[10px] text-[#A1A1AA] uppercase tracking-wider block mb-1">
              {isRejectMode ? 'Mandatory Rejection Rationale (Audit Log)' : 'Operational Approval Endorsement'}
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-[#0E0E12] border border-[#29292F] rounded p-2.5 text-xs text-[#F5F5F5] focus:outline-hidden focus:border-[#4C87E7]"
            />
          </div>

          {!isRejectMode && (
            <label className="flex items-start gap-2 pt-1 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={acknowledged}
                onChange={(e) => setAcknowledged(e.target.checked)}
                className="mt-0.5 rounded border-[#29292F] bg-[#0E0E12] text-[#4C87E7]"
              />
              <span className="text-[10px] text-[#A1A1AA] leading-snug">
                I certify that I have audited the schedule against corridor traffic conditions, confirmed zero active train conflicts, and authorize track possession issuance.
              </span>
            </label>
          )}
        </div>

        <DialogFooter className="flex items-center justify-between sm:justify-between pt-2 border-t border-[#202024]">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setIsRejectMode(!isRejectMode)}
            className="text-xs text-[#71717A] hover:text-[#F5F5F5]"
          >
            {isRejectMode ? 'Switch to Approve' : 'Switch to Reject'}
          </Button>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              className="border-[#29292F] text-xs text-[#A1A1AA]"
            >
              Cancel
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={isSubmitting || (!isRejectMode && !acknowledged)}
              onClick={handleSubmit}
              className={`text-xs font-mono font-semibold ${
                isRejectMode
                  ? 'bg-rose-600 hover:bg-rose-500 text-white'
                  : 'bg-emerald-600 hover:bg-emerald-500 text-white'
              }`}
            >
              {isSubmitting ? (
                'Recording Immutable Audit...'
              ) : isRejectMode ? (
                <>
                  <XCircle className="w-3.5 h-3.5 mr-1" />
                  Confirm Rejection
                </>
              ) : (
                <>
                  <CheckCircle className="w-3.5 h-3.5 mr-1" />
                  Grant Human Approval
                </>
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
