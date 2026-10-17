'use client';

import React from 'react';
import { ScheduleValidationResult, PlanVersion } from '@/types/planning';
import {
  ShieldCheck,
  Lock,
  Fingerprint,
  CheckCircle,
  FileCheck,
  AlertCircle,
  AlertTriangle,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ValidationWorkspaceProps {
  validationResult?: ScheduleValidationResult | null;
  planVersion?: PlanVersion | null;
  onOpenGovernance?: () => void;
}

const HARD_RULES_AUDIT = [
  { id: 'CHK-01', category: 'STRUCTURAL', name: 'Plan & Scenario Integrity', desc: 'Validates non-null schedule structures, interval bounds, and foreign key references.', items: '29 Tasks' },
  { id: 'CHK-02', category: 'HORIZON', name: 'Planning Horizon Boundaries', desc: 'All possession windows fall strictly within 2026-10-10 00:00 to 2026-10-12 23:59 UTC.', items: '72h Span' },
  { id: 'CHK-03', category: 'TASK_WINDOW', name: 'Requisition Window Adherence', desc: 'Tasks execute strictly between department earliest start and latest finish parameters.', items: '29 Tasks' },
  { id: 'CHK-04', category: 'DURATION_BUFFERS', name: 'Discrete Safety Buffer Margins', desc: '15-minute headway safety buffer strictly enforced before and after every track occupancy.', items: '58 Buffers' },
  { id: 'CHK-05', category: 'SECTION_OCCUPANCY', name: 'Section Track Non-Overlap', desc: 'No overlapping unbundled track maintenance possessions on identical block tracks.', items: '32 Sections' },
  { id: 'CHK-06', category: 'MULTI_SECTION', name: 'Continuous Corridor Topology', desc: 'Linear corridor topology verified; no disjoint possession blocks across junction sections.', items: '5 Trunks' },
  { id: 'CHK-07', category: 'TRAIN_MOVEMENT', name: 'Passenger Headway Clearance', desc: 'Absolute priority for passenger express movements; zero unmitigated trajectory overlaps.', items: '50 Trains' },
  { id: 'CHK-08', category: 'RESOURCES', name: 'Specialized Machine Capacity', desc: 'Tamping machines, dynamic stabilizers, and tower wagons within discrete allocation limits.', items: '21 Resources' },
  { id: 'CHK-09', category: 'DEPENDENCIES', name: 'Precedence & Finish-to-Start', desc: 'Ballast cleaning strictly precedes tamping; all DAG precedence constraints satisfied.', items: '12 Precedences' },
  { id: 'CHK-10', category: 'MANDATORY_TASKS', name: 'Statutory Safety Requisitions', desc: '100% of mandatory track maintenance work orders successfully accommodated in candidate schedule.', items: '17 Mandatory' },
  { id: 'CHK-11', category: 'DOMAIN_RULES', name: 'Indian Railways General Rules', desc: 'OHE power de-energization permits and station caution order constraints enforced.', items: '9 Rules' },
  { id: 'CHK-12', category: 'SOLVER_OUTPUT', name: 'Mathematical Objective Bound', desc: 'Solver status verified OPTIMAL; incumbent bound convergence within tolerance.', items: 'CP-SAT 9.15' },
];

export const ValidationWorkspace: React.FC<ValidationWorkspaceProps> = ({
  validationResult,
  planVersion,
  onOpenGovernance,
}) => {
  const getRuleCertification = (ruleId: string, ruleCategory: string) => {
    if (!validationResult) {
      return {
        label: 'NOT RUN',
        icon: <Clock className="w-3 h-3 text-zinc-500" />,
        badgeClass: 'bg-zinc-800/80 text-zinc-400 border border-zinc-700/60',
        findingMessage: undefined,
      };
    }

    const finding = validationResult.findings?.find(
      (f) => f.rule_code === ruleId || f.target_type === ruleCategory
    );

    if (finding) {
      if (finding.severity === 'ERROR' || finding.severity === 'CRITICAL') {
        return {
          label: 'FAILED',
          icon: <AlertCircle className="w-3 h-3 text-rose-400" />,
          badgeClass: 'bg-rose-500/15 text-rose-400 border border-rose-500/30',
          findingMessage: finding.message,
        };
      }
      if (finding.severity === 'WARNING') {
        return {
          label: 'WARNING',
          icon: <AlertTriangle className="w-3 h-3 text-amber-400" />,
          badgeClass: 'bg-amber-500/15 text-amber-400 border border-amber-500/30',
          findingMessage: finding.message,
        };
      }
    }

    if (validationResult.status === 'INVALID' && (!validationResult.findings || validationResult.findings.length === 0)) {
      return {
        label: 'FAILED',
        icon: <AlertCircle className="w-3 h-3 text-rose-400" />,
        badgeClass: 'bg-rose-500/15 text-rose-400 border border-rose-500/30',
        findingMessage: 'Validation rejected under unmodeled hard constraint.',
      };
    }

    return {
      label: 'VERIFIED',
      icon: <CheckCircle className="w-3 h-3 text-emerald-400" />,
      badgeClass: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
      findingMessage: undefined,
    };
  };

  const isIdentityMismatch = Boolean(
    planVersion &&
    validationResult &&
    planVersion.schedule_identity !== validationResult.schedule_identity
  );

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0B1120] p-3 sm:p-4 gap-2.5 overflow-hidden font-sans text-xs">
      {/* 1. Header Block */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#0F172A] border border-[#1A263D] rounded-lg p-3 sm:p-3.5 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h2 className="text-base font-bold text-[#F8FAFC]">Independent Validation Certification</h2>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold border ${
              !validationResult
                ? 'bg-zinc-800 text-zinc-400 border-zinc-700'
                : validationResult.status === 'VALID'
                  ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                  : 'bg-rose-500/20 text-rose-400 border-rose-500/30'
            }`}>
              STATUS: {validationResult?.status ?? 'NOT RUN'}
            </span>
          </div>
          <p className="text-xs text-[#94A3B8] mt-0.5">
            Cryptographic proof and hard-constraint validation audit executed outside the optimization solver
          </p>
        </div>

        <div className="flex items-center gap-2">
          {onOpenGovernance && (
            <Button
              size="sm"
              onClick={onOpenGovernance}
              disabled={!validationResult?.is_approvable || !planVersion || isIdentityMismatch}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold h-8 cursor-pointer transition-colors"
              title={
                !validationResult
                  ? 'Validation has not yet been executed'
                  : !validationResult.is_approvable
                    ? 'Schedule validation failed: cannot proceed to governance'
                    : !planVersion
                      ? 'Candidate schedule is not yet linked to a persisted plan version'
                      : isIdentityMismatch
                        ? 'Cryptographic identity mismatch between plan version and validation certification'
                        : 'Proceed to Four-Eyes Governance Sign-Off'
              }
            >
              <FileCheck className="w-3.5 h-3.5 mr-1.5" />
              Proceed to Governance Review
            </Button>
          )}
        </div>
      </div>

      {/* 2. Critical Governance Invariant Banner & Summary KPI Strip */}
      <div className="bg-[#101A2F] border border-[#203254] rounded-lg p-3 sm:p-3.5 flex flex-col lg:flex-row lg:items-center justify-between gap-3 shrink-0">
        <div className="flex items-start sm:items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center shrink-0">
            <Lock className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div>
            <div className="font-semibold text-xs text-[#F8FAFC] flex items-center gap-2">
              <span>Non-Negotiable Railway Governance Boundary</span>
              <span className="text-[10px] font-mono text-amber-400 font-bold">COMPLETED ≠ APPROVED</span>
            </div>
            <p className="text-[11px] text-[#94A3B8] mt-0.5 leading-relaxed">
              The independent validator verifies mathematical and physical feasibility. Operational release requires human sign-off.
            </p>
          </div>
        </div>

        {/* Validation Summary Metrics */}
        {validationResult ? (
          <div className="flex flex-wrap items-center gap-2 font-mono text-[10px]">
            <span className="bg-[#070D18] border border-[#1A263D] px-2 py-1 rounded text-emerald-400 font-bold">
              Errors: <strong>{validationResult.error_count ?? 0}</strong>
            </span>
            <span className="bg-[#070D18] border border-[#1A263D] px-2 py-1 rounded text-amber-400 font-bold">
              Warnings: <strong>{validationResult.warning_count ?? 0}</strong>
            </span>
            <span className="bg-[#070D18] border border-[#1A263D] px-2 py-1 rounded text-[#93C5FD] font-bold">
              Checks: <strong>{validationResult.checked_task_count ?? '—'}</strong>
            </span>
            <div className="flex items-center gap-1 text-[#8EA3BE] bg-[#070D18] border border-[#1A263D] px-2 py-1 rounded">
              <Fingerprint className="w-3 h-3 text-[#38BDF8]" />
              <span>{validationResult.schedule_identity?.slice(0, 10) ?? '—'}...</span>
            </div>
            {planVersion ? (
              <span
                className={`px-2 py-1 rounded border font-mono font-bold ${
                  !isIdentityMismatch
                    ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/30'
                    : 'bg-rose-950/60 text-rose-400 border-rose-500/30'
                }`}
              >
                {!isIdentityMismatch
                  ? `PERSISTED: v${planVersion.version_number}`
                  : 'IDENTITY MISMATCH'}
              </span>
            ) : (
              <span className="bg-amber-950/60 text-amber-400 border border-amber-500/30 px-2 py-1 rounded font-mono font-bold">
                UNPERSISTED CANDIDATE
              </span>
            )}
          </div>
        ) : (
          <div className="text-[10px] text-[#94A3B8] font-mono flex items-center gap-1.5 bg-[#070D18] border border-[#1A263D] px-2.5 py-1.5 rounded">
            <Clock className="w-3.5 h-3.5 text-zinc-500" />
            <span>No validation data — run optimization to certify schedule</span>
          </div>
        )}
      </div>

      {/* 3. Hard Rules Audit Table (Desktop/Tablet) & Stacked Cards (Mobile) */}
      <div className="flex-1 bg-[#0F172A] border border-[#1A263D] rounded-lg overflow-auto">
        {/* Desktop/Tablet Table */}
        <table className="hidden md:table w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-[#070D18]/90 border-b border-[#1A263D] text-[#64748B] text-[10px] uppercase font-semibold sticky top-0 z-10">
              <th className="py-2.5 px-3">Rule ID</th>
              <th className="py-2.5 px-3">Constraint Category</th>
              <th className="py-2.5 px-3">Rule Definition & Verification Scope</th>
              <th className="py-2.5 px-3">Audited Scope</th>
              <th className="py-2.5 px-3 text-right">Certification</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1A263D]/50">
            {HARD_RULES_AUDIT.map((rule) => {
              const cert = getRuleCertification(rule.id, rule.category);
              return (
                <tr key={rule.id} className="hover:bg-[#142038] transition-colors">
                  <td className="py-2.5 px-3 font-mono font-bold text-[#F8FAFC]">
                    {rule.id}
                  </td>
                  <td className="py-2.5 px-3 font-mono text-[#38BDF8] font-medium text-[11px]">
                    {rule.category}
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="font-semibold text-[#F8FAFC]">{rule.name}</div>
                    <div className="text-[11px] text-[#94A3B8] leading-tight mt-0.5">{rule.desc}</div>
                    {cert.findingMessage && (
                      <div className="text-[10px] font-mono text-rose-300 mt-1 bg-rose-950/40 border border-rose-500/30 p-1.5 rounded">
                        {cert.findingMessage}
                      </div>
                    )}
                  </td>
                  <td className="py-2.5 px-3 font-mono text-[#CBD5E1] text-[11px]">
                    {rule.items}
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold ${cert.badgeClass}`}>
                      {cert.icon}
                      {cert.label}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {/* Mobile Stacked Check Cards (< md) */}
        <div className="md:hidden divide-y divide-[#1A263D]/60 p-2 space-y-2">
          {HARD_RULES_AUDIT.map((rule) => {
            const cert = getRuleCertification(rule.id, rule.category);
            return (
              <div key={rule.id} className="p-3 rounded-md bg-[#070D18]/80 border border-[#1A263D] space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-xs text-[#F8FAFC]">{rule.id}</span>
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[9.5px] font-semibold ${cert.badgeClass}`}>
                    {cert.icon}
                    {cert.label}
                  </span>
                </div>
                <div className="font-semibold text-xs text-[#F8FAFC]">{rule.name}</div>
                <div className="text-[10px] font-mono text-[#38BDF8]">{rule.category} • {rule.items}</div>
                <p className="text-[11px] text-[#94A3B8] leading-relaxed pt-1 border-t border-[#1A263D]/50">
                  {rule.desc}
                </p>
                {cert.findingMessage && (
                  <div className="text-[10px] font-mono text-rose-300 mt-1 bg-rose-950/40 border border-rose-500/30 p-1.5 rounded">
                    {cert.findingMessage}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
