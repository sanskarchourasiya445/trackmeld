'use client';

import React, { useState, useEffect } from 'react';
import { AppShell } from '@/components/shell/AppShell';
import { StatusBadge } from '@/components/common/StatusBadge';
import { SyntheticDataBadge } from '@/components/common/SyntheticDataBadge';
import {
  getPlanVersions,
  getPlanVersionAudit,
  approvePlanVersion,
  rejectPlanVersion,
  DEMO_PLAN_VERSION,
  DEMO_AUDIT_LOGS,
} from '@/lib/api/client';
import { PlanVersion, AuditLogEntry } from '@/types/planning';
import { PlanApprovalModal } from '@/components/governance/PlanApprovalModal';
import {
  History,
  FileCheck,
  Lock,
  UserCheck,
  Fingerprint,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function AuditPage() {
  const [planVersion, setPlanVersion] = useState<PlanVersion>(DEMO_PLAN_VERSION);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>(DEMO_AUDIT_LOGS);
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleManualRefresh = async () => {
    setLoading(true);
    try {
      const versions = await getPlanVersions('SCN-DEMO-001');
      if (versions && versions.length > 0) {
        const active = versions[0];
        setPlanVersion(active);
        const logs = await getPlanVersionAudit(active.plan_version_id);
        if (logs && logs.length > 0) {
          setAuditLogs(logs);
        }
      }
    } catch (err) {
      console.warn('Failed to load live audit data, using fallback:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    getPlanVersions('SCN-DEMO-001')
      .then(async (versions) => {
        if (cancelled || !versions || versions.length === 0) return;
        const active = versions[0];
        setPlanVersion(active);
        const logs = await getPlanVersionAudit(active.plan_version_id);
        if (!cancelled && logs && logs.length > 0) {
          setAuditLogs(logs);
        }
      })
      .catch((err) => {
        console.warn('Failed to load live audit data, using fallback:', err);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleApprove = async (payload: {
    reviewer_name: string;
    reviewer_role: string;
    approval_notes: string;
  }) => {
    try {
      const updated = await approvePlanVersion(planVersion.plan_version_id, payload.approval_notes);
      setPlanVersion(updated);
      await handleManualRefresh();
    } catch (err) {
      console.error('Approval failed:', err);
    }
  };

  const handleReject = async (payload: {
    reviewer_name: string;
    reviewer_role: string;
    rejection_reason: string;
  }) => {
    try {
      const updated = await rejectPlanVersion(planVersion.plan_version_id, payload.rejection_reason);
      setPlanVersion(updated);
      await handleManualRefresh();
    } catch (err) {
      console.error('Rejection failed:', err);
    }
  };

  const isPendingReview =
    planVersion.status === 'PENDING_REVIEW' || planVersion.status === 'READY_FOR_REVIEW';

  return (
    <AppShell activeScenarioId="SCN-DEMO-001">
      <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-6xl mx-auto w-full">
        {/* Header Block */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#202024] pb-5">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold font-mono text-[#F5F5F5]">
                Plan Governance & Immutable Audit Ledger
              </h1>
              <SyntheticDataBadge />
            </div>
            <p className="text-xs text-[#A1A1AA] mt-1 font-mono">
              Cryptographic Verification & Human-in-the-Loop Sign-off Records
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleManualRefresh}
              disabled={loading}
              className="border-[#29292F] text-xs font-mono text-[#A1A1AA]"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh Ledger
            </Button>

            {isPendingReview && (
              <Button
                onClick={() => setIsApprovalOpen(true)}
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs"
              >
                <CheckCircle className="w-3.5 h-3.5 mr-1.5" />
                Sign & Authorize Version
              </Button>
            )}
          </div>
        </div>

        {/* Core Principle Banner */}
        <div className="bg-[#141418] border border-[#202024] rounded-md p-4 font-mono text-xs">
          <div className="flex items-center gap-2 text-[#4C87E7] font-semibold mb-1">
            <Lock className="w-3.5 h-3.5" />
            <span>Non-Negotiable Architecture Principle</span>
          </div>
          <p className="text-[#A1A1AA] leading-relaxed">
            Rules classify → Optimization schedules → Independent Validator verifies → Humans approve → AI explains.
            The optimizer and validator cannot self-certify operational train plans. Every released possession requires an immutable signature by an authorized railway operations officer.
          </p>
        </div>

        {/* Current Plan Version Details Card */}
        <div className="bg-[#141418] border border-[#202024] rounded-md p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-[#202024] pb-3">
            <div className="flex items-center gap-3">
              <FileCheck className="w-5 h-5 text-[#4C87E7]" />
              <div>
                <h2 className="text-sm font-bold font-mono text-[#F5F5F5]">
                  Plan Version {planVersion.version_number} ({planVersion.plan_version_id || planVersion.id})
                </h2>
                <span className="text-[10px] font-mono text-[#71717A]">
                  Created {new Date(planVersion.created_at).toLocaleString()} by {planVersion.created_by}
                </span>
              </div>
            </div>

            <StatusBadge status={planVersion.status} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-xs">
            <div className="bg-[#0E0E12] p-3 rounded border border-[#202024]">
              <span className="text-[#71717A] text-[10px]">SCHEDULED POSSESSIONS</span>
              <div className="text-base font-bold text-emerald-400 mt-0.5">
                {planVersion.total_scheduled ?? 29} tasks scheduled
              </div>
            </div>
            <div className="bg-[#0E0E12] p-3 rounded border border-[#202024]">
              <span className="text-[#71717A] text-[10px]">UNSCHEDULED CONFLICTS</span>
              <div className="text-base font-bold text-rose-400 mt-0.5">
                {planVersion.total_unscheduled ?? 1} unplaced tasks
              </div>
            </div>
            <div className="bg-[#0E0E12] p-3 rounded border border-[#202024]">
              <span className="text-[#71717A] text-[10px]">IMMUTABLE STATE</span>
              <div className="text-base font-bold text-[#F5F5F5] mt-0.5 flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-[#4C87E7]" />
                {planVersion.status === 'APPROVED' || planVersion.status === 'REJECTED'
                  ? 'LOCKED / SEALED'
                  : 'PENDING HUMAN SIGNATURE'}
              </div>
            </div>
          </div>

          {/* SHA-256 Fingerprint */}
          <div className="bg-[#0E0E12] p-3 rounded border border-[#202024] font-mono text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-[#A1A1AA]">
              <Fingerprint className="w-4 h-4 text-[#4C87E7]" />
              <span>Schedule Fingerprint (SHA-256):</span>
            </div>
            <code className="text-[11px] text-[#4C87E7] bg-[#141418] px-2 py-0.5 rounded border border-[#29292F] select-all">
              {planVersion.schedule_identity || 'bae346ecf37b1fd80608cc5e0b8dae030517a44d5d5305f640d5767ed46999aa'}
            </code>
          </div>

          {/* Approval Signatures */}
          {planVersion.approved_by && (
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded p-4 font-mono text-xs text-[#F5F5F5] space-y-1">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                <UserCheck className="w-4 h-4" />
                <span>Authorized Human Approval Granted</span>
              </div>
              <p className="text-[11px] text-[#A1A1AA]">
                Signed by <strong>{planVersion.approved_by}</strong> on{' '}
                {new Date(planVersion.approved_at || '').toLocaleString()}
              </p>
              {planVersion.approval_notes && (
                <p className="text-[11px] text-emerald-200 mt-2 bg-emerald-950/60 p-2 rounded border border-emerald-800">
                  Notes: &quot;{planVersion.approval_notes}&quot;
                </p>
              )}
            </div>
          )}

          {planVersion.rejection_reason && (
            <div className="bg-rose-500/10 border border-rose-500/30 rounded p-4 font-mono text-xs text-[#F5F5F5] space-y-1">
              <div className="flex items-center gap-2 text-rose-400 font-semibold">
                <AlertTriangle className="w-4 h-4" />
                <span>Plan Rejected During Review</span>
              </div>
              <p className="text-[11px] text-rose-200 mt-2 bg-rose-950/60 p-2 rounded border border-rose-800">
                Reason: &quot;{planVersion.rejection_reason}&quot;
              </p>
            </div>
          )}
        </div>

        {/* Audit Log Timeline */}
        <div className="bg-[#141418] border border-[#202024] rounded-md p-5 space-y-4">
          <div className="flex items-center gap-2 border-b border-[#202024] pb-3">
            <History className="w-4 h-4 text-[#4C87E7]" />
            <h2 className="text-sm font-bold font-mono text-[#F5F5F5]">
              Immutable Lifecycle Audit Trail ({auditLogs.length} Events)
            </h2>
          </div>

          <div className="space-y-3 font-mono text-xs">
            {auditLogs.map((event) => {
              const eventId = event.event_id || event.id || 'AUD-001';
              const eventType = event.event_type || event.action || 'EVENT';
              const comment = event.comment || event.details || '';
              const actor = event.actor_username || event.actor_name || 'System';
              const role = event.actor_role || 'OPERATOR';

              const isHumanApproval =
                eventType.includes('APPROV') || role === 'ADMIN' || role === 'OPERATOR';
              const isHumanRejection = eventType.includes('REJECT');
              const isHumanAction = isHumanApproval || isHumanRejection;

              return (
                <div
                  key={eventId}
                  className="relative pl-6 pb-4 border-l border-[#29292F] last:border-0 last:pb-0"
                >
                  {/* Timeline node marker */}
                  <div
                    className={`absolute -left-[5px] top-0 w-2.5 h-2.5 rounded-full border-2 border-[#141418] ${
                      isHumanApproval
                        ? 'bg-emerald-400'
                        : isHumanRejection
                        ? 'bg-rose-400'
                        : 'bg-[#4C87E7]'
                    }`}
                  />

                  <div
                    className={`p-3 rounded space-y-1.5 border ${
                      isHumanApproval
                        ? 'bg-emerald-950/20 border-emerald-500/40 ring-1 ring-emerald-500/20'
                        : isHumanRejection
                        ? 'bg-rose-950/20 border-rose-500/40 ring-1 ring-rose-500/20'
                        : 'bg-[#0E0E12] border-[#202024]'
                    }`}
                  >
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        {/* System vs Human badge */}
                        <span
                          className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider ${
                            isHumanAction
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-[#18181C] text-[#71717A] border border-[#29292F]'
                          }`}
                        >
                          {isHumanAction ? 'HUMAN ACTION' : 'SYSTEM EVENT'}
                        </span>

                        <span className="text-[10px] bg-[#18181C] text-[#F5F5F5] px-2 py-0.5 rounded border border-[#29292F] font-bold">
                          {eventType}
                        </span>
                        <span className="text-[10px] text-[#71717A]">({eventId})</span>
                      </div>
                      <span className="text-[10px] text-[#71717A]">
                        {new Date(event.timestamp).toLocaleString()}
                      </span>
                    </div>

                    {comment && (
                      <p
                        className={`text-[11px] leading-relaxed ${
                          isHumanApproval
                            ? 'text-emerald-100 font-medium'
                            : isHumanRejection
                            ? 'text-rose-100 font-medium'
                            : 'text-[#A1A1AA]'
                        }`}
                      >
                        {comment}
                      </p>
                    )}

                    <div className="text-[10px] text-[#71717A] pt-1 flex items-center gap-2">
                      <span>
                        Officer / Agent:{' '}
                        <strong
                          className={
                            isHumanApproval
                              ? 'text-emerald-300'
                              : isHumanRejection
                              ? 'text-rose-300'
                              : 'text-zinc-300'
                          }
                        >
                          {actor}
                        </strong>{' '}
                        ({role})
                      </span>
                      {event.schedule_identity && (
                        <span className="truncate max-w-[200px]" title={event.schedule_identity}>
                          • Hash: {event.schedule_identity.slice(0, 12)}...
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <PlanApprovalModal
        isOpen={isApprovalOpen}
        onClose={() => setIsApprovalOpen(false)}
        planVersion={planVersion}
        onApprove={handleApprove}
        onReject={handleReject}
      />
    </AppShell>
  );
}
