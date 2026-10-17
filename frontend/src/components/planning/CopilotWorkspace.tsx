'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  Lock,
  FileText,
  AlertTriangle,
  HelpCircle,
  RefreshCw,
  ExternalLink,
  ShieldAlert,
} from 'lucide-react';
import { askCopilot, CopilotEvidenceItem } from '@/lib/api/client';
import { ResponsiveDrawer } from '@/components/common/ResponsiveDrawer';
import { MarkdownRenderer } from '@/components/common/MarkdownRenderer';

interface Message {
  id: string;
  sender: 'USER' | 'COPILOT';
  text: string;
  timestamp: string;
  evidence?: CopilotEvidenceItem[];
  provider?: string;
  isError?: boolean;
}

const INITIAL_MESSAGES: Message[] = [
  {
    id: 'MSG-01',
    sender: 'COPILOT',
    text: `### TrackMeld Decision Support Copilot
TrackMeld Copilot is initialized in **strictly read-only decision support mode**. All explanations are grounded against solver telemetry snapshots and statutory Indian Railways operating rules.

You can inquire about:
- **Task Scheduling Decisions**: Why a work order was scheduled or unscheduled
- **Timetable & Section Contention**: Conflicting passenger express trains or shared equipment
- **Railway Operating Rules**: Statutory safety clearances, headway rules, and manual citations
- **Governance & Approval Status**: DRM sign-off requirements and plan version audit logs

*Safety Boundary:* The Copilot cannot alter schedules, bypass constraints, or grant operational approvals (\`COMPLETED ≠ APPROVED\`).`,
    timestamp: '14:30 UTC',
    provider: 'DETERMINISTIC_EVIDENCE_ENGINE',
  },
];

interface CopilotWorkspaceProps {
  hideHeader?: boolean;
  selectedTaskId?: string | null;
  onSelectTask?: (taskId: string) => void;
}

export const CopilotWorkspace: React.FC<CopilotWorkspaceProps> = ({
  hideHeader = false,
  selectedTaskId,
  onSelectTask,
}) => {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeEvidence, setActiveEvidence] = useState<CopilotEvidenceItem[]>([]);
  const [isEvidenceDrawerOpen, setIsEvidenceDrawerOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message on update
  useEffect(() => {
    if (messages.length > 1 || loading) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading]);

  const handleSend = async (queryText?: string) => {
    const text = (queryText || inputQuery).trim();
    if (!text || loading) return;

    const userMsg: Message = {
      id: `USER-${Date.now()}`,
      sender: 'USER',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setLoading(true);

    try {
      const res = await askCopilot({
        prompt: text,
        scenario_id: 'SCN-DEMO-001',
        task_id: selectedTaskId || undefined,
      });

      const copilotMsg: Message = {
        id: `COPILOT-${Date.now()}`,
        sender: 'COPILOT',
        text: res.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        evidence: res.evidence,
        provider: res.provider_used,
      };

      setMessages((prev) => [...prev, copilotMsg]);
      if (res.evidence && res.evidence.length > 0) {
        setActiveEvidence(res.evidence);
      }
    } catch (err: unknown) {
      console.warn('Copilot query error:', err);
      const errMsg = err instanceof Error ? err.message : 'Backend unreachable';
      const errorMsg: Message = {
        id: `ERROR-${Date.now()}`,
        sender: 'COPILOT',
        text: `**System Communication Warning:** Could not reach the backend Copilot service (${errMsg}).

In adherence to Indian Railways decision support boundaries, the Copilot cannot infer, speculate, or fabricate ungrounded answers without verified database records.

*Recommendation:* Ensure backend service is active or retry inquiry.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        provider: 'LOCAL_GUARDRAIL',
        isError: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleEvidenceClick = (ev: CopilotEvidenceItem) => {
    if (onSelectTask) {
      if (ev.evidence_id.startsWith('TASK:')) {
        onSelectTask(ev.evidence_id.replace('TASK:', ''));
      } else if (ev.evidence_id.startsWith('CONFLICT:')) {
        onSelectTask(ev.evidence_id.replace('CONFLICT:', ''));
      }
    }
  };

  const renderEvidenceList = () => (
    <>
      {activeEvidence.length === 0 ? (
        <div className="py-8 text-center text-[#64748B] space-y-1">
          <HelpCircle className="w-6 h-6 mx-auto mb-1 opacity-50" />
          <p>No active evidence citations for this query.</p>
          <span className="text-[11px] text-[#475569]">Evidence cards populate from verified solver snapshots and railway rules.</span>
        </div>
      ) : (
        activeEvidence.map((ev, idx) => (
          <div
            key={idx}
            className="bg-[#0A0E17]/80 border border-[#1E2D4A] rounded-lg p-3.5 space-y-2 text-xs"
          >
            <div className="flex justify-between items-center">
              <span className="font-semibold text-[#F8FAFC]">{ev.title}</span>
              <span className="text-[9.5px] font-mono text-[#38BDF8] bg-[#141F36] px-1.5 py-0.5 rounded border border-[#1E2D4A]">
                {ev.evidence_type}
              </span>
            </div>

            <div className="text-[10px] font-mono text-[#64748B]">
              Evidence Ref: <strong className="text-[#93C5FD]">{ev.evidence_id}</strong>
            </div>

            {/* Structured facts view */}
            {ev.data && Object.keys(ev.data).length > 0 && (
              <div className="bg-[#070B12] rounded p-2.5 border border-[#1E2D4A]/60 space-y-1">
                {Object.entries(ev.data).map(([key, val]) => (
                  <div key={key} className="flex justify-between items-center text-[10.5px]">
                    <span className="text-[#64748B] font-mono capitalize">{key.replace(/_/g, ' ')}:</span>
                    <span className="font-mono text-[#CBD5E1] truncate max-w-[240px]">
                      {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {ev.source_reference && (
              <div className="text-[10px] text-[#64748B] flex items-center justify-between pt-1 border-t border-[#1E2D4A]/60">
                <span className="flex items-center gap-1">
                  <span>Source:</span>
                  <span className="text-[#94A3B8] font-mono">{ev.source_reference}</span>
                </span>
                {(ev.evidence_id.startsWith('TASK:') || ev.evidence_id.startsWith('CONFLICT:')) && onSelectTask && (
                  <button
                    onClick={() => handleEvidenceClick(ev)}
                    className="text-[#38BDF8] hover:underline flex items-center gap-0.5 cursor-pointer"
                  >
                    <span>Inspect Record</span>
                    <ExternalLink className="w-2.5 h-2.5" />
                  </button>
                )}
              </div>
            )}
          </div>
        ))
      )}

      {/* Safety Notice */}
      <div className="bg-[#141F36] border border-[#1E2D4A] rounded-md p-2.5 space-y-1 text-[10px] text-[#94A3B8]">
        <div className="font-semibold text-[#F8FAFC] flex items-center gap-1">
          <AlertTriangle className="w-3 h-3 text-amber-400" />
          <span>Deterministic Safety Boundary</span>
        </div>
        <p className="leading-relaxed">
          Copilot queries execute over verified snapshot facts. It has no tool bindings to modify database records or grant operational clearances.
        </p>
      </div>
    </>
  );

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0A0E17] p-2 sm:p-2.5 gap-2 overflow-hidden font-sans text-xs min-h-0">
      {/* 1. Header */}
      {!hideHeader && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-2.5 sm:p-3 shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <Bot className="w-4.5 h-4.5 text-[#2563EB]" />
              <h2 className="text-sm font-bold text-[#F8FAFC]">AI Copilot Decision Support</h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-[#38BDF8] font-bold border border-blue-500/30">
                STRICTLY READ-ONLY
              </span>
            </div>
            <p className="text-[11px] text-[#94A3B8] mt-0.5">
              Evidence-grounded operational inquiries, constraint explanations, and rule citations
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsEvidenceDrawerOpen(true)}
              className="lg:hidden flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#141F36] hover:bg-[#1E2D4A] border border-[#2D436D] text-xs font-mono text-[#93C5FD] transition-colors cursor-pointer"
            >
              <FileText className="w-3.5 h-3.5 text-[#38BDF8]" />
              <span>Evidence ({activeEvidence.length})</span>
            </button>

            <div className="hidden sm:flex items-center gap-2 text-xs font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-2.5 py-1 rounded">
              <span>Evidence Grounded • Zero Hallucinations</span>
            </div>
          </div>
        </div>
      )}

      {/* 2. Read-Only Guardrail Warning Banner */}
      <div className="bg-[#141F36] border border-[#2D436D] rounded-lg px-3 py-1.5 flex items-center justify-between gap-2.5 shrink-0 flex-wrap sm:flex-nowrap">
        <div className="flex items-center gap-2">
          <Lock className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <div className="text-[11px] text-[#CBD5E1]">
            <span className="font-semibold text-[#F8FAFC] mr-1">Read-Only Safety Guardrail:</span>
            <span>
              The Copilot cannot approve plans, modify schedules, or issue railway commands. All actions remain under human authority.
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 font-bold">
            Verified Evidence Records
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/60 border border-amber-500/30 text-amber-400 font-bold">
            Deterministic Safety Boundary
          </span>
          <span className="text-[10px] font-mono text-amber-400 font-bold shrink-0">
            COMPLETED ≠ APPROVED
          </span>
        </div>
      </div>

      {/* 3. Primary Conversation Workspace */}
      <div className="flex-1 w-full bg-[#0F172A] border border-[#1E2D4A] rounded-lg flex flex-col overflow-hidden min-h-0 shadow-sm">
        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
          {messages.map((m) => {
            const isCopilot = m.sender === 'COPILOT';
            return (
              <div
                key={m.id}
                className={`flex gap-3.5 ${isCopilot ? 'items-start max-w-4xl' : 'items-start justify-end ml-auto max-w-2xl'}`}
              >
                {isCopilot && (
                  <div className="w-8 h-8 rounded-lg bg-[#141F36] border border-[#2D436D] flex items-center justify-center text-[#38BDF8] shrink-0 mt-1 shadow-xs">
                    <Bot className="w-4.5 h-4.5" />
                  </div>
                )}

                <div
                  className={`rounded-xl p-4 sm:p-5 space-y-2.5 text-xs leading-relaxed shadow-sm ${
                    isCopilot
                      ? m.isError
                        ? 'bg-rose-950/30 border border-rose-500/40 text-rose-100'
                        : 'bg-[#141F36]/90 border border-[#1E2D4A] text-[#F8FAFC]'
                      : 'bg-[#2563EB] text-white'
                  }`}
                >
                  <div className="flex items-center justify-between gap-4 text-[10.5px]">
                    <span className={isCopilot ? 'text-[#38BDF8] font-semibold flex items-center gap-1.5' : 'text-blue-100 font-semibold'}>
                      {isCopilot ? (
                        <>
                          <Sparkles className="w-3 h-3 text-[#38BDF8]" />
                          <span>TrackMeld Copilot ({m.provider || 'Read-Only'})</span>
                        </>
                      ) : (
                        'Operations Planner'
                      )}
                    </span>
                    <span className="font-mono text-[#64748B]">{m.timestamp}</span>
                  </div>

                  {/* Render Markdown */}
                  <MarkdownRenderer content={m.text} />

                  {/* Evidence Citations */}
                  {m.evidence && m.evidence.length > 0 && (
                    <div className="pt-3 border-t border-[#1E2D4A] flex items-center gap-2 flex-wrap">
                      <span className="text-[10.5px] text-[#64748B] flex items-center gap-1 font-mono font-bold uppercase">
                        <FileText className="w-3.5 h-3.5 text-[#38BDF8]" />
                        Citations:
                      </span>
                      {m.evidence.map((ev) => (
                        <button
                          key={ev.evidence_id}
                          onClick={() => {
                            setActiveEvidence(m.evidence || []);
                            setIsEvidenceDrawerOpen(true);
                          }}
                          className="text-[11px] font-mono bg-[#0A0E17] hover:bg-[#1E2D4A] hover:border-[#38BDF8] text-[#93C5FD] border border-[#2D436D] px-2.5 py-1 rounded-md transition-colors cursor-pointer flex items-center gap-1.5"
                          title="Inspect verified evidence record"
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-[#38BDF8]" />
                          <span>{ev.title}</span>
                          <span className="text-[9.5px] text-[#64748B]">({ev.evidence_type})</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="flex items-center gap-2.5 text-xs text-[#94A3B8] p-3 bg-[#141F36]/60 border border-[#1E2D4A] rounded-lg max-w-md">
              <RefreshCw className="w-4 h-4 text-[#38BDF8] animate-spin" />
              <span>Auditing solver constraints and querying verified database records...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Queries Strip */}
        <div className="px-3 py-1.5 bg-[#0A0E17]/80 border-t border-[#1E2D4A] flex items-center gap-1.5 overflow-x-auto shrink-0 text-xs">
          <span className="text-[10px] text-[#64748B] uppercase font-bold font-mono shrink-0">
            Suggested:
          </span>
          <button
            onClick={() => handleSend('Why was task TSK-0007 not scheduled in the 72-hour planning window?')}
            className="text-[11px] bg-[#141F36] hover:bg-[#1E2D4A] hover:border-[#38BDF8] text-[#CBD5E1] hover:text-white border border-[#1E2D4A] px-2.5 py-1 rounded-md whitespace-nowrap transition-colors cursor-pointer"
          >
            Why was TSK-0007 not scheduled?
          </button>
          <button
            onClick={() => handleSend('Explain headway clearance margins for express trains under RULE-HDW-01')}
            className="text-[11px] bg-[#141F36] hover:bg-[#1E2D4A] hover:border-[#38BDF8] text-[#CBD5E1] hover:text-white border border-[#1E2D4A] px-2.5 py-1 rounded-md whitespace-nowrap transition-colors cursor-pointer"
          >
            Explain headway clearance margins
          </button>
          <button
            onClick={() => handleSend('What constraint rules are verified by the independent validator?')}
            className="text-[11px] bg-[#141F36] hover:bg-[#1E2D4A] hover:border-[#38BDF8] text-[#CBD5E1] hover:text-white border border-[#1E2D4A] px-2.5 py-1 rounded-md whitespace-nowrap transition-colors cursor-pointer"
          >
            List independent validation checks
          </button>
          <button
            onClick={() => handleSend('What is the governance review status of Plan Version 1?')}
            className="text-[11px] bg-[#141F36] hover:bg-[#1E2D4A] hover:border-[#38BDF8] text-[#CBD5E1] hover:text-white border border-[#1E2D4A] px-2.5 py-1 rounded-md whitespace-nowrap transition-colors cursor-pointer"
          >
            Check Plan Version 1 status
          </button>
        </div>

        {/* Input Composer */}
        <div className="p-2 sm:p-2.5 bg-[#141F36] border-t border-[#1E2D4A] flex items-center gap-2 shrink-0">
          <input
            type="text"
            placeholder="Ask Copilot about conflicts, schedule feasibility, or rule references..."
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSend();
            }}
            disabled={loading}
            className="flex-1 bg-[#0A0E17] border border-[#1E2D4A] rounded-lg px-3 py-1.5 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:outline-hidden focus:border-[#2563EB]"
          />
          <button
            onClick={() => setIsEvidenceDrawerOpen(true)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#0F172A] hover:bg-[#1E2D4A] border border-[#2D436D] text-xs font-mono text-[#93C5FD] transition-colors cursor-pointer h-7.5"
            title="Inspect active evidence citations"
          >
            <FileText className="w-3.5 h-3.5 text-[#38BDF8]" />
            <span className="hidden sm:inline">Evidence ({activeEvidence.length})</span>
          </button>
          <button
            onClick={() => handleSend()}
            disabled={loading || !inputQuery.trim()}
            className="bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-40 text-white px-3.5 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer font-semibold text-xs h-7.5"
            title="Submit query"
          >
            <span>Ask</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 4. Verified Evidence Drawer */}
      <ResponsiveDrawer
        isOpen={isEvidenceDrawerOpen}
        onClose={() => setIsEvidenceDrawerOpen(false)}
        title="Verified Evidence & Provenance Records"
        subtitle="Grounded against solver snapshots and statutory Indian Railways rules"
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-[#38BDF8] font-bold border border-blue-500/30">
            {activeEvidence.length} CITATIONS
          </span>
        }
        maxWidth="max-w-xl"
      >
        <div className="p-5 space-y-4">
          {renderEvidenceList()}
        </div>
      </ResponsiveDrawer>
    </div>
  );
};
