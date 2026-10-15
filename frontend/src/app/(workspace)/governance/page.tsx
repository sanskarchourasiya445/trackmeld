'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { PlanApprovalModal } from '@/components/governance/PlanApprovalModal';
import {
  DEMO_VALIDATION_RESULT,
  DEMO_PLAN_VERSION,
  DEMO_AUDIT_LOGS,
  getPlanVersions,
  getPlanVersionAudit,
  approvePlanVersion,
  rejectPlanVersion,
} from '@/lib/api/client';
import {
  PlanVersion,
  ScheduleValidationResult,
  AuditLogEntry,
  DataProvenance,
  ScheduleResult,
} from '@/types/planning';
import {
  ShieldCheck,
  FileCheck,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  UserCheck,
  History,
  Hash,
  RefreshCw,
  Database,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function GovernancePage() {
  const [planVersion, setPlanVersion] = useState<PlanVersion | null>(null);
  const [validationResult, setValidationResult] = useState<ScheduleValidationResult | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [provenance, setProvenance] = useState<DataProvenance>('loading');
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const loadVersion = useCallback(async () => {
    setProvenance('loading');
    setFetchError(null);
    try {
      const versions = await getPlanVersions('SCN-DEMO-001');
      if (versions && versions.length > 0) {
        const active = versions[0];
        setPlanVersion(active);
        setProvenance('backend');
        const schedResult = (active as unknown as { schedule_result?: ScheduleResult }).schedule_result;
        const valData = schedResult?.validation || (schedResult as unknown as { validation_summary?: ScheduleValidationResult })?.validation_summary;
        if (valData) {
          setValidationResult(valData as ScheduleValidationResult);
        } else if (active.validation_status === 'VALID' && active.schedule_identity) {
          setValidationResult({
            status: 'VALID',
            valid: true,
            is_approvable: active.is_approvable ?? true,
            schedule_identity: active.schedule_identity,
            findings: [],
            error_count: (active.validation_findings_summary?.error_count as number) || 0,
            warning_count: 0,
            info_count: 0,
            checked_task_count: 0,
            checked_section_count: 0,
            checked_resource_count: 0,
            checked_train_movement_count: 0,
            checks_executed: [],
            approval_gate_message: 'Certified under authoritative backend governance record',
          });
        } else if (active.validation_status === 'INVALID' && active.schedule_identity) {
          setValidationResult({
            status: 'INVALID',
            valid: false,
            is_approvable: false,
            schedule_identity: active.schedule_identity,
            findings: [],
            error_count: (active.validation_findings_summary?.error_count as number) || 1,
            warning_count: 0,
            info_count: 0,
            checked_task_count: 0,
            checked_section_count: 0,
            checked_resource_count: 0,
            checked_train_movement_count: 0,
            checks_executed: [],
            approval_gate_message: 'Validation rejected: Schedule contains constraint violations',
          });
        } else {
          setValidationResult(null);
        }
        try {
          const logs = await getPlanVersionAudit(active.plan_version_id);
          setAuditLogs(logs || []);
        } catch {
          setAuditLogs([]);
        }
      } else {
        setPlanVersion(null);
        setValidationResult(null);
        setAuditLogs([]);
        setProvenance('backend');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setFetchError(`BACKEND GOVERNANCE SERVICE UNAVAILABLE: ${msg}`);
      setProvenance('unavailable');
      setPlanVersion(null);
      setValidationResult(null);
      setAuditLogs([]);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    getPlanVersions('SCN-DEMO-001')
      .then(async (versions) => {
        if (cancelled) return;
        if (versions && versions.length > 0) {
          const active = versions[0];
          setPlanVersion(active);
          setProvenance('backend');
          const schedResult = (active as unknown as { schedule_result?: ScheduleResult }).schedule_result;
          const valData = schedResult?.validation || (schedResult as unknown as { validation_summary?: ScheduleValidationResult })?.validation_summary;
          if (valData) {
            setValidationResult(valData as ScheduleValidationResult);
          } else if (active.validation_status === 'VALID' && active.schedule_identity) {
            setValidationResult({
              status: 'VALID',
              valid: true,
              is_approvable: active.is_approvable ?? true,
              schedule_identity: active.schedule_identity,
              findings: [],
              error_count: (active.validation_findings_summary?.error_count as number) || 0,
              warning_count: 0,
              info_count: 0,
              checked_task_count: 0,
              checked_section_count: 0,
              checked_resource_count: 0,
              checked_train_movement_count: 0,
              checks_executed: [],
              approval_gate_message: 'Certified under authoritative backend governance record',
            });
          } else if (active.validation_status === 'INVALID' && active.schedule_identity) {
            setValidationResult({
              status: 'INVALID',
              valid: false,
              is_approvable: false,
              schedule_identity: active.schedule_identity,
              findings: [],
              error_count: (active.validation_findings_summary?.error_count as number) || 1,
              warning_count: 0,
              info_count: 0,
              checked_task_count: 0,
              checked_section_count: 0,
              checked_resource_count: 0,
              checked_train_movement_count: 0,
              checks_executed: [],
              approval_gate_message: 'Validation rejected: Schedule contains constraint violations',
            });
          } else {
            setValidationResult(null);
          }
          try {
            const logs = await getPlanVersionAudit(active.plan_version_id);
            if (!cancelled) setAuditLogs(logs || []);
          } catch {
            if (!cancelled) setAuditLogs([]);
          }
        } else {
          setPlanVersion(null);
          setValidationResult(null);
          setAuditLogs([]);
          setProvenance('backend');
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : String(err);
        setFetchError(`BACKEND GOVERNANCE SERVICE UNAVAILABLE: ${msg}`);
        setProvenance('unavailable');
        setPlanVersion(null);
        setValidationResult(null);
        setAuditLogs([]);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleLoadDemo = () => {
    setPlanVersion(DEMO_PLAN_VERSION);
    setValidationResult(DEMO_VALIDATION_RESULT);
    setAuditLogs(DEMO_AUDIT_LOGS);
    setProvenance('synthetic');
    setFetchError(null);
  };

  const isIdentityMismatch = Boolean(
    planVersion &&
    validationResult &&
    planVersion.schedule_identity !== validationResult.schedule_identity
  );

  const handleApprove = async (payload: { reviewer_name: string; reviewer_role: string; approval_notes: string }) => {
    if (!planVersion || provenance !== 'backend') return;
    if (isIdentityMismatch) {
      setActionError('Cannot approve plan version: Cryptographic identity mismatch with validation certification.');
      return;
    }
    if (!validationResult || !validationResult.is_approvable || planVersion.validation_status === 'INVALID' || planVersion.is_approvable === false) {
      setActionError('Cannot approve plan version: Validation has not certified this plan as valid and approvable.');
      return;
    }
    setActionError(null);
    try {
      const updated = await approvePlanVersion(
        planVersion.plan_version_id,
        payload.approval_notes,
        payload.reviewer_name,
        payload.reviewer_role
      );
      setPlanVersion(updated);
      setIsApprovalOpen(false);
      try {
        const logs = await getPlanVersionAudit(planVersion.plan_version_id);
        setAuditLogs(logs || []);
      } catch {
        // Non-blocking refresh
      }
    } catch (err: unknown) {
      console.error('Plan approval error:', err);
      const msg = err instanceof Error ? err.message : String(err);
      setActionError(`GOVERNANCE ACTION REJECTED: ${msg}`);
      setIsApprovalOpen(false);
    }
  };

  const handleReject = async (payload: { reviewer_name: string; reviewer_role: string; rejection_reason: string }) => {
    if (!planVersion || provenance !== 'backend') return;
    if (isIdentityMismatch) {
      setActionError('Cannot reject plan version: Cryptographic identity mismatch with validation certification.');
      return;
    }
    setActionError(null);
    try {
      const updated = await rejectPlanVersion(planVersion.plan_version_id, payload.rejection_reason);
      setPlanVersion(updated);
      setIsApprovalOpen(false);
      try {
        const logs = await getPlanVersionAudit(planVersion.plan_version_id);
        setAuditLogs(logs || []);
      } catch {
        // Non-blocking refresh
      }
    } catch (err: unknown) {
      console.error('Plan rejection error:', err);
      const msg = err instanceof Error ? err.message : String(err);
      setActionError(`GOVERNANCE ACTION REJECTED: ${msg}`);
      setIsApprovalOpen(false);
    }
  };

  return (
    <>
      <div className="flex-1 overflow-y-auto p-3 sm:p-4 lg:p-5 space-y-3.5 max-w-[1920px] w-full mx-auto font-sans select-none">
        {/* ============================================================== */}
        {/* 1. GOVERNANCE COMMAND HEADER                                   */}
        {/* ============================================================== */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-[#1E2D4A]">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-xs">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h1 className="text-xl font-bold tracking-tight text-[#F8FAFC]">
                    Safety Validation & Human Governance
                  </h1>
                  {provenance === 'loading' && (
                    <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-[#162238] text-[#38BDF8] border border-[#2563EB]/30 animate-pulse">
                      CONNECTING TO BACKEND...
                    </span>
                  )}
                  {provenance === 'backend' && (
                    <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-emerald-950/80 text-emerald-400 border border-emerald-500/40 font-bold">
                      AUTHORITATIVE BACKEND LEDGER
                    </span>
                  )}
                  {provenance === 'synthetic' && (
                    <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-amber-950/80 text-amber-400 border border-amber-500/40 font-bold">
                      DEMO AUDIT TRAIL • READ ONLY
                    </span>
                  )}
                  {provenance === 'unavailable' && (
                    <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-rose-950/80 text-rose-400 border border-rose-500/40 font-bold">
                      BACKEND OFFLINE
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-[#94A3B8] mt-0.5">
                  Independent mathematical validation check and Four-Eyes human operator sign-off
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            {planVersion && (
              <div className="bg-[#0B101C] border border-[#1E2D4A] rounded-md px-2.5 py-1 flex items-center gap-2 text-xs font-mono">
                <span className="text-[#64748B]">Plan Version:</span>
                <strong className="text-[#F8FAFC]">v{planVersion.version_number}</strong>
                <span className="text-[#334155]">•</span>
                <span
                  className={`px-2 py-0.5 rounded font-bold text-[10px] border ${
                    planVersion.status === 'APPROVED'
                      ? 'bg-emerald-950/80 text-emerald-400 border-emerald-500/40'
                      : planVersion.status === 'REJECTED'
                      ? 'bg-rose-950/80 text-rose-400 border-rose-500/40'
                      : 'bg-amber-950/80 text-amber-400 border-amber-500/40'
                  }`}
                >
                  {planVersion.status}
                </span>
              </div>
            )}

            <Button
              size="sm"
              variant="outline"
              onClick={loadVersion}
              className="border-[#1E2D4A] text-xs text-[#94A3B8] hover:text-white h-8 px-2.5"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1" />
              <span>Refresh</span>
            </Button>

            <Button
              size="sm"
              disabled={
                !planVersion ||
                provenance !== 'backend' ||
                planVersion.status === 'APPROVED' ||
                planVersion.status === 'REJECTED' ||
                isIdentityMismatch ||
                !validationResult ||
                !validationResult.is_approvable ||
                planVersion.validation_status === 'INVALID' ||
                planVersion.is_approvable === false
              }
              onClick={() => setIsApprovalOpen(true)}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold px-3 h-8 shadow-xs cursor-pointer"
              title={
                provenance === 'synthetic'
                  ? 'Demo scenarios are read-only. Connect to backend for authoritative governance review.'
                  : isIdentityMismatch
                    ? 'Cryptographic identity mismatch between plan version and validation certification.'
                    : validationResult && !validationResult.is_approvable
                      ? 'Plan validation failed hard constraint certification.'
                      : undefined
              }
            >
              <FileCheck className="w-3.5 h-3.5 mr-1.5" />
              <span>
                {provenance === 'synthetic'
                  ? 'Demo Plan — Read Only'
                  : !planVersion
                    ? 'No Plan Version'
                    : isIdentityMismatch
                      ? 'Identity Mismatch'
                      : !validationResult ||
                        !validationResult.is_approvable ||
                        planVersion?.validation_status === 'INVALID' ||
                        planVersion?.is_approvable === false
                        ? 'Validation Incomplete'
                        : planVersion?.status === 'APPROVED'
                          ? 'Plan Approved'
                          : planVersion?.status === 'REJECTED'
                            ? 'Plan Rejected'
                            : 'Perform Four-Eyes Review'}
              </span>
            </Button>
          </div>
        </div>

        {/* Identity Mismatch Warning Banner */}
        {isIdentityMismatch && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2 text-xs text-rose-300 flex items-center gap-2 shrink-0">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>
              <strong>Cryptographic Identity Mismatch:</strong> The plan version identity (<code className="font-mono">{planVersion?.schedule_identity?.slice(0, 12)}...</code>) does not match the validation audit record (<code className="font-mono">{validationResult?.schedule_identity?.slice(0, 12)}...</code>). Four-Eyes approval is strictly blocked.
            </span>
          </div>
        )}

        {/* Action Error Banner */}
        {actionError && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2 text-xs text-rose-300 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{actionError}</span>
            </div>
            <button
              onClick={() => setActionError(null)}
              className="text-[#94A3B8] hover:text-white text-xs px-2 py-0.5 rounded hover:bg-rose-500/20 cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Fetch Error / Backend Offline Banner */}
        {fetchError && provenance === 'unavailable' && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-3.5 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-rose-400 font-bold">
                <AlertCircle className="w-4 h-4" />
                <span>Backend Governance Service Unreachable</span>
              </div>
              <span className="text-[10px] font-mono text-rose-400 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-500/30">
                OFFLINE
              </span>
            </div>
            <p className="text-[#94A3B8] leading-relaxed">
              TrackMeld was unable to retrieve authoritative plan versions or validation evidence from the backend server.
              Offline state prevents live governance decisions.
            </p>
            <div className="flex items-center gap-2 pt-1">
              <Button size="sm" onClick={loadVersion} className="bg-rose-600 hover:bg-rose-500 text-white text-xs h-7 px-3">
                <RefreshCw className="w-3 h-3 mr-1" />
                Retry Connection
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleLoadDemo}
                className="border-[#1E2D4A] text-[#94A3B8] hover:text-white text-xs h-7 px-3"
              >
                <Database className="w-3 h-3 mr-1" />
                Inspect Synthetic Demo Scenario
              </Button>
            </div>
          </div>
        )}

        {/* Empty State when backend returns no versions */}
        {provenance === 'backend' && !planVersion && (
          <div className="bg-[#0B101C] border border-[#1E2D4A] rounded-lg p-6 text-center text-[#94A3B8] space-y-2">
            <ShieldCheck className="w-8 h-8 mx-auto text-[#64748B]" />
            <h3 className="font-bold text-sm text-[#F8FAFC]">No Plan Versions Created Yet</h3>
            <p className="text-xs max-w-md mx-auto">
              Run an optimization solve in the Planning Workspace and persist a candidate version to submit it for formal Four-Eyes governance.
            </p>
            <div className="pt-2">
              <Button size="sm" variant="outline" onClick={handleLoadDemo} className="border-[#1E2D4A] text-[#38BDF8] hover:text-white text-xs">
                Inspect Synthetic Demo Scenario
              </Button>
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* 2. FORMAL OPERATIONAL GOVERNANCE WORKFLOW PIPELINE             */}
        {/* ============================================================== */}
        <div className="bg-[#0B101C] border border-[#1E2D4A] rounded-lg p-3 sm:p-4 shadow-xs space-y-2.5">
          <div className="text-[10px] font-mono uppercase font-bold text-[#64748B] tracking-wider">
            FORMAL OPERATIONAL GOVERNANCE PIPELINE
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-2.5">
            <div className="bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-3 relative">
              <span className="text-[10px] font-mono text-[#64748B] block font-bold">STAGE 1</span>
              <span className="font-bold text-xs text-[#F8FAFC] block mt-0.5">CP-SAT Optimization</span>
              <p className="text-[11px] text-emerald-400 font-mono mt-0.5 font-semibold">
                {planVersion ? `${planVersion.scheduler_type || 'CP-SAT'} Solver` : 'Awaiting Run'}
              </p>
              <span className="text-[10.5px] text-[#94A3B8] block mt-0.5">Mathematical interval assignment</span>
            </div>

            <div className="bg-[#0F172A] border border-emerald-500/40 rounded-lg p-3 relative">
              <span className="text-[10px] font-mono text-emerald-400 block font-bold">STAGE 2</span>
              <span className="font-bold text-xs text-[#F8FAFC] block mt-0.5">Independent Validation</span>
              <p
                className={`text-[11px] font-mono mt-0.5 font-semibold ${
                  validationResult?.valid
                    ? 'text-emerald-400'
                    : validationResult
                    ? 'text-rose-400'
                    : 'text-[#94A3B8]'
                }`}
              >
                {validationResult?.valid
                  ? `VALID (${validationResult.findings?.length || 0} findings)`
                  : validationResult
                  ? `INVALID (${validationResult.findings?.length || 0} violations)`
                  : 'VALIDATION PENDING'}
              </p>
              <span className="text-[10.5px] text-[#94A3B8] block mt-0.5">Separated verification engine</span>
            </div>

            <div className="bg-[#0F172A] border border-[#2563EB]/40 rounded-lg p-3 relative">
              <span className="text-[10px] font-mono text-[#38BDF8] block font-bold">STAGE 3</span>
              <span className="font-bold text-xs text-[#F8FAFC] block mt-0.5">Four-Eyes Human Review</span>
              <p className="text-[11px] text-[#93C5FD] font-mono mt-0.5 font-semibold">Role Segregation Mandatory</p>
              <span className="text-[10.5px] text-[#94A3B8] block mt-0.5">Creator cannot approve plan</span>
            </div>

            <div
              className={`border rounded-lg p-3 relative ${
                planVersion?.status === 'APPROVED'
                  ? 'bg-emerald-950/20 border-emerald-500/50'
                  : planVersion?.status === 'REJECTED'
                  ? 'bg-rose-950/20 border-rose-500/40'
                  : 'bg-amber-950/20 border-amber-500/40'
              }`}
            >
              <span className="text-[10px] font-mono block text-[#94A3B8] font-bold">STAGE 4</span>
              <span className="font-bold text-xs text-[#F8FAFC] block mt-0.5">Final Track Clearance</span>
              <p
                className={`text-[11px] font-mono mt-0.5 font-bold ${
                  provenance === 'synthetic'
                    ? 'text-amber-400'
                    : planVersion?.status === 'APPROVED'
                    ? 'text-emerald-400'
                    : planVersion?.status === 'REJECTED'
                    ? 'text-rose-400'
                    : 'text-amber-400'
                }`}
              >
                {provenance === 'synthetic'
                  ? 'DEMO SCENARIO (READ ONLY)'
                  : planVersion?.status === 'APPROVED'
                  ? 'PLAN AUTHORIZED & SIGNED'
                  : planVersion?.status === 'REJECTED'
                  ? 'PLAN REJECTED BY GOVERNANCE'
                  : 'AWAITING EXECUTIVE SIGN-OFF'}
              </p>
              <span className="text-[10.5px] text-[#94A3B8] block mt-0.5">
                {provenance === 'synthetic'
                  ? 'Approval disabled on demo fixture'
                  : planVersion?.status === 'APPROVED'
                  ? 'Ready for field dispatch'
                  : planVersion?.status === 'REJECTED'
                  ? 'Cannot dispatch to live corridor'
                  : 'Action required by DRM/Sr. DOM'}
              </span>
            </div>
          </div>
        </div>

        {/* ============================================================== */}
        {/* 3. FOUR-EYES ROLE SEGREGATION & CRYPTOGRAPHIC IDENTITY         */}
        {/* ============================================================== */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5">
          {/* Left: Four-Eyes Principle */}
          <div className="lg:col-span-6 bg-[#0B101C] border border-[#1E2D4A] rounded-lg p-3.5 sm:p-4 space-y-2.5">
            <div className="flex items-center justify-between pb-2.5 border-b border-[#1E2D4A]">
              <span className="font-bold text-xs text-[#F8FAFC] flex items-center gap-1.5">
                <UserCheck className="w-3.5 h-3.5 text-[#38BDF8]" />
                Four-Eyes Operational Principle
              </span>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/50 px-2 py-0.5 rounded border border-emerald-500/30 font-bold">
                MANDATORY STATUTORY RULE
              </span>
            </div>
            <p className="text-[11px] text-[#94A3B8] leading-relaxed">
              TrackMeld enforces strict role segregation. The author of an optimization scenario cannot approve their own plan for live track execution.
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-0.5">
              <div className="bg-[#0F172A] p-2.5 rounded-md border border-[#1E2D4A]">
                <span className="text-[10px] text-[#64748B] block font-bold">PLAN CREATOR:</span>
                <span className="font-bold text-[#F8FAFC] text-xs block mt-0.5">
                  {planVersion?.created_by || '—'}
                </span>
                <span className="text-[10.5px] text-[#94A3B8] block mt-0.5">Chief Operations Planner</span>
              </div>
              <div className="bg-[#0F172A] p-2.5 rounded-md border border-[#1E2D4A]">
                <span className="text-[10px] text-[#64748B] block font-bold">
                  {planVersion?.status === 'APPROVED'
                    ? 'APPROVED BY:'
                    : planVersion?.status === 'REJECTED'
                    ? 'REJECTED BY:'
                    : 'DESIGNATED APPROVER:'}
                </span>
                <span
                  className={`font-bold text-xs block mt-0.5 ${
                    planVersion?.status === 'APPROVED'
                      ? 'text-emerald-400'
                      : planVersion?.status === 'REJECTED'
                      ? 'text-rose-400'
                      : 'text-[#94A3B8]'
                  }`}
                >
                  {planVersion?.status === 'APPROVED'
                    ? planVersion.approved_by || '—'
                    : planVersion?.status === 'REJECTED'
                    ? planVersion.rejected_by || 'Operations Reviewer'
                    : 'Pending Four-Eyes Review'}
                </span>
                <span className="text-[10.5px] text-[#94A3B8] block mt-0.5">
                  {planVersion?.status === 'APPROVED'
                    ? `Authorized on ${planVersion.approved_at ? new Date(planVersion.approved_at).toLocaleDateString() : 'Confirmed'}`
                    : planVersion?.status === 'REJECTED'
                    ? `Rejected: ${planVersion.rejection_reason || 'Safety criteria not met'}`
                    : 'Independent Safety & Governance Officer'}
                </span>
              </div>
            </div>
          </div>

          {/* Right: Cryptographic Plan Identity */}
          <div className="lg:col-span-6 bg-[#0B101C] border border-[#1E2D4A] rounded-lg p-3.5 sm:p-4 space-y-2.5">
            <div className="flex items-center justify-between pb-2.5 border-b border-[#1E2D4A]">
              <span className="font-bold text-xs text-[#F8FAFC] flex items-center gap-1.5">
                <Hash className="w-3.5 h-3.5 text-[#38BDF8]" />
                Cryptographic Plan Identity & Proof
              </span>
              <span className="text-[10px] font-mono text-[#93C5FD] bg-[#141F36] px-2 py-0.5 rounded border border-[#2D436D] font-bold">
                SHA-256 PROOF
              </span>
            </div>
            <div className="space-y-2 text-xs font-mono">
              <div className="bg-[#0F172A] p-2.5 rounded-md border border-[#1E2D4A]">
                <span className="text-[10px] text-[#64748B] block font-bold mb-0.5">SCHEDULE IDENTITY HASH:</span>
                <span className="text-[#38BDF8] break-all text-[11px] leading-normal select-all font-mono">
                  {planVersion?.schedule_identity || 'No active candidate'}
                </span>
              </div>
              <div className="flex justify-between text-[11px] text-[#94A3B8] pt-0.5">
                <span>
                  Snapshot: <strong className="text-white">{validationResult?.input_snapshot_id || '—'}</strong>
                </span>
                <span>
                  Validation Runtime:{' '}
                  <strong className="text-emerald-400">
                    {validationResult?.validation_runtime_ms
                      ? `${validationResult.validation_runtime_ms.toFixed(1)} ms`
                      : '—'}
                  </strong>
                </span>
                <span>
                  Scheduled Tasks:{' '}
                  <strong className="text-white">
                    {planVersion?.total_scheduled !== undefined ? planVersion.total_scheduled : '—'}
                  </strong>
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ============================================================== */}
        {/* 4. INDEPENDENT VALIDATION SUITE RESULTS                        */}
        {/* ============================================================== */}
        <div className="bg-[#0B101C] border border-[#1E2D4A] rounded-lg p-3 sm:p-4 flex flex-col shadow-xs space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-2.5 border-b border-[#1E2D4A]">
            <div>
              <h2 className="text-sm font-bold text-[#F8FAFC]">Independent Feasibility Validation Suite</h2>
              <p className="text-[11px] text-[#94A3B8] mt-0.5">
                Executed outside the solver process by an isolated deterministic validation engine
              </p>
            </div>
            {validationResult ? (
              <span
                className={`text-xs font-mono font-bold px-2.5 py-1 rounded-md border ${
                  validationResult.valid
                    ? 'text-emerald-400 bg-emerald-950/60 border-emerald-500/40'
                    : 'text-rose-400 bg-rose-950/60 border-rose-500/40'
                }`}
              >
                {validationResult.valid
                  ? 'VERIFIED VALID (0 BREACHES)'
                  : `${validationResult.error_count || validationResult.findings?.length || 1} VIOLATIONS DETECTED`}
              </span>
            ) : (
              <span className="text-xs font-mono font-bold text-[#94A3B8] bg-[#141F36] px-2.5 py-1 rounded-md border border-[#1E2D4A]">
                NO VALIDATION EVIDENCE
              </span>
            )}
          </div>

          {validationResult ? (
            validationResult.findings && validationResult.findings.length > 0 ? (
              <div className="overflow-x-auto rounded-md border border-[#1E2D4A] bg-[#0F172A]">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[#141F36] text-[#64748B] font-mono uppercase text-[10px] sticky top-0 border-b border-[#1E2D4A]">
                    <tr>
                      <th className="py-2 px-3">Rule Code</th>
                      <th className="py-2 px-3">Target</th>
                      <th className="py-2 px-3">Severity</th>
                      <th className="py-2 px-3">Finding Message</th>
                      <th className="py-2 px-3 text-right">Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1E2D4A]/50 font-sans">
                    {validationResult.findings.map((f, idx) => (
                      <tr key={idx} className="hover:bg-[#141F36] transition-colors">
                        <td className="py-2 px-3 font-mono font-bold text-[#38BDF8]">{f.rule_code}</td>
                        <td className="py-2 px-3 font-mono text-[#CBD5E1]">
                          {f.target_type} {f.target_id || ''}
                        </td>
                        <td className="py-2 px-3 font-mono text-[10px]">
                          <span
                            className={`px-2 py-0.5 rounded font-bold border ${
                              f.severity === 'CRITICAL' || f.severity === 'ERROR'
                                ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                                : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                            }`}
                          >
                            {f.severity}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-[#CBD5E1] leading-relaxed">{f.message}</td>
                        <td className="py-2 px-3 text-right">
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-rose-400 bg-rose-950/40 px-2 py-0.5 rounded border border-rose-500/30">
                            FAIL
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="bg-[#0A0E17] border border-emerald-500/30 rounded-md p-4 space-y-3">
                <div className="flex items-center gap-2 text-emerald-400 font-semibold text-xs">
                  <CheckCircle className="w-4 h-4" />
                  <span>All modeled safety and feasibility constraints passed (0 breaches reported)</span>
                </div>
                {validationResult.checks_executed && validationResult.checks_executed.length > 0 && (
                  <div>
                    <span className="text-[10px] font-mono uppercase text-[#64748B] block font-bold mb-1.5">
                      Executed Verification Modules ({validationResult.checks_executed.length}):
                    </span>
                    <div className="flex flex-wrap gap-1.5 font-mono text-[10px]">
                      {validationResult.checks_executed.map((chk, i) => (
                        <span key={i} className="px-2 py-0.5 rounded bg-[#141F36] text-[#38BDF8] border border-[#1E2D4A]">
                          ✓ {chk}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {validationResult.approval_gate_message && (
                  <p className="text-[11px] font-mono text-[#94A3B8] border-t border-[#1E2D4A] pt-2 mt-2">
                    {validationResult.approval_gate_message}
                  </p>
                )}
              </div>
            )
          ) : (
            <div className="bg-[#0A0E17] border border-[#1E2D4A] rounded-md p-6 text-center text-[#94A3B8] space-y-1">
              <ShieldCheck className="w-6 h-6 mx-auto text-[#64748B] mb-2" />
              <p className="text-xs font-semibold text-[#F8FAFC]">
                No validation evidence available for this plan version
              </p>
              <p className="text-[11px]">
                The schedule candidate must undergo independent deterministic validation before human Four-Eyes sign-off.
              </p>
            </div>
          )}
        </div>

        {/* ============================================================== */}
        {/* 5. IMMUTABLE AUDIT TRAIL TIMELINE & LOGS                       */}
        {/* ============================================================== */}
        <div className="bg-[#0B101C] border border-[#1E2D4A] rounded-lg p-3 sm:p-4 flex flex-col shadow-xs space-y-3">
          <div className="flex items-center justify-between pb-2.5 border-b border-[#1E2D4A]">
            <span className="font-bold text-sm text-[#F8FAFC] flex items-center gap-1.5">
              <History className="w-3.5 h-3.5 text-[#38BDF8]" />
              Immutable Governance Audit Log
            </span>
            <span className="text-[11px] text-[#64748B] font-mono">
              {provenance === 'backend'
                ? 'Persisted backend governance audit events'
                : provenance === 'synthetic'
                ? 'Synthetic demo audit events (Read-only)'
                : 'No audit records connected'}
            </span>
          </div>

          {auditLogs && auditLogs.length > 0 ? (
            <div className="overflow-x-auto rounded-md border border-[#1E2D4A] bg-[#0F172A]">
              <table className="w-full text-xs text-left">
                <thead className="bg-[#141F36] text-[#64748B] font-mono uppercase text-[10px] border-b border-[#1E2D4A]">
                  <tr>
                    <th className="py-2 px-3">Event ID</th>
                    <th className="py-2 px-3">Action Type</th>
                    <th className="py-2 px-3">Operator</th>
                    <th className="py-2 px-3">Role</th>
                    <th className="py-2 px-3">State Transition</th>
                    <th className="py-2 px-3 text-right">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1E2D4A]/50 font-mono text-[11px]">
                  {auditLogs.map((log) => (
                    <tr key={log.event_id} className="hover:bg-[#141F36]">
                      <td className="py-2 px-3 text-[#38BDF8] font-bold">{log.event_id}</td>
                      <td className="py-2 px-3 text-[#F8FAFC] font-semibold">{log.event_type}</td>
                      <td className="py-2 px-3 text-[#CBD5E1]">{log.actor_username}</td>
                      <td className="py-2 px-3 text-[#94A3B8]">{log.actor_role}</td>
                      <td className="py-2 px-3">
                        <span className="text-[#64748B]">{log.previous_state || 'NONE'}</span>
                        <span className="mx-1.5 text-[#38BDF8]">→</span>
                        <span className="text-emerald-400 font-bold">{log.new_state}</span>
                      </td>
                      <td className="py-2 px-3 text-right text-[#64748B]">{log.timestamp}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="bg-[#0A0E17] border border-[#1E2D4A] rounded-md p-6 text-center text-[#94A3B8] space-y-1">
              <History className="w-6 h-6 mx-auto text-[#64748B] mb-2" />
              <p className="text-xs font-semibold text-[#F8FAFC]">No governance audit events registered yet</p>
              <p className="text-[11px]">
                Audit entries will be recorded here when review comments, approvals, or rejections occur.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Human Governance Approval Modal */}
      {planVersion && provenance === 'backend' && (
        <PlanApprovalModal
          isOpen={isApprovalOpen}
          onClose={() => setIsApprovalOpen(false)}
          planVersion={planVersion}
          validationSummary={validationResult || undefined}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      )}
    </>
  );
}
