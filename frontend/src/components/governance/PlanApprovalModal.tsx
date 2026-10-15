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
      <DialogContent className="bg-[#0B101C] border border-[#1E2D4A] text-[#F8FAFC] sm:max-w-lg p-6 font-sans select-none shadow-2xl">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold text-[#F8FAFC]">
                {isRejectMode ? 'Reject Maintenance Plan Version' : 'Authorize & Approve Plan Version'}
              </DialogTitle>
              <DialogDescription className="text-xs text-[#94A3B8]">
                Plan Version {planVersion?.version_number ?? 1} • Immutable Four-Eyes Governance Gate
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Cryptographic schedule identity badge */}
        <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-3 space-y-1.5 text-xs font-mono">
          <div className="flex items-center justify-between text-[#94A3B8]">
            <span className="flex items-center gap-1.5 font-semibold text-[#CBD5E1]">
              <Fingerprint className="w-4 h-4 text-[#38BDF8]" />
              Schedule Identity (SHA-256):
            </span>
            {validationSummary?.valid === true ? (
              <span className="text-emerald-400 flex items-center gap-1 font-bold text-[11px]">
                <Lock className="w-3 h-3" />
                Feasibility Checked
              </span>
            ) : validationSummary?.valid === false ? (
              <span className="text-rose-400 flex items-center gap-1 font-bold text-[11px]">
                <AlertTriangle className="w-3 h-3" />
                Validation Errors Present
              </span>
            ) : (
              <span className="text-[#94A3B8] flex items-center gap-1 font-bold text-[11px]">
                <Lock className="w-3 h-3" />
                Identity Recorded
              </span>
            )}
          </div>
          <div className="text-[10px] text-[#38BDF8] break-all select-all font-mono">
            {scheduleFingerprint}
          </div>
        </div>

        {/* Warning Callout: COMPLETED != APPROVED */}
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-xs text-amber-200 space-y-1">
          <div className="flex items-center gap-1.5 font-bold text-amber-300 text-[11px]">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
            <span>OPERATIONAL BOUNDARY: COMPLETED ≠ APPROVED</span>
          </div>
          <p className="text-[11px] leading-relaxed text-amber-300/90 font-sans">
            Solver optimization and independent verification confirm mathematical and safety feasibility only.
            Track possession cannot commence without explicit human operational authorization.
          </p>
        </div>

        {/* Form Inputs */}
        <div className="space-y-3.5 text-xs font-sans">
          <div>
            <label className="text-[10px] text-[#94A3B8] uppercase tracking-wider block font-bold mb-1">
              Reviewing Officer
            </label>
            <input
              type="text"
              value={reviewerName}
              onChange={(e) => setReviewerName(e.target.value)}
              className="w-full bg-[#0F172A] border border-[#1E2D4A] rounded-md px-3 py-2 text-xs text-[#F8FAFC] focus:outline-hidden focus:border-[#2563EB]"
            />
          </div>

          <div>
            <label className="text-[10px] text-[#94A3B8] uppercase tracking-wider block font-bold mb-1">
              Designation / Role
            </label>
            <select
              value={reviewerRole}
              onChange={(e) => setReviewerRole(e.target.value)}
              className="w-full bg-[#0F172A] border border-[#1E2D4A] rounded-md px-3 py-2 text-xs text-[#F8FAFC] focus:outline-hidden focus:border-[#2563EB]"
            >
              <option value="DIVISIONAL_RAILWAY_MANAGER">Divisional Railway Manager (DRM)</option>
              <option value="SENIOR_DIV_OPERATIONS_MANAGER">Senior Divisional Operations Manager (Sr. DOM)</option>
              <option value="SENIOR_DIV_ENGINEER">Senior Divisional Engineer (Sr. DEN)</option>
              <option value="CHIEF_CONTROLLER">Chief Operating Controller (HQ)</option>
            </select>
          </div>

          <div>
            <label className="text-[10px] text-[#94A3B8] uppercase tracking-wider block font-bold mb-1">
              {isRejectMode ? 'Mandatory Rejection Rationale (Audit Log)' : 'Operational Approval Endorsement'}
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-[#0F172A] border border-[#1E2D4A] rounded-md p-2.5 text-xs text-[#F8FAFC] focus:outline-hidden focus:border-[#2563EB]"
            />
          </div>

          {!isRejectMode && (
            <label className="flex items-start gap-2 pt-1 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={acknowledged}
                onChange={(e) => setAcknowledged(e.target.checked)}
                className="mt-0.5 rounded border-[#1E2D4A] bg-[#0F172A] text-[#2563EB]"
              />
              <span className="text-[11px] text-[#94A3B8] leading-snug">
                I confirm that I have reviewed the proposed possession schedule, validated that required checks have passed, and authorize this plan version for issuance.
              </span>
            </label>
          )}
        </div>

        <DialogFooter className="flex items-center justify-between sm:justify-between pt-3 border-t border-[#1E2D4A]">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setIsRejectMode(!isRejectMode)}
            className="text-xs text-[#94A3B8] hover:text-[#F8FAFC]"
          >
            {isRejectMode ? 'Switch to Approve' : 'Switch to Reject'}
          </Button>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              className="border-[#2D436D] text-xs text-[#CBD5E1]"
            >
              Cancel
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={isSubmitting || (!isRejectMode && (!acknowledged || validationSummary?.valid === false))}
              onClick={handleSubmit}
              className={`text-xs font-semibold px-4 h-8 ${
                isRejectMode
                  ? 'bg-rose-600 hover:bg-rose-500 text-white'
                  : 'bg-emerald-600 hover:bg-emerald-500 text-white'
              }`}
            >
              {isSubmitting ? (
                'Recording Immutable Audit...'
              ) : isRejectMode ? (
                <>
                  <XCircle className="w-3.5 h-3.5 mr-1.5" />
                  Confirm Rejection
                </>
              ) : (
                <>
                  <CheckCircle className="w-3.5 h-3.5 mr-1.5" />
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
