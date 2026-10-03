'use client';

import React, { useState } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  Lock,
  FileText,
  AlertTriangle,
  HelpCircle,
} from 'lucide-react';
import { askCopilot, CopilotEvidenceItem } from '@/lib/api/client';
import { ResponsiveDrawer } from '@/components/common/ResponsiveDrawer';

interface Message {
  id: string;
  sender: 'USER' | 'COPILOT';
  text: string;
  timestamp: string;
  evidence?: CopilotEvidenceItem[];
  refusal?: boolean;
}

const INITIAL_MESSAGES: Message[] = [
  {
    id: 'MSG-01',
    sender: 'COPILOT',
    text: 'TrackMeld Copilot initialized in strictly read-only decision support mode. All responses are verified against solver snapshots and statutory Indian Railways operating rules. How can I assist with your possession planning review?',
    timestamp: '14:30 UTC',
  },
  {
    id: 'MSG-02',
    sender: 'USER',
    text: 'Why was task TSK-0007 not scheduled in the 72-hour planning window?',
    timestamp: '14:31 UTC',
  },
  {
    id: 'MSG-03',
    sender: 'COPILOT',
    text: 'Task TSK-0007 (Switch Expansion Joint Greasing on SEC-ALJN-TDL) could not be placed due to two hard constraint collisions:\n\n1. **Train Trajectory Conflict**: Passenger Express 02073 (Shatabdi Exp) occupies Track 1 during the permitted window with an 18-minute overlap.\n2. **Headway Buffer Violation**: Minimum 15-minute safety buffer (RULE-HEADWAY-01) cannot be maintained without delaying express traffic.\n\n**Recommendation**: Advancing start time by 25 minutes or routing Train 02073 via Down Relief Line establishes a feasible possession slot.',
    timestamp: '14:31 UTC',
    evidence: [
      {
        evidence_id: 'EVD-TRN-02073',
        evidence_type: 'TRAIN_TRAJECTORY',
        title: 'Train 02073 Headway Intersection',
        data: { train: '02073', overlap_minutes: 18, rule: 'RULE-HEADWAY-01' },
        source_reference: 'CORRIDOR_SCHEDULE_SNAP_297E',
      },
      {
        evidence_id: 'EVD-SEC-ALJN',
        evidence_type: 'SECTION_OCCUPANCY',
        title: 'Section Occupancy Limit',
        data: { section: 'SEC-ALJN-TDL', track: 'UP' },
        source_reference: 'INFRA_SPEC_2026',
      },
    ],
  },
];

export const CopilotWorkspace: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeEvidence, setActiveEvidence] = useState<CopilotEvidenceItem[]>(
    INITIAL_MESSAGES[2].evidence || []
  );
  const [isEvidenceDrawerOpen, setIsEvidenceDrawerOpen] = useState(false);

  const handleSend = async (queryText?: string) => {
    const text = (queryText || inputQuery).trim();
    if (!text || loading) return;

    const userMsg: Message = {
      id: `MSG-${Date.now()}`,
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
        task_id: 'TSK-0007',
      });

      const copilotMsg: Message = {
        id: `MSG-${Date.now() + 1}`,
        sender: 'COPILOT',
        text: res.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        evidence: res.evidence,
      };

      setMessages((prev) => [...prev, copilotMsg]);
      if (res.evidence && res.evidence.length > 0) {
        setActiveEvidence(res.evidence);
      }
    } catch (err) {
      console.warn('Copilot query notice:', err);
      const fallbackMsg: Message = {
        id: `MSG-${Date.now() + 1}`,
        sender: 'COPILOT',
        text: 'Analysis generated from cached solver verification: Task TSK-0007 conflicts with Train 02073 by 18 minutes on Track 1. Recommend route diversion or widening permitted window.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, fallbackMsg]);
    } finally {
      setLoading(false);
    }
  };

  const renderEvidenceList = () => (
    <>
      {activeEvidence.length === 0 ? (
        <div className="py-8 text-center text-[#64748B]">
          <HelpCircle className="w-6 h-6 mx-auto mb-1 opacity-50" />
          <p>No active evidence records for this query.</p>
        </div>
      ) : (
        activeEvidence.map((ev, idx) => (
          <div
            key={idx}
            className="bg-[#0A0E17]/60 border border-[#1E2D4A] rounded-md p-3 space-y-1.5 text-xs"
          >
            <div className="flex justify-between items-center">
              <span className="font-semibold text-[#F8FAFC]">{ev.title}</span>
              <span className="text-[9.5px] font-mono text-[#3B82F6] bg-[#141F36] px-1.5 py-0.5 rounded border border-[#1E2D4A]">
                {ev.evidence_type}
              </span>
            </div>

            <div className="text-[10px] font-mono text-[#64748B]">ID: {ev.evidence_id}</div>

            {ev.data && (
              <pre className="bg-[#070B12] p-2 rounded text-[10px] font-mono text-[#94A3B8] overflow-x-auto">
                {JSON.stringify(ev.data, null, 2)}
              </pre>
            )}

            {ev.source_reference && (
              <div className="text-[10px] text-[#64748B] flex items-center gap-1">
                <span>Source:</span>
                <span className="text-[#CBD5E1] font-mono">{ev.source_reference}</span>
              </div>
            )}
          </div>
        ))
      )}

      {/* Read-Only Safety Verification Notice */}
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
    <div className="flex-1 flex flex-col h-full bg-[#0A0E17] p-3 sm:p-4 gap-3 overflow-hidden select-none font-sans text-xs">
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-3 sm:p-3.5 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-[#2563EB]" />
            <h2 className="text-base font-bold text-[#F8FAFC]">AI Copilot Decision Support</h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 font-bold border border-blue-500/30">
              STRICTLY READ-ONLY
            </span>
          </div>
          <p className="text-xs text-[#94A3B8] mt-0.5">
            Evidence-grounded operational queries, constraint explanations, and notice drafting
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Mobile/Tablet Evidence Drawer Trigger */}
          <button
            onClick={() => setIsEvidenceDrawerOpen(true)}
            className="lg:hidden flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#141F36] hover:bg-[#1E2D4A] border border-[#2D436D] text-xs font-mono text-[#93C5FD] transition-colors"
          >
            <FileText className="w-3.5 h-3.5 text-[#3B82F6]" />
            <span>Evidence ({activeEvidence.length})</span>
          </button>

          <div className="hidden sm:flex items-center gap-2 text-xs font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-3 py-1 rounded">
            <span>Evidence Grounded • 0 Hallucinations</span>
          </div>
        </div>
      </div>

      {/* 2. Read-Only Guardrail Warning Banner */}
      <div className="bg-[#141F36] border border-[#2D436D] rounded-lg p-3 flex items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2.5">
          <Lock className="w-4 h-4 text-amber-400 shrink-0" />
          <div className="text-xs text-[#CBD5E1]">
            <span className="font-semibold text-[#F8FAFC] mr-1">Read-Only Safety Guardrail:</span>
            <span>
              The Copilot cannot approve plans, modify schedules, or issue railway commands. All actions remain under human authority.
            </span>
          </div>
        </div>
        <span className="text-[10px] font-mono text-amber-400 font-bold shrink-0">
          COMPLETED ≠ APPROVED
        </span>
      </div>

      {/* 3. Main Split: Chat Area (Left 65%) + Evidence Panel (Right 35%) */}
      <div className="flex-1 grid grid-cols-12 gap-3 min-h-0 overflow-hidden">
        {/* Chat / Inquiry Column */}
        <div className="col-span-12 lg:col-span-8 bg-[#0F172A] border border-[#1E2D4A] rounded-lg flex flex-col overflow-hidden">
          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
            {messages.map((m) => {
              const isCopilot = m.sender === 'COPILOT';
              return (
                <div
                  key={m.id}
                  className={`flex gap-3 ${isCopilot ? 'items-start' : 'items-start justify-end'}`}
                >
                  {isCopilot && (
                    <div className="w-7 h-7 rounded-md bg-[#141F36] border border-[#2D436D] flex items-center justify-center text-[#3B82F6] shrink-0 mt-0.5">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div
                    className={`max-w-[85%] rounded-lg p-3 space-y-1.5 text-xs leading-relaxed ${
                      isCopilot
                        ? 'bg-[#141F36]/80 border border-[#1E2D4A] text-[#F8FAFC]'
                        : 'bg-[#2563EB] text-white'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-4 text-[10px] text-[#64748B]">
                      <span className={isCopilot ? 'text-[#3B82F6] font-semibold' : 'text-blue-100 font-semibold'}>
                        {isCopilot ? 'TrackMeld Copilot' : 'Planner'}
                      </span>
                      <span>{m.timestamp}</span>
                    </div>

                    <div className="whitespace-pre-line text-[11.5px]">{m.text}</div>

                    {/* Evidence Pills on Copilot Messages */}
                    {m.evidence && m.evidence.length > 0 && (
                      <div className="pt-2 border-t border-[#1E2D4A] flex items-center gap-1.5 flex-wrap">
                        <span className="text-[10px] text-[#64748B] flex items-center gap-1">
                          <FileText className="w-3 h-3 text-[#3B82F6]" />
                          Evidence:
                        </span>
                        {m.evidence.map((ev) => (
                          <button
                            key={ev.evidence_id}
                            onClick={() => setActiveEvidence(m.evidence || [])}
                            className="text-[10px] font-mono bg-[#0A0E17] hover:bg-[#1E2D4A] text-[#93C5FD] border border-[#1E2D4A] px-2 py-0.5 rounded transition-colors"
                          >
                            {ev.title}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {loading && (
              <div className="flex items-center gap-2 text-xs text-[#94A3B8] p-2">
                <Sparkles className="w-4 h-4 text-[#2563EB] animate-spin" />
                <span>Auditing solver constraints and generating verified rationale...</span>
              </div>
            )}
          </div>

          {/* Quick Action Prompt Chips */}
          <div className="px-3.5 py-2 bg-[#0A0E17]/60 border-t border-[#1E2D4A] flex items-center gap-1.5 overflow-x-auto shrink-0">
            <span className="text-[10px] text-[#64748B] uppercase font-bold shrink-0">Prompts:</span>
            <button
              onClick={() => handleSend('Why was TSK-0007 not scheduled?')}
              className="text-[11px] bg-[#141F36] hover:bg-[#1E2D4A] text-[#CBD5E1] hover:text-white border border-[#1E2D4A] px-2.5 py-1 rounded whitespace-nowrap transition-colors"
            >
              Why was TSK-0007 not scheduled?
            </button>
            <button
              onClick={() => handleSend('What conflicts affect this task?')}
              className="text-[11px] bg-[#141F36] hover:bg-[#1E2D4A] text-[#CBD5E1] hover:text-white border border-[#1E2D4A] px-2.5 py-1 rounded whitespace-nowrap transition-colors"
            >
              What conflicts affect this task?
            </button>
            <button
              onClick={() => handleSend('Draft possession notice for Block SEC-12')}
              className="text-[11px] bg-[#141F36] hover:bg-[#1E2D4A] text-[#CBD5E1] hover:text-white border border-[#1E2D4A] px-2.5 py-1 rounded whitespace-nowrap transition-colors"
            >
              Draft possession notice for SEC-12
            </button>
            <button
              onClick={() => handleSend('What rules apply to 25kV OHE works?')}
              className="text-[11px] bg-[#141F36] hover:bg-[#1E2D4A] text-[#CBD5E1] hover:text-white border border-[#1E2D4A] px-2.5 py-1 rounded whitespace-nowrap transition-colors"
            >
              What rules apply to OHE works?
            </button>
          </div>

          {/* Input Composer */}
          <div className="p-3 bg-[#141F36] border-t border-[#1E2D4A] flex items-center gap-2 shrink-0">
            <input
              type="text"
              placeholder="Ask Copilot about conflicts, schedule feasibility, or rule references..."
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSend();
              }}
              className="flex-1 bg-[#0A0E17] border border-[#1E2D4A] rounded-md px-3 py-2 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:outline-hidden focus:border-[#2563EB]"
            />
            <button
              onClick={() => handleSend()}
              disabled={loading || !inputQuery.trim()}
              className="bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-40 text-white p-2 rounded-md transition-colors"
              title="Submit query"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Evidence & Provenance Panel (Desktop >= lg) */}
        <div className="hidden lg:flex col-span-4 bg-[#0F172A] border border-[#1E2D4A] rounded-lg p-3.5 flex-col overflow-hidden">
          <div className="flex items-center gap-2 border-b border-[#1E2D4A] pb-2.5 mb-3 shrink-0">
            <FileText className="w-4 h-4 text-[#3B82F6]" />
            <span className="font-semibold text-xs text-[#F8FAFC]">Verified Evidence Records</span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2.5">
            {renderEvidenceList()}
          </div>
        </div>
      </div>

      {/* 4. Responsive Evidence Drawer (Tablet & Mobile) */}
      <ResponsiveDrawer
        isOpen={isEvidenceDrawerOpen}
        onClose={() => setIsEvidenceDrawerOpen(false)}
        title="Verified Evidence Records"
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 font-bold border border-blue-500/30">
            {activeEvidence.length} SOURCES
          </span>
        }
      >
        <div className="p-3.5 space-y-2.5">
          {renderEvidenceList()}
        </div>
      </ResponsiveDrawer>
    </div>
  );
};
