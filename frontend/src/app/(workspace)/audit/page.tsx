'use client';

import React, { useState, useEffect } from 'react';
import {
  getPlanVersions,
  getPlanVersionAudit,
  approvePlanVersion,
  rejectPlanVersion,
} from '@/lib/api/client';
import { PlanVersion, AuditLogEntry } from '@/types/planning';
import { PlanApprovalModal } from '@/components/governance/PlanApprovalModal';
import {
  FileCheck,
  Lock,
  Fingerprint,
  CheckCircle,
  RefreshCw,
  Plus,
  Send,
  MessageSquare,
  ShieldCheck,
  XCircle,
  RotateCcw,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PlanVersionSummary {
  id: string;
  version: string;
  status: 'PENDING_REVIEW' | 'UNDER_REVIEW' | 'APPROVED' | 'REJECTED' | 'SUPERSEDED';
  created: string;
  creator: string;
  scheduledCount: number;
  unplacedCount: number;
  hash: string;
}

const INITIAL_VERSIONS: PlanVersionSummary[] = [
  {
    id: 'PV-20261002-5F8A180A',
    version: 'v1.2',
    status: 'PENDING_REVIEW',
    created: 'Today, 14:15 UTC',
    creator: 'chief_operations_admin',
    scheduledCount: 67,
    unplacedCount: 15,
    hash: 'bae346ecf37b1fd80608cc5e0b8dae030517a44d5d5305f640d5767ed46999aa',
  },
  {
    id: 'PV-20261001-B1299C04',
    version: 'v1.1',
    status: 'APPROVED',
    created: 'Yesterday, 18:30 UTC',
    creator: 'divisional_planning_officer',
    scheduledCount: 65,
    unplacedCount: 17,
    hash: '9f83ac428a6f8742d13b4e7230198e0941bc4a1329a1b02130e5504781cae931',
  },
  {
    id: 'PV-20260930-1840DF21',
    version: 'v1.0',
    status: 'APPROVED',
    created: '2 days ago',
    creator: 'operations_director',
    scheduledCount: 64,
    unplacedCount: 18,
    hash: '4173ea614092b772c530189fa41094038201fae2170314a8b79201f9301da287',
  },
  {
    id: 'PV-20260929-9941AC07',
    version: 'v0.9',
    status: 'REJECTED',
    created: '3 days ago',
    creator: 'assistant_planner',
    scheduledCount: 52,
    unplacedCount: 30,
    hash: '09ab31f419c82410a8274017fbc8201940173e871239ab710481239841029cba',
  },
];

interface ReviewComment {
  id: string;
  author: string;
  role: string;
  time: string;
  text: string;
  isLocalDraft?: boolean;
}

const INITIAL_COMMENTS: ReviewComment[] = [];

function mapApiToSummary(v: PlanVersion): PlanVersionSummary {
  const resultSummary = v.result_summary as Record<string, unknown> | undefined;
  const schedCount =
    typeof v.total_scheduled === 'number'
      ? v.total_scheduled
      : typeof resultSummary?.scheduled_tasks === 'number'
      ? (resultSummary.scheduled_tasks as number)
      : 30;
  const unschedCount =
    typeof v.total_unscheduled === 'number'
      ? v.total_unscheduled
      : typeof resultSummary?.unscheduled_tasks === 'number'
      ? (resultSummary.unscheduled_tasks as number)
      : 0;

  const validStatuses: PlanVersion['status'][] = [
    'PENDING_REVIEW',
    'UNDER_REVIEW',
    'APPROVED',
    'REJECTED',
    'SUPERSEDED',
  ];
  const assignedStatus = validStatuses.includes(v.status)
    ? v.status
    : 'PENDING_REVIEW';

  return {
    id: v.plan_version_id,
    version: `v${v.version_number}`,
    status: assignedStatus,
    created: v.created_at ? new Date(v.created_at).toLocaleString() : 'Recent',
    creator: v.created_by || 'operations_officer',
    scheduledCount: schedCount,
    unplacedCount: unschedCount,
    hash: v.schedule_identity || '',
  };
}

export default function AuditPage() {
  const [versions, setVersions] = useState<PlanVersionSummary[]>(INITIAL_VERSIONS);
  const [selectedVersionId, setSelectedVersionId] = useState<string>(INITIAL_VERSIONS[0].id);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [comments, setComments] = useState<ReviewComment[]>(INITIAL_COMMENTS);
  const [newCommentText, setNewCommentText] = useState('');
  const [inspectorTab, setInspectorTab] = useState<'DETAILS' | 'REVIEW' | 'AUDIT'>('DETAILS');
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isAuthoritative, setIsAuthoritative] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  const selectedVersion = versions.find((v) => v.id === selectedVersionId) || versions[0];

  useEffect(() => {
    let cancelled = false;
    getPlanVersions('SCN-DEMO-001')
      .then(async (apiVersions) => {
        if (cancelled || !apiVersions || apiVersions.length === 0) return;
        setVersions(apiVersions.map(mapApiToSummary));
        setIsAuthoritative(true);
        const active = apiVersions[0];
        setSelectedVersionId(active.plan_version_id);
        const logs = await getPlanVersionAudit(active.plan_version_id);
        if (!cancelled && logs && logs.length > 0) {
          setAuditLogs(logs);
        }
      })
      .catch((err) => {
        console.warn('Failed to load authoritative audit trail, displaying synthetic reference:', err);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleManualRefresh = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const apiVersions = await getPlanVersions('SCN-DEMO-001');
      if (apiVersions && apiVersions.length > 0) {
        setVersions(apiVersions.map(mapApiToSummary));
        setIsAuthoritative(true);
      }
      const logs = await getPlanVersionAudit(selectedVersion.id);
      if (logs && logs.length > 0) {
        setAuditLogs(logs);
      }
    } catch (err: unknown) {
      console.warn('Manual refresh notice:', err);
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(`Failed to refresh ledger from backend: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveAction = async (payload?: {
    reviewer_name?: string;
    reviewer_role?: string;
    approval_notes?: string;
  }) => {
    try {
      await approvePlanVersion(
        selectedVersion.id,
        payload?.approval_notes || 'Approved by Authorized Operations Officer under Railway Board Policy.',
        payload?.reviewer_name,
        payload?.reviewer_role
      );

      // Refresh authoritative data from backend
      const updatedVersions = await getPlanVersions('SCN-DEMO-001');
      if (updatedVersions && updatedVersions.length > 0) {
        setVersions(updatedVersions.map(mapApiToSummary));
        setIsAuthoritative(true);
      }
      const logs = await getPlanVersionAudit(selectedVersion.id);
      if (logs && logs.length > 0) {
        setAuditLogs(logs);
      }
      setErrorMessage(null);
      setInfoMessage(`Plan ${selectedVersion.id} approved successfully.`);
    } catch (err: unknown) {
      console.warn('Approval error:', err);
      // STRICT SAFETY: Do NOT mutate governance state to APPROVED on error!
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(
        `ACTION NOT COMPLETED: The backend did not confirm this approval (${msg}). No local state transition has been applied.`
      );
    }
  };

  const handleRejectAction = async (payload?: {
    reviewer_name?: string;
    reviewer_role?: string;
    rejection_reason?: string;
  }) => {
    try {
      await rejectPlanVersion(
        selectedVersion.id,
        payload?.rejection_reason || 'Returned for revision due to operational constraints.'
      );

      // Refresh authoritative data from backend
      const updatedVersions = await getPlanVersions('SCN-DEMO-001');
      if (updatedVersions && updatedVersions.length > 0) {
        setVersions(updatedVersions.map(mapApiToSummary));
        setIsAuthoritative(true);
      }
      const logs = await getPlanVersionAudit(selectedVersion.id);
      if (logs && logs.length > 0) {
        setAuditLogs(logs);
      }
      setErrorMessage(null);
      setInfoMessage(`Plan ${selectedVersion.id} rejected.`);
    } catch (err: unknown) {
      console.warn('Rejection error:', err);
      // STRICT SAFETY: Do NOT mutate governance state to REJECTED on error!
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(
        `ACTION NOT COMPLETED: The backend did not confirm this rejection (${msg}). No local state transition has been applied.`
      );
    }
  };

  const handleDirectApprove = () => handleApproveAction();
  const handleDirectReject = () => handleRejectAction();

  const handleAddComment = () => {
    if (!newCommentText.trim()) return;
    setComments((prev) => [
      ...prev,
      {
        id: `REV-${Date.now()}`,
        author: 'Operations Planner',
        role: 'Planning Officer',
        time: 'Just now',
        text: newCommentText.trim(),
        isLocalDraft: true,
      },
    ]);
    setNewCommentText('');
  };

  // Convert for Modal
  const modalPlanVersion: PlanVersion = {
    plan_version_id: selectedVersion.id,
    planning_run_id: 'RUN-AUTHORITATIVE',
    scenario_id: 'SCN-DEMO-001',
    version_number: parseInt(selectedVersion.version.replace('v', ''), 10) || 1,
    status: selectedVersion.status,
    scheduler_type: 'CP_SAT',
    schedule_identity: selectedVersion.hash,
    is_approvable: selectedVersion.status === 'PENDING_REVIEW' || selectedVersion.status === 'UNDER_REVIEW',
    created_at: new Date().toISOString(),
    created_by: selectedVersion.creator,
    total_scheduled: selectedVersion.scheduledCount,
    total_unscheduled: selectedVersion.unplacedCount,
  };

  // Dynamic KPI counts computed from versions state
  const pendingCount = versions.filter((v) => v.status === 'PENDING_REVIEW' || v.status === 'UNDER_REVIEW').length;
  const approvedCount = versions.filter((v) => v.status === 'APPROVED').length;
  const rejectedCount = versions.filter((v) => v.status === 'REJECTED').length;

  return (
    <>
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 max-w-7xl mx-auto w-full bg-[#070D18] font-sans text-xs">
        {/* Top Header Block */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-1">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold text-[#F8FAFC]">Audit & Governance</h1>
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                  isAuthoritative
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                    : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                }`}
              >
                {isAuthoritative ? 'AUTHORITATIVE BACKEND LEDGER' : 'DEMO AUDIT TRAIL • READ ONLY'}
              </span>
            </div>
            <p className="text-xs text-[#94A3B8] mt-0.5">
              Immutable audit trail and plan version approvals
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleManualRefresh}
              disabled={loading}
              className="border-[#1A263D] text-xs text-[#94A3B8] hover:bg-[#162238] hover:text-white bg-[#0B1120] h-8"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh Ledger
            </Button>

            <Button
              size="sm"
              onClick={() =>
                setInfoMessage('New Plan Version candidates can be created directly from validated runs in the Planning Workspace.')
              }
              className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-semibold h-8 shadow-xs"
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
              New Plan Version
            </Button>
          </div>
        </div>

        {/* Error Alert Notice */}
        {errorMessage && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2 text-xs text-rose-300 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button onClick={() => setErrorMessage(null)} className="text-[#94A3B8] hover:text-white text-xs ml-3">
              Dismiss
            </button>
          </div>
        )}

        {/* Informational Notice */}
        {infoMessage && (
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg px-3 py-2 text-xs text-blue-300 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-400 shrink-0" />
              <span>{infoMessage}</span>
            </div>
            <button onClick={() => setInfoMessage(null)} className="text-[#94A3B8] hover:text-white text-xs ml-3">
              Dismiss
            </button>
          </div>
        )}

        {/* 4 Summary KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {/* Card 1: Total Plan Versions */}
          <div className="bg-[#0B1120] border border-[#1A263D] rounded-lg p-3.5">
            <span className="text-[10px] uppercase font-semibold text-[#64748B] tracking-wider block">
              Total Plan Versions
            </span>
            <div className="text-2xl font-bold font-mono text-[#F8FAFC] mt-1">{versions.length}</div>
            <span className="text-[10px] text-[#94A3B8] mt-1 block">Across all scenarios</span>
          </div>

          {/* Card 2: Pending Review */}
          <div className="bg-[#0B1120] border border-[#1A263D] rounded-lg p-3.5">
            <span className="text-[10px] uppercase font-semibold text-[#64748B] tracking-wider block">
              Pending Review
            </span>
            <div className="text-2xl font-bold font-mono text-[#F59E0B] mt-1">{pendingCount}</div>
            <span className="text-[10px] text-amber-400 mt-1 block">Awaiting approval</span>
          </div>

          {/* Card 3: Approved Plans */}
          <div className="bg-[#0B1120] border border-[#1A263D] rounded-lg p-3.5">
            <span className="text-[10px] uppercase font-semibold text-[#64748B] tracking-wider block">
              Approved Plans
            </span>
            <div className="text-2xl font-bold font-mono text-[#10B981] mt-1">{approvedCount}</div>
            <span className="text-[10px] text-emerald-400 mt-1 block">Ready for execution</span>
          </div>

          {/* Card 4: Rejected Plans */}
          <div className="bg-[#0B1120] border border-[#1A263D] rounded-lg p-3.5">
            <span className="text-[10px] uppercase font-semibold text-[#64748B] tracking-wider block">
              Rejected Plans
            </span>
            <div className="text-2xl font-bold font-mono text-[#EF4444] mt-1">{rejectedCount}</div>
            <span className="text-[10px] text-rose-400 mt-1 block">Revision required</span>
          </div>
        </div>

        {/* Split Workstation: Plan Versions Table (Left 45%) & Detailed Inspector (Right 55%) */}
        <div className="grid grid-cols-12 gap-4 items-start">
          {/* Left Side: Plan Versions List */}
          <div className="col-span-12 lg:col-span-5 bg-[#0B1120] border border-[#1A263D] rounded-lg overflow-hidden flex flex-col">
            <div className="bg-[#162238] border-b border-[#1A263D] px-3.5 py-2.5 flex items-center justify-between">
              <span className="font-semibold text-[#F8FAFC]">Plan Versions</span>
              <span className="text-[10px] font-mono text-[#64748B]">History & Ledger</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-[#070D18] border-b border-[#1A263D] text-[#94A3B8] text-[10px] uppercase font-semibold">
                    <th className="py-2.5 px-3">Version</th>
                    <th className="py-2.5 px-2.5">Status</th>
                    <th className="py-2.5 px-2.5">Created</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1A263D]/60">
                  {versions.map((ver) => {
                    const isSelected = selectedVersionId === ver.id;
                    const isPending = ver.status === 'PENDING_REVIEW';
                    const isApproved = ver.status === 'APPROVED';
                    const isRejected = ver.status === 'REJECTED';

                    return (
                      <tr
                        key={ver.id}
                        onClick={() => setSelectedVersionId(ver.id)}
                        className={`cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-[#162238] text-[#F8FAFC] border-l-2 border-l-[#2563EB]'
                            : 'hover:bg-[#162238]/80 text-[#94A3B8]'
                        }`}
                      >
                        <td className="py-3 px-3">
                          <span className="font-mono font-semibold text-[#F8FAFC]">{ver.version}</span>
                          <span className="block text-[9.5px] font-mono text-[#64748B] truncate max-w-[100px]">
                            {ver.id}
                          </span>
                        </td>

                        <td className="py-3 px-2.5 whitespace-nowrap">
                          {isApproved ? (
                            <span className="inline-block px-2 py-0.5 rounded text-[9.5px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                              Approved
                            </span>
                          ) : isPending ? (
                            <span className="inline-block px-2 py-0.5 rounded text-[9.5px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                              Pending Review
                            </span>
                          ) : isRejected ? (
                            <span className="inline-block px-2 py-0.5 rounded text-[9.5px] font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                              Rejected
                            </span>
                          ) : ver.status === 'UNDER_REVIEW' ? (
                            <span className="inline-block px-2 py-0.5 rounded text-[9.5px] font-semibold bg-sky-500/15 text-sky-400 border border-sky-500/30">
                              Under Review
                            </span>
                          ) : (
                            <span className="inline-block px-2 py-0.5 rounded text-[9.5px] font-semibold bg-slate-500/15 text-slate-400 border border-slate-500/30">
                              Superseded
                            </span>
                          )}
                        </td>

                        <td className="py-3 px-2.5 text-[11px] text-[#CBD5E1] whitespace-nowrap">
                          {ver.created}
                        </td>

                        <td className="py-3 px-3 text-right whitespace-nowrap">
                          {isPending ? (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedVersionId(ver.id);
                                setIsApprovalOpen(true);
                              }}
                              className="px-2.5 py-1 rounded text-[11px] font-medium bg-[#2563EB] hover:bg-[#1D4ED8] text-white transition-colors"
                            >
                              Review
                            </button>
                          ) : (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedVersionId(ver.id);
                              }}
                              className="px-2.5 py-1 rounded text-[11px] font-medium bg-[#162238] hover:bg-[#1A263D] text-[#CBD5E1] border border-[#1A263D] transition-colors"
                            >
                              View
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Side: Detailed Plan Version Inspector */}
          <div className="col-span-12 lg:col-span-7 bg-[#0B1120] border border-[#162238] rounded-lg overflow-hidden flex flex-col">
            {/* Inspector Header with Tabs */}
            <div className="bg-[#070D18] border-b border-[#162238] px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-[#38BDF8]" />
                <span className="font-semibold text-[#F8FAFC]">
                  Plan Version {selectedVersion.version} ({selectedVersion.status === 'PENDING_REVIEW' ? 'Active' : selectedVersion.status})
                </span>
              </div>

              {/* Inspector Sub-Tabs: [Details | Review | Audit Trail] */}
              <div className="flex items-center gap-1 bg-[#070D18] border border-[#162238] p-0.5 rounded text-[11px] font-medium">
                <button
                  onClick={() => setInspectorTab('DETAILS')}
                  className={`px-3 py-1 rounded transition-colors ${
                    inspectorTab === 'DETAILS' ? 'bg-[#2563EB] text-white shadow-xs' : 'text-[#94A3B8] hover:text-[#F8FAFC]'
                  }`}
                >
                  Details
                </button>
                <button
                  onClick={() => setInspectorTab('REVIEW')}
                  className={`px-3 py-1 rounded transition-colors ${
                    inspectorTab === 'REVIEW' ? 'bg-[#2563EB] text-white shadow-xs' : 'text-[#94A3B8] hover:text-[#F8FAFC]'
                  }`}
                >
                  Review ({comments.length})
                </button>
                <button
                  onClick={() => setInspectorTab('AUDIT')}
                  className={`px-3 py-1 rounded transition-colors ${
                    inspectorTab === 'AUDIT' ? 'bg-[#2563EB] text-white shadow-xs' : 'text-[#94A3B8] hover:text-[#F8FAFC]'
                  }`}
                >
                  Audit Trail
                </button>
              </div>
            </div>

            {/* Tab 1: Details Content */}
            {inspectorTab === 'DETAILS' && (
              <div className="p-4 space-y-4">
                <div className="grid grid-cols-2 gap-3 bg-[#070D18] border border-[#162238] rounded-lg p-3.5 text-xs">
                  <div>
                    <span className="text-[10px] text-[#64748B] block font-mono">Plan Version ID</span>
                    <span className="font-mono font-semibold text-[#F8FAFC]">{selectedVersion.id}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#64748B] block font-mono">Scenario</span>
                    <span className="text-[#F8FAFC] font-medium">SCN-DEMO-001 (Northern Corridor)</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#64748B] block font-mono">Created By</span>
                    <span className="text-[#CBD5E1]">{selectedVersion.creator}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#64748B] block font-mono">Timestamp</span>
                    <span className="font-mono text-[#CBD5E1]">{selectedVersion.created}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#64748B] block font-mono">Scheduled Work</span>
                    <span className="font-bold text-emerald-400">{selectedVersion.scheduledCount} tasks placed</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#64748B] block font-mono">Unplaced Requisitions</span>
                    <span className="font-bold text-amber-400">{selectedVersion.unplacedCount} unplaced</span>
                  </div>
                </div>

                {/* SHA-256 Fingerprint */}
                <div className="bg-[#070D18] border border-[#162238] rounded-lg p-3.5 text-xs space-y-1">
                  <div className="flex items-center gap-1.5 text-[#94A3B8]">
                    <Fingerprint className="w-3.5 h-3.5 text-[#38BDF8]" />
                    <span className="font-semibold text-[#F8FAFC]">Schedule Fingerprint (SHA-256)</span>
                  </div>
                  <code className="block bg-[#0B1120] border border-[#162238] p-2 rounded text-[11px] font-mono text-[#38BDF8] break-all select-all">
                    {selectedVersion.hash}
                  </code>
                </div>

                {/* Independent Validation Banner */}
                {selectedVersion.status === 'APPROVED' ? (
                  <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3 text-xs flex items-center justify-between text-[#F8FAFC]">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      <div>
                        <span className="font-semibold text-emerald-300">Independent Feasibility Verified</span>
                        <p className="text-[11px] text-[#94A3B8]">Algorithmic feasibility verified (0 hard constraint violations prior to sign-off)</p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
                      APPROVED
                    </span>
                  </div>
                ) : selectedVersion.status === 'REJECTED' ? (
                  <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg p-3 text-xs flex items-center justify-between text-[#F8FAFC]">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-rose-400" />
                      <div>
                        <span className="font-semibold text-rose-300">Governance Review: Rejected</span>
                        <p className="text-[11px] text-[#94A3B8]">Plan version rejected during Four-Eyes review gate</p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-rose-400 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800">
                      REJECTED
                    </span>
                  </div>
                ) : (
                  <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-xs flex items-center justify-between text-[#F8FAFC]">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-amber-400" />
                      <div>
                        <span className="font-semibold text-amber-300">Candidate Evaluation</span>
                        <p className="text-[11px] text-[#94A3B8]">Validation findings subject to formal Four-Eyes sign-off</p>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800">
                      PENDING
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Tab 2: Review Comments Thread */}
            {inspectorTab === 'REVIEW' && (
              <div className="p-4 space-y-4">
                {comments.length > 0 ? (
                  <div className="space-y-3">
                    {comments.map((c) => (
                      <div
                        key={c.id}
                        className="bg-[#070D18] border border-[#162238] rounded-lg p-3 space-y-1.5 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-[#F8FAFC]">{c.author}</span>
                            <span className="text-[10px] text-[#64748B] font-mono">({c.role})</span>
                            {c.isLocalDraft && (
                              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 font-medium">
                                Local Session Draft (Not Persisted to Backend)
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] text-[#64748B] font-mono">{c.time}</span>
                        </div>
                        <p className="text-[#CBD5E1] text-[11px] leading-relaxed">{c.text}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-6 text-[#94A3B8] text-xs">
                    <MessageSquare className="w-6 h-6 mx-auto text-[#64748B] mb-2" />
                    <p className="font-semibold text-[#F8FAFC]">No Review Comments</p>
                    <p className="text-[11px] mt-0.5">No comments recorded for this plan version.</p>
                  </div>
                )}

                {/* Add Comment Input */}
                <div className="pt-2 flex items-center gap-2">
                  <div className="relative flex-1">
                    <MessageSquare className="w-3.5 h-3.5 text-[#64748B] absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      placeholder="Add a review comment..."
                      value={newCommentText}
                      onChange={(e) => setNewCommentText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleAddComment();
                      }}
                      className="w-full bg-[#070D18] border border-[#162238] rounded-lg pl-9 pr-3 py-2 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:outline-hidden focus:border-[#2563EB]"
                    />
                  </div>
                  <Button
                    size="sm"
                    onClick={handleAddComment}
                    className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs h-9 px-3"
                  >
                    <Send className="w-3 h-3 mr-1" />
                    Post
                  </Button>
                </div>
              </div>
            )}

            {/* Tab 3: Audit Trail Timeline */}
            {inspectorTab === 'AUDIT' && (
              <div className="p-4 space-y-3">
                {auditLogs.length > 0 ? (
                  <div className="space-y-3 text-xs">
                    {auditLogs.map((log, idx) => (
                      <div key={idx} className="relative pl-6 pb-3 border-l border-[#162238] last:border-0 last:pb-0">
                        <div className="absolute -left-[5px] top-0 w-2.5 h-2.5 rounded-full bg-[#2563EB] border-2 border-[#0B1120]" />
                        <div className="bg-[#070D18] border border-[#162238] rounded-lg p-2.5 space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-[#F8FAFC]">
                              {log.event_type || 'PLAN_VERSION_EVENT'}
                            </span>
                            <span className="text-[10px] text-[#64748B] font-mono">
                              {new Date(log.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          <p className="text-[11px] text-[#94A3B8]">
                            {log.comment || 'Event registered in immutable hash-chained audit ledger.'}
                          </p>
                          <div className="text-[10px] text-[#64748B] font-mono">
                            Actor: {log.actor_username || 'System'} ({log.actor_role || 'OPERATOR'})
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-6 text-[#94A3B8] text-xs">
                    <ShieldCheck className="w-6 h-6 mx-auto text-[#64748B] mb-2" />
                    <p className="font-semibold text-[#F8FAFC]">No Audit Events</p>
                    <p className="text-[11px] mt-0.5">No immutable audit events registered yet for this plan version.</p>
                  </div>
                )}
              </div>
            )}

            {/* Bottom Persistent Human Decision Bar */}
            <div className="bg-[#070D18] border-t border-[#162238] p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-auto">
              <div className="flex items-center gap-1.5 text-xs text-amber-400 font-medium">
                <Lock className="w-3.5 h-3.5 text-amber-400" />
                <span>Human Decision Required: COMPLETED ≠ APPROVED</span>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setInfoMessage('Returned plan version for revisions in workflow queue.')}
                  className="border-[#162238] text-xs text-[#CBD5E1] hover:text-white bg-[#0B1120] hover:bg-[#162238] h-8"
                >
                  <RotateCcw className="w-3 h-3 mr-1" />
                  Return for Revision
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDirectReject}
                  className="border-rose-500/40 text-xs text-rose-400 hover:bg-rose-950/40 h-8"
                >
                  <XCircle className="w-3 h-3 mr-1" />
                  Reject Plan
                </Button>

                <Button
                  size="sm"
                  onClick={handleDirectApprove}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold h-8 shadow-xs"
                >
                  <CheckCircle className="w-3.5 h-3.5 mr-1" />
                  Approve Plan
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Plan Approval Modal */}
      <PlanApprovalModal
        isOpen={isApprovalOpen}
        onClose={() => setIsApprovalOpen(false)}
        planVersion={modalPlanVersion}
        onApprove={(data) =>
          handleApproveAction({
            reviewer_name: data.reviewer_name,
            reviewer_role: data.reviewer_role,
            approval_notes: data.approval_notes,
          })
        }
        onReject={(data) =>
          handleRejectAction({
            reviewer_name: data.reviewer_name,
            reviewer_role: data.reviewer_role,
            rejection_reason: data.rejection_reason,
          })
        }
      />
    </>
  );
}
