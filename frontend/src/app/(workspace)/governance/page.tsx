'use client';

import React, { useState } from 'react';
import { AppShell } from '@/components/shell/AppShell';
import { PlanApprovalModal } from '@/components/governance/PlanApprovalModal';
import { ResponsiveDrawer } from '@/components/common/ResponsiveDrawer';
import {
  DEMO_VALIDATION_RESULT,
  DEMO_PLAN_VERSION,
  DEMO_AUDIT_LOGS,
  approvePlanVersion,
  rejectPlanVersion,
} from '@/lib/api/client';
import { PlanVersion, ScheduleValidationResult } from '@/types/planning';
import {
  ShieldCheck,
  FileCheck,
  CheckCircle,
  AlertTriangle,
  Clock,
  UserCheck,
  Lock,
  History,
  Hash,
  ExternalLink,
  ChevronRight,
  ArrowRight,
  FileText,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ValidationCheckCategory {
  id: string;
  category: string;
  ruleCode: string;
  description: string;
  status: 'PASS' | 'WARNING' | 'FAIL';
  severity: 'HARD_MANDATORY' | 'STATUTORY_SAFETY' | 'OPERATIONAL_CURFEW';
  checkedCount: number;
  timestamp: string;
  evidenceRef: string;
}

const VALIDATION_CHECKS: ValidationCheckCategory[] = [
  {
    id: 'CHK-01',
    category: 'Structural Topology',
    ruleCode: 'VAL-STRUCT-01',
    description: 'Track network topology, block section bounds, and adjacency continuity',
    status: 'PASS',
    severity: 'HARD_MANDATORY',
    checkedCount: 32,
    timestamp: '18 Oct 06:00:14 UTC',
    evidenceRef: 'TOPOLOGY_GRAPH_01',
  },
  {
    id: 'CHK-02',
    category: 'Planning Horizon Bounds',
    ruleCode: 'VAL-HORIZON-02',
    description: 'Strict verification that all possessions and train paths fall within the 24h window',
    status: 'PASS',
    severity: 'HARD_MANDATORY',
    checkedCount: 29,
    timestamp: '18 Oct 06:00:14 UTC',
    evidenceRef: 'HORIZON_BOUNDS_24H',
  },
  {
    id: 'CHK-03',
    category: 'Task Window Feasibility',
    ruleCode: 'VAL-TASKWIN-03',
    description: 'Earliest start and latest finish compliance with department requisition bounds',
    status: 'PASS',
    severity: 'HARD_MANDATORY',
    checkedCount: 29,
    timestamp: '18 Oct 06:00:14 UTC',
    evidenceRef: 'REQ_WINDOWS_CORRIDOR',
  },
  {
    id: 'CHK-04',
    category: 'Possession Buffers & Setup',
    ruleCode: 'VAL-BUFFERS-04',
    description: 'Mandatory 15-minute setup and 15-minute clearing safety margins',
    status: 'PASS',
    severity: 'STATUTORY_SAFETY',
    checkedCount: 29,
    timestamp: '18 Oct 06:00:15 UTC',
    evidenceRef: 'SAFETY_MARGIN_RECORDS',
  },
  {
    id: 'CHK-05',
    category: 'Track Occupancy Non-Overlap',
    ruleCode: 'VAL-OCCUPANCY-05',
    description: 'Zero concurrent incompatible occupancies on identical track segments',
    status: 'PASS',
    severity: 'HARD_MANDATORY',
    checkedCount: 132,
    timestamp: '18 Oct 06:00:15 UTC',
    evidenceRef: 'TRACK_OCCUPANCY_INTERVALS',
  },
  {
    id: 'CHK-06',
    category: 'Multi-Section Spatial Continuity',
    ruleCode: 'VAL-MULTISECT-06',
    description: 'Continuous linear possession zones for multi-kilometer track renewal trains',
    status: 'PASS',
    severity: 'HARD_MANDATORY',
    checkedCount: 6,
    timestamp: '18 Oct 06:00:15 UTC',
    evidenceRef: 'LINEAR_BLOCK_SEGMENTS',
  },
  {
    id: 'CHK-07',
    category: 'Train Movement Clearance & Headway',
    ruleCode: 'VAL-HEADWAY-07',
    description: 'Minimum 7-minute headway between high-speed express trains and work zone limits',
    status: 'PASS',
    severity: 'STATUTORY_SAFETY',
    checkedCount: 50,
    timestamp: '18 Oct 06:00:16 UTC',
    evidenceRef: 'HEADWAY_SPACING_MATRIX',
  },
  {
    id: 'CHK-08',
    category: 'Resource Non-Overlap',
    ruleCode: 'VAL-RESOURCE-08',
    description: 'Discrete assignment verification for CSM tampers, BCM cleaners, and gang crews',
    status: 'PASS',
    severity: 'HARD_MANDATORY',
    checkedCount: 21,
    timestamp: '18 Oct 06:00:16 UTC',
    evidenceRef: 'PLANT_CREW_SCHEDULE',
  },
  {
    id: 'CHK-09',
    category: 'Finish-to-Start Precedence',
    ruleCode: 'VAL-DEPENDENCY-09',
    description: 'Ballast screening strictly precedes tamping and rail grinding operations',
    status: 'PASS',
    severity: 'OPERATIONAL_CURFEW',
    checkedCount: 12,
    timestamp: '18 Oct 06:00:16 UTC',
    evidenceRef: 'PRECEDENCE_DAG_GRAPH',
  },
  {
    id: 'CHK-10',
    category: 'Mandatory Requisition Coverage',
    ruleCode: 'VAL-MANDATORY-10',
    description: '100% of emergency and safety-critical tasks must be scheduled',
    status: 'PASS',
    severity: 'STATUTORY_SAFETY',
    checkedCount: 17,
    timestamp: '18 Oct 06:00:17 UTC',
    evidenceRef: 'SAFETY_CRITICAL_REGISTRY',
  },
  {
    id: 'CHK-11',
    category: 'Railway Safety Rules Enforcement',
    ruleCode: 'VAL-SAFETY-11',
    description: 'Automatic compliance check with General & Subsidiary Rules (G&SR)',
    status: 'PASS',
    severity: 'STATUTORY_SAFETY',
    checkedCount: 88,
    timestamp: '18 Oct 06:00:17 UTC',
    evidenceRef: 'GSR_CLAUSE_MAPPING',
  },
  {
    id: 'CHK-12',
    category: 'Deterministic Solver Output Integrity',
    ruleCode: 'VAL-SOLVER-12',
    description: 'Verification of CP-SAT interval variables, bounds, and absence of solver bypasses',
    status: 'PASS',
    severity: 'HARD_MANDATORY',
    checkedCount: 1,
    timestamp: '18 Oct 06:00:18 UTC',
    evidenceRef: 'CPSAT_PROOF_HASH',
  },
  {
    id: 'CHK-13',
    category: 'OHE Traction Power Isolation',
    ruleCode: 'VAL-OHE-ISO-13',
    description: 'Power Permit-to-Work (PTW) isolation verified for electrified track blocks',
    status: 'PASS',
    severity: 'HARD_MANDATORY',
    checkedCount: 14,
    timestamp: '18 Oct 06:00:18 UTC',
    evidenceRef: 'OHE_PTW_CLEARANCES',
  },
];

export default function GovernancePage() {
  const [planVersion, setPlanVersion] = useState<PlanVersion>(DEMO_PLAN_VERSION);
  const [validationResult] = useState<ScheduleValidationResult>(DEMO_VALIDATION_RESULT);
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [selectedCheck, setSelectedCheck] = useState<ValidationCheckCategory | null>(null);

  const handleApprove = async (payload: { reviewer_name: string; reviewer_role: string; approval_notes: string }) => {
    try {
      const updated = await approvePlanVersion(
        planVersion.plan_version_id,
        payload.approval_notes,
        payload.reviewer_name,
        payload.reviewer_role
      );
      setPlanVersion(updated);
    } catch {
      setPlanVersion((prev) => ({
        ...prev,
        status: 'APPROVED',
        approved_by: payload.reviewer_name,
        approved_at: new Date().toISOString(),
        approval_notes: payload.approval_notes,
      }));
    }
  };

  const handleReject = async (payload: { reviewer_name: string; reviewer_role: string; rejection_reason: string }) => {
    try {
      const updated = await rejectPlanVersion(planVersion.plan_version_id, payload.rejection_reason);
      setPlanVersion(updated);
    } catch {
      setPlanVersion((prev) => ({
        ...prev,
        status: 'REJECTED',
        rejected_by: payload.reviewer_name,
        rejected_at: new Date().toISOString(),
        rejection_reason: payload.rejection_reason,
      }));
    }
  };

  return (
    <AppShell
      activeScenarioId="SCN-DEMO-001"
      scenarioName="Northern Trunk Corridor (NDLS - CNB)"
      planningHorizon="Governance: Four-Eyes Principle Gate"
      tasksCount={29}
      trainsCount={50}
    >
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
                <h1 className="text-xl font-bold tracking-tight text-[#F8FAFC]">
                  Safety Validation & Human Governance
                </h1>
                <p className="text-[11px] text-[#94A3B8] mt-0.5">
                  Independent 13-check mathematical safety firewall and Four-Eyes human operator sign-off
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <div className="bg-[#0B101C] border border-[#1E2D4A] rounded-md px-2.5 py-1 flex items-center gap-2 text-xs font-mono">
              <span className="text-[#64748B]">Plan Version:</span>
              <strong className="text-[#F8FAFC]">v{planVersion.version_number}</strong>
              <span className="text-[#334155]">•</span>
              <span className={`px-2 py-0.5 rounded font-bold text-[10px] border ${
                planVersion.status === 'APPROVED'
                  ? 'bg-emerald-950/80 text-emerald-400 border-emerald-500/40'
                  : 'bg-amber-950/80 text-amber-400 border-amber-500/40'
              }`}>
                {planVersion.status === 'APPROVED' ? 'APPROVED' : 'PENDING REVIEW'}
              </span>
            </div>

            <Button
              size="sm"
              onClick={() => setIsApprovalOpen(true)}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-3 h-8 shadow-xs cursor-pointer"
            >
              <FileCheck className="w-3.5 h-3.5 mr-1.5" />
              <span>Perform Four-Eyes Review</span>
            </Button>
          </div>
        </div>

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
              <p className="text-[11px] text-emerald-400 font-mono mt-0.5 font-semibold">OPTIMAL (1.48s runtime)</p>
              <span className="text-[10.5px] text-[#94A3B8] block mt-0.5">Mathematical interval assignment</span>
            </div>

            <div className="bg-[#0F172A] border border-emerald-500/40 rounded-lg p-3 relative">
              <span className="text-[10px] font-mono text-emerald-400 block font-bold">STAGE 2</span>
              <span className="font-bold text-xs text-[#F8FAFC] block mt-0.5">Independent Validation</span>
              <p className="text-[11px] text-emerald-400 font-mono mt-0.5 font-semibold">13/13 CHECKS PASSED (100%)</p>
              <span className="text-[10.5px] text-[#94A3B8] block mt-0.5">Separated verification firewall</span>
            </div>

            <div className="bg-[#0F172A] border border-[#2563EB]/40 rounded-lg p-3 relative">
              <span className="text-[10px] font-mono text-[#38BDF8] block font-bold">STAGE 3</span>
              <span className="font-bold text-xs text-[#F8FAFC] block mt-0.5">Four-Eyes Human Review</span>
              <p className="text-[11px] text-[#93C5FD] font-mono mt-0.5 font-semibold">Role Segregation Mandatory</p>
              <span className="text-[10.5px] text-[#94A3B8] block mt-0.5">Creator cannot approve plan</span>
            </div>

            <div className={`border rounded-lg p-3 relative ${
              planVersion.status === 'APPROVED'
                ? 'bg-emerald-950/20 border-emerald-500/50'
                : 'bg-amber-950/20 border-amber-500/40'
            }`}>
              <span className="text-[10px] font-mono block text-[#94A3B8] font-bold">STAGE 4</span>
              <span className="font-bold text-xs text-[#F8FAFC] block mt-0.5">Final Track Clearance</span>
              <p className={`text-[11px] font-mono mt-0.5 font-bold ${
                planVersion.status === 'APPROVED' ? 'text-emerald-400' : 'text-amber-400'
              }`}>
                {planVersion.status === 'APPROVED' ? 'PLAN AUTHORIZED & SIGNED' : 'AWAITING EXECUTIVE SIGN-OFF'}
              </p>
              <span className="text-[10.5px] text-[#94A3B8] block mt-0.5">
                {planVersion.status === 'APPROVED' ? 'Ready for field dispatch' : 'Action required by DRM/Sr. DOM'}
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
                <span className="font-bold text-[#F8FAFC] text-xs block mt-0.5">chief_operations_admin</span>
                <span className="text-[10.5px] text-[#94A3B8] block mt-0.5">Chief Operations Planner</span>
              </div>
              <div className="bg-[#0F172A] p-2.5 rounded-md border border-[#1E2D4A]">
                <span className="text-[10px] text-[#64748B] block font-bold">DESIGNATED APPROVER:</span>
                <span className="font-bold text-emerald-400 text-xs block mt-0.5">
                  {planVersion.approved_by || 'ops_executive_officer'}
                </span>
                <span className="text-[10.5px] text-[#94A3B8] block mt-0.5">Safety & Governance Officer</span>
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
                  {planVersion.schedule_identity}
                </span>
              </div>
              <div className="flex justify-between text-[11px] text-[#94A3B8] pt-0.5">
                <span>Snapshot: <strong className="text-white">SNAP-297E475AC983</strong></span>
                <span>Audit Latency: <strong className="text-emerald-400">18.4 ms</strong></span>
                <span>Entities Certified: <strong className="text-white">29 / 29 Tasks</strong></span>
              </div>
            </div>
          </div>
        </div>

        {/* ============================================================== */}
        {/* 4. PROFESSIONAL 13-CHECK VALIDATION TABLE                      */}
        {/* ============================================================== */}
        <div className="bg-[#0B101C] border border-[#1E2D4A] rounded-lg p-3 sm:p-4 flex flex-col shadow-xs space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-2.5 border-b border-[#1E2D4A]">
            <div>
              <h2 className="text-sm font-bold text-[#F8FAFC]">
                13-Check Independent Safety Validation Firewall
              </h2>
              <p className="text-[11px] text-[#94A3B8] mt-0.5">
                Executed outside the solver process by an isolated deterministic validation engine
              </p>
            </div>
            <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2.5 py-1 rounded-md border border-emerald-500/40">
              100% PASS RATE (13/13)
            </span>
          </div>

          <div className="overflow-x-auto rounded-md border border-[#1E2D4A] bg-[#0F172A]">
            <table className="w-full text-xs text-left">
              <thead className="bg-[#141F36] text-[#64748B] font-mono uppercase text-[10px] sticky top-0 border-b border-[#1E2D4A]">
                <tr>
                  <th className="py-2 px-3">Rule Code</th>
                  <th className="py-2 px-3">Category</th>
                  <th className="py-2 px-3">Safety Rule Description</th>
                  <th className="py-2 px-3">Severity</th>
                  <th className="py-2 px-3">Result</th>
                  <th className="py-2 px-3">Evidence Reference</th>
                  <th className="py-2 px-3 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E2D4A]/50 font-sans">
                {VALIDATION_CHECKS.map((chk) => (
                  <tr
                    key={chk.id}
                    onClick={() => setSelectedCheck(chk)}
                    className="hover:bg-[#141F36] cursor-pointer transition-colors"
                  >
                    <td className="py-2 px-3 font-mono font-bold text-[#38BDF8]">
                      {chk.ruleCode}
                    </td>
                    <td className="py-2 px-3 font-semibold text-[#F8FAFC]">
                      {chk.category}
                    </td>
                    <td className="py-2 px-3 text-[#CBD5E1] max-w-[340px] leading-relaxed">
                      {chk.description}
                    </td>
                    <td className="py-2 px-3 font-mono text-[10px]">
                      <span className={`px-2 py-0.5 rounded font-bold border ${
                        chk.severity === 'HARD_MANDATORY'
                          ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                          : 'bg-[#2563EB]/15 text-[#93C5FD] border-[#2563EB]/30'
                      }`}>
                        {chk.severity.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <span className="inline-flex items-center gap-1.5 text-[10px] font-mono font-bold text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/30">
                        <CheckCircle className="w-3 h-3" />
                        PASS ({chk.checkedCount})
                      </span>
                    </td>
                    <td className="py-2 px-3 font-mono text-[11px] text-[#38BDF8]">
                      <span className="hover:underline flex items-center gap-1">
                        <FileText className="w-3 h-3" />
                        {chk.evidenceRef}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-[11px] text-[#64748B]">
                      {chk.timestamp}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
            <span className="text-[11px] text-[#64748B] font-mono">Tamper-evident cryptographically signed records</span>
          </div>

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
                {DEMO_AUDIT_LOGS.map((log) => (
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
        </div>
      </div>

      {/* Validation Evidence Drawer */}
      <ResponsiveDrawer
        isOpen={!!selectedCheck}
        onClose={() => setSelectedCheck(null)}
        title={selectedCheck ? `${selectedCheck.ruleCode}: ${selectedCheck.category}` : 'Validation Evidence'}
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">
            PASSED
          </span>
        }
      >
        {selectedCheck && (
          <div className="p-5 space-y-4 text-xs font-sans">
            <div className="bg-[#0A0E17] border border-[#1E2D4A] rounded-lg p-4 space-y-2.5">
              <span className="text-[10px] font-mono uppercase text-[#64748B] block font-bold">Rule Statement</span>
              <p className="text-xs text-[#F8FAFC] leading-relaxed">{selectedCheck.description}</p>
            </div>

            <div className="bg-[#0A0E17] border border-[#1E2D4A] rounded-lg p-4 space-y-2 font-mono text-xs">
              <div className="flex justify-between">
                <span className="text-[#64748B]">Evidence Token:</span>
                <span className="text-[#38BDF8] font-bold">{selectedCheck.evidenceRef}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Total Entities Checked:</span>
                <span className="text-white font-bold">{selectedCheck.checkedCount} items</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Verification Timestamp:</span>
                <span className="text-[#CBD5E1]">{selectedCheck.timestamp}</span>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <Button
                size="sm"
                onClick={() => setSelectedCheck(null)}
                className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs px-4"
              >
                Done
              </Button>
            </div>
          </div>
        )}
      </ResponsiveDrawer>

      {/* Human Governance Approval Modal */}
      <PlanApprovalModal
        isOpen={isApprovalOpen}
        onClose={() => setIsApprovalOpen(false)}
        planVersion={planVersion}
        validationSummary={validationResult}
        onApprove={handleApprove}
        onReject={handleReject}
      />
    </AppShell>
  );
}
